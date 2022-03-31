#!/usr/local/bin/python3
import os
import re
import random
import logging
import concurrent.futures
import time
from py2neo import Graph
from kubernetes import client, config
from pyaci import Node, options, filters
from pprint import pformat
#If you need to look at the API calls this is what you do
#logging.basicConfig(level=logger.info)
logging.getLogger('pyaci').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-1s %(levelname)-1s [%(threadName)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class VkaciEnvVariables(object):
    '''Parse the environment variables'''
    def __init__(self, dict_env:dict = None):
        """Constructor with real environment variables"""
        super().__init__()
        self.dict_env = dict_env

        self.apic_ip = self.enviro().get("APIC_IPS")
        if self.apic_ip is not None:
            self.apic_ip = self.apic_ip.split(',')
        else:
            self.apic_ip = []

        self.tenant = self.enviro().get("TENANT")
        self.vrf = self.enviro().get("VRF")

        self.mode = self.enviro().get("MODE")
        if self.mode is None:
            self.mode = "None"

        self.kube_config = self.enviro().get("KUBE_CONFIG")
        self.cert_user= self.enviro().get("CERT_USER")
        self.cert_name= self.enviro().get("CERT_NAME")
        self.key_path= self.enviro().get("KEY_PATH")

        self.neo4j_url = self.enviro().get("NEO4J_URL", "neo4j://my-neo4j-release-neo4j:7687")
        self.neo4j_browser_url = self.enviro().get("NEO4J_BROWSER_URL", self.neo4j_url)
        self.neo4j_user = self.enviro().get("NEO4J_USER","neo4j")
        self.neo4j_password = self.enviro().get("NEO4J_PASSWORD")
        logger.info("Parsed Environment Variables %s", pformat(vars(self)))

    def enviro(self):
        '''Return the Dictionary with all the Environment Variables'''
        if self.dict_env == None:
            return os.environ
        else:
            return self.dict_env

class ApicMethodsResolve(object):
    '''Class to execute APIC Call to resolve Objects'''
    def __init__(self) -> None:
        super().__init__()
        
    def get_fvcep(self, apic: Node, aci_vrf: str):
        '''Return all the Mac addresses and the Child objects in a VRF '''
        return apic.methods.ResolveClass('fvCEp').GET(**options.rspSubtreeChildren &
            options.subtreeFilter(filters.Eq('fvIp.vrfDn', aci_vrf)))

    def get_fvcep_mac(self, apic: Node, mac: str):
        '''Return the fvRsCEpToPathEp of the specified mac address  '''
        return apic.methods.ResolveClass('fvCEp').GET(**options.filter(
            filters.Eq('fvCEp.mac', mac)) & options.rspSubtreeClass('fvRsCEpToPathEp'))[0]

    def get_lldpif(self, apic:Node, pathDn):
        '''Return the LLDP Interfaces for a specific port'''
        return apic.methods.ResolveClass('lldpIf').GET(**options.filter(
            filters.Eq('lldpIf.portDesc',pathDn)) & options.rspSubtreeClass('lldpAdjEp'))

    def get_cdpif(self, apic:Node, pathDn):
        '''Return the CDP Interfaces for a specific port'''
        return apic.methods.ResolveClass('cdpIf').GET(**options.filter(
            filters.Eq('cdpIf.locDesc',pathDn)) & options.rspSubtreeClass('cdpAdjEp'))

    def get_bgppeerentry(self, apic:Node, vrf: str, node_ip: str):
        '''Return the BGP Peer of the specified BGP neighbor (K8s node)'''
        return apic.methods.ResolveClass('bgpPeerEntry').GET(**options.filter(
            filters.Wcard('bgpPeerEntry.dn', vrf) & filters.Eq('bgpPeerEntry.addr', node_ip)))

    def path_fixup(self,apic:Node, path):
        '''In general the LLDP/CDP Path and the Endpoint paths are the same however in case we run
        mac pinning and vPC we end up with LACP running in individual mode and the
        the LLDP/CDP path to be the one of the vPC interface, but the endpoint is learned on
        the physical interface for example:
        The end point is learned over          topology/pod-1/paths-2104/pathep-[eth1/11]
        TheLLDP/CDP Adjagency is learned over  topology/pod-1/protpaths-2103-2104/pathep-[vpc_ucs-c1-1]
        So I need to normalize this
        '''

        if 'protpaths' in path:
            # protpaths means the interface is a vPC/PC so I canjust return the path all good
            return path

        #Derive the physcal interface from the proto path topology/pod-1/paths-2104/pathep-[eth1/11] -->
        #  topology/pod-1/node-2103/sys/phys-[eth1/11]
        logger.info('Detected a non vPC/PC interface')

        path_dn = path.replace('paths','node')
        path_dn = path_dn.replace('pathep','sys/phys')
        logger.info('Getting interface %s CDP and LLDP infos', path_dn)
        #Get the interface and its relationships to the CDP/LLDP class
        #Every interface should have them both even if disabled. But the only thing I care here is to find the 
        # Mapping to the correct vPC path and seems this does the trick.
        objs = apic.mit.FromDn(path_dn).GET(
            **options.rspSubtreeInclude('relations')
            & options.rspSubtreeClass('lldpIf,cdpIf'))
        for obj in objs:
            if obj.ClassName == 'lldpIf':
                logger.info("Interface %s is Bundled under %s ", path, obj.portDesc)
                return obj.portDesc
            if obj.ClassName == 'cdpIf':
                logger.info("Interface %s is Bundled under %s ", path, obj.locDesc)
                return obj.locDesc

        # If I do not find any path I return the original path this should not happen but at least 
        #Like this shouldn't crash
        return path

class VkaciBuilTopology(object):
    ''' Class to build the topology'''
    def __init__(self, env:VkaciEnvVariables, apic_methods:ApicMethodsResolve) -> None:
        super().__init__()
        self.pod = {}
        self.topology = {}
        self.env = env
        self.apic_methods = apic_methods

        if self.env.tenant is not None and self.env.vrf is not None:
            self.aci_vrf = 'uni/tn-' + self.env.tenant + '/ctx-' + self.env.vrf
        else: 
            self.aci_vrf = None
            logger.error("Invalid Tenant or VRF.")

        ## Configs can be set in Configuration class directly or using helper utility
        if self.is_local_mode(): 
            config.load_kube_config(config_file = self.env.kube_config)
        elif self.is_cluster_mode():
            config.load_incluster_config()
        else:
            logger.error("Invalid Mode, %s. Only LOCAL or CLUSTER is supported.", self.env.mode)

        self.v1 = client.CoreV1Api()

    def is_local_mode(self):
        '''Check if we are running in local mode: Not in a K8s cluster'''
        return self.env.mode.casefold() == "LOCAL".casefold()

    def is_cluster_mode(self):
        '''Check if we are running in cluster mode: in a K8s cluster'''
        return self.env.mode.casefold() == "CLUSTER".casefold()

    def add_neighbour(self, node, neighbour):
        ''' Get the Host that should be either the same as the K8s node or a Hypervisor host name.
            I try to get the LLDP adj, if fails I get the CDP one.
            I do expect to have at least one of the 2 '''
        AdjEp = getattr(neighbour, 'lldpAdjEp', None)
        if not AdjEp:
            AdjEp = getattr(neighbour, 'cdpAdjEp', None)

        for neighbour_adj in AdjEp:
            if neighbour_adj.sysName not in node['neighbours'].keys():
                node['neighbours'][neighbour_adj.sysName] = {}
                logger.info("Found the following Host as Neighbour %s", neighbour_adj.sysName)

            # Get the switch name and remove the topology and POD-1 topology/pod-1/node-204
            switch = neighbour.dn.split('/')[2].replace("node", "leaf")
            if switch not in node['neighbours'][neighbour_adj.sysName].keys() and neighbour_adj:
                node['neighbours'][neighbour_adj.sysName][switch] = set()
                logger.info("Found %s as Neighbour to %s:", switch, neighbour_adj.sysName)
            #LLDP Class is portId (I.E. VMNICX)
            neighbour_adj_port = getattr(neighbour_adj, 'chassisIdV', None)
            if not neighbour_adj_port:
                # CDP Class is portId
                neighbour_adj_port = getattr(neighbour_adj, 'portId', None)

            # If CDP and LLDP are on at the same time only LLDP will be enabled on the DVS so I check that I actually
            # Have a neighbour_adj_port and not None.
            if neighbour_adj_port:
                node['neighbours'][neighbour_adj.sysName][switch].add(neighbour_adj_port + '-' + neighbour.id  )
                logger.info("Added neighbour details %s to %s - %s", neighbour_adj_port + '-' + neighbour.id, neighbour_adj.sysName, switch)

    def update_node(self, apic, node):
        '''Gets a K8s node and populates it with the LLDP/CDP and BGP information'''

        #Find the mac to interface mapping
        logger.info("Find the mac to interface mapping for Node %s with MAC %s", node['node_ip'], node['mac'])
        path =  self.apic_methods.get_fvcep_mac(apic, node['mac'])

        #Get Path, there should be only one...need to add checks
        # i.e I get topology/pod-1/protpaths-101-102/pathep-[esxi1_PolGrp] 
        if len(path.fvRsCEpToPathEp) > 1:
            logger.error("Node %s %s is learned over multiple paths. This points to an ACI misconfiguration, i.e. port-channel/vPC operating in individual mode", node['node_ip'], node['mac'])

        for fvRsCEpToPathEp in path.fvRsCEpToPathEp:
            pathtDn = fvRsCEpToPathEp.tDn
            logger.info("Found path %s for %s %s", pathtDn, node['node_ip'], node['mac'])

        #Get all LLDP and CDP Neighbors for that interface, since I am using the path
        #This return a list of all the interfaces in that proto path 
        pathtDn = self.apic_methods.path_fixup(apic, pathtDn)
        lldp_neighbours = self.apic_methods.get_lldpif(apic, pathtDn)
        cdp_neighbours = self.apic_methods.get_cdpif(apic, pathtDn)

        if (len(lldp_neighbours) == 0 and len(cdp_neighbours) == 0 ):
            logger.error("No LLDP or CDP neighbour detected, the topology will be incomplete. ")

        # IF LLDP is UP and CDP is DOWN
        for lldp_neighbour in lldp_neighbours:
            if lldp_neighbour.operRxSt == "up" and lldp_neighbour.operTxSt == 'up':
                logger.debug("LLDP ADD")
                self.add_neighbour(node, lldp_neighbour)

        # IF CDP is UP and LLDP is DOWN
        for cdp_neighbour in cdp_neighbours:
            if cdp_neighbour.operSt == "up":
                logger.debug("CDP ADD")
                self.add_neighbour(node, cdp_neighbour)

        #Find the BGP Peer for the K8s Nodes, here I need to know the VRF of the K8s Node so that I can find the BGP entries in the right VRF. 
        # This is important as we might have IP reused in different VRFs. Luckilly the EP info has the VRF in it. 
        # The VRF format is  uni/tn-common/ctx-calico and we care about the tenant and ctx so we can split by / and - to get ['uni', 'tn', 'common', 'ctx', 'calico']
        #and extract the common and calico part.
        vrf=re.split('/|-',self.aci_vrf)
        vrf = '.*/dom-' + vrf[2] + ':' + vrf[4] + '/.*'
        bgpPeerEntry = self.apic_methods.get_bgppeerentry(apic, vrf, node['node_ip'])

        for bgpPeer in bgpPeerEntry:
            if bgpPeer.operSt == "established":
                node['bgp_peers'].add( bgpPeer.dn.split("/")[2].replace("node", "leaf") )

    def update(self):
        '''Update the topology by querying the APIC and K8s cluster'''
        logger.info("Start Topology Generation")
        self.topology = { }
        self.apics = []

        # Check APIC Ips
        if self.env.apic_ip is None or len(self.env.apic_ip) == 0:
            logger.error("Invalid APIC IP addresses.")
            return

        #Create list of APICs and set the useX509CertAuth parameters
        for i in self.env.apic_ip:
            self.apics.append(Node('https://' + i))
        logger.info("APICs To Probe %s", self.env.apic_ip)
        for apic in self.apics:
            if self.is_local_mode():
                logger.info("Running in Local Mode, using %s as user name, %s as certificate name and %s as key path", self.env.cert_user, self.env.cert_name, self.env.key_path)
                apic.useX509CertAuth(self.env.cert_user, self.env.cert_name, self.env.key_path)
            elif self.is_cluster_mode():
                logger.info("Running in Cluster Mode, using %s as user name, %s as certificate name and key is loaded as a K8s Secret ", self.env.cert_user, self.env.cert_name)
                apic.useX509CertAuth(self.env.cert_user, self.env.cert_name, '/usr/local/etc/aci-cert/user.key')
            else:
                logger.error("MODE can only be LOCAL or CLUSTER but %s was given", self.env.mode)
                return
        
        ##Load all the POD and Nodes in Memory. 
        logger.info("Loading K8s Pods in Memory")
        ret = self.v1.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            if i.spec.node_name not in self.topology.keys():
                self.topology[i.spec.node_name] = {
                   "node_ip": i.status.host_ip,
                   "pods" : {},
                   'bgp_peers': set(),
                   'neighbours': {}
                   }

            self.topology[i.spec.node_name]['pods'][i.metadata.name] = {
                "ip": i.status.pod_ip,
                "ns": i.metadata.namespace
                }

        logger.info("Pods Loaded, Current Topology %s", pformat(self.topology))
        start = time.time()
        #Get all the mac and ips in the Cluster VRF, and map the node_ip to Mac.
        # This is faster done locally. 
        # The same query where I filter by IP and VRF takes 0.4s per node
        # Dumping 900 EPs takes 1.3s in total.
        logger.info("Loading all the endpoints in %s VRF", self.aci_vrf)
        eps = self.apic_methods.get_fvcep(self.apics[0], self.aci_vrf)
        logger.info("ACI EP completed after: %s seconds", (time.time() - start))
        #Find the K8s Node IP/Mac
        # No Thread 50 nodes takes ~ 41 seconds
        #for k,v in self.topology.items():
        #    self.update_node(node=v)

        #Threaded to single APIC 50 nodes takes ~ 11 seconds
        #Threaded picking APIC randomly 50 nodes takes ~ 8 seconds
        logger.info("Start querying ACI")
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for k,v in self.topology.items():
                #find the mac for the IP of the node and add it to the topology file.
                for ep in eps:
                    for ip in ep.Children:
                        if ip.addr == v['node_ip']:
                            v['mac'] = ep.mac
                future = executor.submit(self.update_node, apic = random.choice(self.apics), node=v)
        executor.shutdown(wait=True)
        result = future.result()
        
        logger.info("ACI queries completed after: {} seconds".format(time.time() - start))
        logger.info("Topology:")
        logger.info(pformat(self.topology))
        return self.topology

    def get(self):
        '''return the topology'''
        return self.topology

    def get_leafs(self):
        '''return all the ACI leaves'''
        leafs = []
        for node in self.topology.keys():
            for v in self.topology[node]["bgp_peers"]:
                leafs.append(v)
            for v, n in self.topology[node]["neighbours"].items():
                leafs.extend(n.keys())    
        al=list(set(leafs))
        al.sort()
        return al
        
    def get_nodes(self):
        '''return all the K8s nodes'''
        al=list(self.topology.keys())
        al.sort()
        return al

    def get_pods(self):
        '''return all the pods'''
        pod_names = []
        for node in self.topology.keys():
            for pod in self.topology[node]["pods"].keys():
                pod_names.append(pod)
        return pod_names

    def get_namespaces(self):
        '''return all the namespaces'''
        namespaces = []
        for node in self.topology.keys():
            for k,v in self.topology[node]["pods"].items():
                namespaces.append(v["ns"])
        return list(set(namespaces))


class VkaciGraph(object):
    '''Class to build the Graph'''
    def __init__(self, env: VkaciEnvVariables, topology: VkaciBuilTopology) -> None:
        super().__init__()
        self.env = env
        self.topology = topology

    # Build query.
    query = """
    WITH $json as data
    UNWIND data.items as n
    UNWIND n.vm_hosts as v

    MERGE (node:Node {id:n.node_name}) ON CREATE
    SET node.name = n.node_name, node.ip = n.node_ip

    FOREACH (p IN n.pods | MERGE (pod:Pod {name:p.name}) ON CREATE
    SET pod.ip = p.ip, pod.ns = p.ns 
    MERGE (pod)-[:RUNNING_ON]->(node))

    MERGE (vmh:VM_Host{name:v.host_name}) MERGE (node)-[:RUNNING_IN]->(vmh)
    FOREACH (s IN v.switches | MERGE (switch:Switch {name:s.name}) MERGE (vmh)-[:CONNECTED_TO {interface:s.interface}]->(switch))

    FOREACH (switchName IN n.bgp_peers | MERGE (switch: Switch {name:switchName}) MERGE (node)-[:PEERED_INTO]->(switch))
    """

    def update_database(self):
        '''Update the neo4j database with the data collected from ACI and K8s'''
        graph = Graph(self.env.neo4j_url, auth=(self.env.neo4j_user, self.env.neo4j_password))
        topology = self.topology.update()
        data = self.build_graph_data(topology)

        graph.run("MATCH (n) DETACH DELETE n")
        results = graph.run(self.query,json=data)

        tx = graph.begin()
        graph.commit(tx)

    def build_graph_data(self, topology):
        '''generate the neo4j data to insert in the DB'''
        data = { "items": [] }

        for node in topology.keys():
            vm_hosts = []
            for neighbour, switches in topology[node]["neighbours"].items():
                switch_list = []
                for switchName, interfaces in switches.items():  
                    switch_list.append({"name": switchName, "interface": next(iter(interfaces or []), "")})     
                vm_hosts.append({"host_name": neighbour, "switches": switch_list})
            
            pods = []
            for pod_name, pod in topology[node]["pods"].items():
                pods.append({"name": pod_name, "ip": pod["ip"], "ns": pod["ns"]})

            data["items"].append({
                "node_name": node,
                "node_ip": topology[node]["node_ip"],
                "pods": pods,
                "vm_hosts": vm_hosts,
                "bgp_peers": list(topology[node]["bgp_peers"])
            })
            
        return data

class VkaciTable ():
    '''Handle the table view'''
    def __init__(self, topology: VkaciBuilTopology) -> None:
        super().__init__()
        self.topology = topology

    def get_table(self):
        '''Get the table data'''
        topology=self.topology.get()
        data = { "parent":0, "data": [] }
        i=1
        for node_name, node in topology.items():
            pods = []
            y = 1
            for pod_name, pod in node["pods"].items():
                pods.append({"id": str(i)+"."+str(y), "value": pod_name,
                    "ip": pod["ip"], "ns": pod["ns"], "image":"pod"})
                y=y+1 
            data["data"].append({
                "id": i,
                "value": node_name,
                "ip"   : node["node_ip"],
                "image":"node",
                "data" : pods
            })
            i=i+1
        return data
