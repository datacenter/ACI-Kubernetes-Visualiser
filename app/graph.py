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
from datetime import datetime
from natsort import natsorted
#If you need to look at the API calls this is what you do
#logging.basicConfig(level=logger.info)
#logging.getLogger('pyaci').setLevel(logging.DEBUG)

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

    def get_all_nexthops(self, apic:Node, dn:str):
        '''Get the routes, I need to also filter by AS'''
        return apic.methods.ResolveClass('uribv4Nexthop').GET(**options.filter(
            filters.Wcard('uribv4Nexthop.dn', dn)))
        
    def get_overlay_ip_to_switch_map(self, apic:Node):
        '''Get a dict mapping the switch ID to it's overlay IP address'''
        nodes = {}
        fabricNodes = apic.methods.ResolveClass('fabricNode').GET()
        for node in fabricNodes:
            nodes[node.address] = node.name
        return nodes
    
    def get_arp_adj_ep(self, apic: Node, mac:str):
        '''Return an IP Address '''
        return apic.methods.ResolveClass('arpAdjEp').GET(**options.filter(
            filters.Eq('arpAdjEp.mac',mac)))

    def path_fixup(self,apic:Node, path):
        '''In general the LLDP/CDP Path and the Endpoint paths are the same however in case we run
        mac pinning and vPC we end up with LACP running in individual mode and the
        the LLDP/CDP path to be the one of the vPC interface, but the endpoint is learned on
        the physical interface for example:
        The end point is learned over topology/pod-1/paths-2104/pathep-[eth1/11]
        The LLDP/CDP Adjagency is learned over topology/pod-1/protpaths-2103-2104/pathep-[vpc_ucs-c1-1]
        So I need to normalize this
        '''

        # Detect the link type by lagT values of fabricPathEp
        #fc-link => Fc Port Channel
        #link Direct Port Channel
        #node Virtaul Port Channel
        #not-aggregated Not an aggregated link
        
        fabricPathEp = apic.mit.FromDn(path).GET()[0]

        if 'node' == fabricPathEp.lagT or "link" == fabricPathEp.lagT:
            logger.info('Detected a vPC or PC Interface')
            # if the interface is a vPC/PC I canjust return the path all good
            return path
        
        #Derive the physcal interface from the proto path topology/pod-1/paths-2104/pathep-[eth1/11] -->
        #  topology/pod-1/node-2103/sys/phys-[eth1/11]
        logger.info('Detected a standalone interface')
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
        self.topology = { 'nodes': {}, 'services': {}}
        self.bgp_info = {}
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
        self.custom_obj = client.CustomObjectsApi()

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
                node['neighbours'][neighbour_adj.sysName] = {'switches': {}}
                node['neighbours'][neighbour_adj.sysName]['Description'] = ""
                logger.info("Found the following Host as Neighbour %s", neighbour_adj.sysName)

            # Get the switch name and remove the topology and POD-1 topology/pod-1/node-204
            switch = neighbour.dn.split('/')[2].replace("node", "leaf")
            if switch not in node['neighbours'][neighbour_adj.sysName]['switches'].keys() and neighbour_adj:
                node['neighbours'][neighbour_adj.sysName]['switches'][switch] = set()
                logger.info("Found %s as Neighbour to %s:", switch, neighbour_adj.sysName)
            
            #LLDP Class is portId (I.E. VMNICX)
            neighbour_description = getattr(neighbour_adj, 'sysDesc', None)
            if not neighbour_description:
                neighbour_description = getattr(neighbour_adj, 'ver', None)
            
            #Vmare esxi puts the port name vmnic in the chassisIdV while linux put the port name in the portDesc
            lldp_port_id_class = 'portDesc'
            if 'VMware' in neighbour_description:
                lldp_port_id_class = 'chassisIdV'
            # UCS Uses the portIdV
            if 'Cisco' in neighbour_description:
                lldp_port_id_class = 'portIdV'
            
            neighbour_adj_port = getattr(neighbour_adj,lldp_port_id_class, None)

            if not neighbour_adj_port:
                # CDP Class is platId
                neighbour_description = getattr(neighbour_adj, 'platId', None)
            
            if not neighbour_adj_port:
                # CDP Class is portId
                neighbour_adj_port = getattr(neighbour_adj, 'portId', None)

            # If CDP and LLDP are on at the same time only LLDP will be enabled on the DVS so I check that I actually
            # Have a neighbour_adj_port and not None.
            if neighbour_adj_port:
                node['neighbours'][neighbour_adj.sysName]['switches'][switch].add(neighbour_adj_port + '-' + neighbour.id)
                node['neighbours'][neighbour_adj.sysName]['Description'] = neighbour_description
                logger.info("Added neighbour details %s to %s - %s", neighbour_adj_port + '-' + neighbour.id, neighbour_adj.sysName, switch)

    def get_cluster_as(self):
        ''' Get the AS from K8s Configuration this assumes Calico is used'''
        asn = 0
        logger.debug("Detect Cluster AS")
        # Try to get Cluster AS from Calico Config
        try: 
            logger.debug("Try to detect Calico")
            res =  self.custom_obj.get_cluster_custom_object(
                group="crd.projectcalico.org",
                version="v1",
                name="default",
                plural="bgpconfigurations"
            )
            logger.info('Calico BGP Config Detected!')
            asn = str(res['spec']['asNumber'])
        except Exception as e:
            # The the CRD does not exists I get an 404 not found exeption
            pass
         # Try to get Cluster AS from kube-rotuer Config
        try: 
            logger.debug("Try to detect Kube-Router")
            pods = self.get_pods(ns='kube-system')
            kr_pod = False
            for pod in pods:
                if "kube-router" in pod:
                    #I just need one so I break immediately
                    kr_pod = self.v1.read_namespaced_pod(pod,'kube-system')
                    break
            if kr_pod:
                for arg in kr_pod.spec.containers[0].args:
                    if "--cluster-asn=" in arg:
                        asn = arg[14:]
                logger.info('Kube-Router Detected! Cluster AS=%s',asn)
        except Exception as e:
            pass
        if asn == 0:
            logger.error("Can't detect K8s Cluster AS, BGP topology will not work corectly")
        return asn

    def update_bgp_info(self, apic:Node):
        '''Get the BGP information'''
        
        # Get the K8s Cluster AS
        k8s_as = self.get_cluster_as()
        overlay_ip_to_switch = self.apic_methods.get_overlay_ip_to_switch_map(apic)
        self.bgp_info = {}
        vrf = self.env.tenant + ":" + self.env.vrf
        dn = "sys/uribv4/dom-" + vrf + "/db-rt"
        hops = self.apic_methods.get_all_nexthops(apic, dn)
        for hop in hops:
            route = ('/'.join(hop.dn.split('/')[7:9])).split('-')[1][1:-1]
            
            #Get only the IP without the Mask
            next_hop = hop.addr.split('/')[0]
            leaf = hop.dn.split('/')[2].replace("node", "leaf")
            if leaf not in self.bgp_info.keys():
                self.bgp_info[leaf] = {}
            if route != hop.addr:
                if route not in self.bgp_info[leaf].keys():
                    self.bgp_info[leaf][route] = {}
                    self.bgp_info[leaf][route]['hosts'] = []
                    self.bgp_info[leaf][route]['k8s_route'] = True
                if hop.tag == k8s_as:
                    #self.bgp_info[leaf][route]['ip'].add(next_hop)
                    host_name = ""
                    image = "node.svg"
                    if next_hop in overlay_ip_to_switch.keys():
                        host_name = overlay_ip_to_switch[next_hop]
                        image = "switch.png"
                    for k, v in self.topology['nodes'].items():
                        if next_hop == v['node_ip']:
                            host_name = k
                    self.bgp_info[leaf][route]["hosts"].append({"ip": next_hop, "hostname": host_name, "image": image})
                else:
                    self.bgp_info[leaf][route]['k8s_route'] = False
                    self.bgp_info[leaf][route]["hosts"].append({"ip": next_hop, "hostname": "&lt;No Hostname&gt;", "image": "Nok8slogo.png"})

        for leaf_name, leaf in self.bgp_info.items():
            count = len(leaf.keys())
            leaf["prefix_count"] = count
        logger.info("BGP Prefixes: %s", pformat(self.bgp_info))

    def update_node(self, apic, node):
        '''Gets a K8s node and populates it with the LLDP/CDP and BGP information'''
        if 'mac' not in node:
            logger.error("Could not resolved the mac address of node with ip %s", node['node_ip'] )
            exit()
        #Find the mac to interface mapping
        logger.info("Find the mac to interface mapping for Node %s with MAC %s", node['node_ip'], node['mac'])
        path =  self.apic_methods.get_fvcep_mac(apic, node['mac'])

        #Get Path, there should be only one...need to add checks
        # i.e I get topology/pod-1/protpaths-101-102/pathep-[esxi1_PolGrp] 
        if len(path.fvRsCEpToPathEp) > 1:
            logger.warning("Node %s %s is learned over multiple paths. This points to a possilbe ACI misconfiguration or Stale fvRsCEpToPathEp in the APIC, i.e. port-channel/vPC operating in individual mode. Will pick the most recent entry", node['node_ip'], node['mac'])
            # Due to CSCwc13370 I need to try to figure out what is the right path, the best way I found for now is 
            # to look for the arpAdjEps for the mac and find the one that has a physical path but it takes a while for the adj to 
            #be updated
            arpAdjEps = self.apic_methods.get_arp_adj_ep(apic, node['mac'])
            create_time = None
            logger.warning("Checking arpAdjEp")
            for arpAdjEp in arpAdjEps:
                if 'tunnel' not in arpAdjEp.physIfId:
                    if not create_time:
                        create_time = datetime.strptime(arpAdjEp.upTS,"%Y-%m-%dT%H:%M:%S.%f%z")
                        #Extract node id from the dn
                        arp_node_owner_id = arpAdjEp.dn.split("/")[2].split('-')[1]
                    elif datetime.strptime(arpAdjEp.upTS,"%Y-%m-%dT%H:%M:%S.%f%z") > create_time:
                        create_time = datetime.strptime(arpAdjEp.upTS,"%Y-%m-%dT%H:%M:%S.%f%z")
                        arp_node_owner_id = arpAdjEp.dn.split("/")[2].split('-')[1]
            for tmp in path.fvRsCEpToPathEp:
                if arp_node_owner_id in tmp.tDn:
                    pathtDn = tmp.tDn
                    logger.warning("Multiple paths: Selecting %s as path", pathtDn)
        else:
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

        if len(lldp_neighbours) > 0:
            # Prefer LLDP over CDP
            for lldp_neighbour in lldp_neighbours:
                if lldp_neighbour.operRxSt == "up" and lldp_neighbour.operTxSt == 'up':
                    logger.debug("LLDP ADD")
                    self.add_neighbour(node, lldp_neighbour)

        elif len(cdp_neighbours) > 0:
            for cdp_neighbour in cdp_neighbours:
                if cdp_neighbour.operSt == "up":
                    logger.debug("CDP ADD")
                    self.add_neighbour(node, cdp_neighbour)

        #Find the BGP Peer for the K8s Nodes, here I need to know the VRF of the K8s Node so that I can find the BGP entries in the right VRF. 
        # This is important as we might have IP reused in different VRFs. Luckilly the EP info has the VRF in it. 
        # The VRF format is  uni/tn-common/ctx-calico and we care about the tenant and ctx so we can split by /.
        #Then we can trim the strings as the tn- and ctx- are fixed. DO NOT split by - as - is a valid char for an APIC object
        tmp=re.split('/',self.aci_vrf)
        tenant=tmp[1][3:]
        vrf = tmp[2][4:]
        dn_filter = '.*/dom-' + tenant + ':' + vrf + '/.*'
        bgpPeerEntry = self.apic_methods.get_bgppeerentry(apic, dn_filter, node['node_ip'])
        logger.debug("bgpPeerEntry %s %s %s %s", bgpPeerEntry, apic, dn_filter, node['node_ip'])

        for bgpPeer in bgpPeerEntry:
            if bgpPeer.operSt == "established":
                name = bgpPeer.dn.split("/")[2].replace("node", "leaf")
                if name not in node['bgp_peers'].keys():
                    count = 0
                    if name in self.bgp_info.keys():
                        count = self.bgp_info[name]["prefix_count"]
                    node['bgp_peers'][name] = {"prefix_count": count}

    def add_prefix(self, svc):
        for leaf, route in self.bgp_info.items():
            for prefix in route.keys():
                if "/32" in prefix:
                    svc_ip = prefix.split('/')[0]
                    if svc_ip == svc['cluster_ip']:
                        svc["prefix"]=prefix
                    elif svc['external_i_ps']:
                        for ext_svc_ip in svc['external_i_ps']:
                            if svc_ip == ext_svc_ip:
                                svc["prefix"]=prefix
        return svc

    def update(self):
        '''Update the topology by querying the APIC and K8s cluster'''
        logger.info("Start Topology Generation")
        #self.topology = { }
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
        

        #Load all the POD, Services and Nodes in Memory. 
        logger.info("Loading K8s Pods in Memory")
        ret = self.v1.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            # Ensure the node has a name, if a POD is Pening there will be no node name.
            if i.spec.node_name:
                if i.spec.node_name not in self.topology['nodes'].keys():
                    self.topology['nodes'][i.spec.node_name] = {
                    "node_ip": i.status.host_ip,
                    "pods" : {},
                    'bgp_peers': {},
                    'neighbours': {}
                    }

                self.topology['nodes'][i.spec.node_name]['pods'][i.metadata.name] = {
                    "ip": i.status.pod_ip,
                    "ns": i.metadata.namespace
                    }
                    
        self.update_bgp_info(self.apics[0])

        logger.info("Loading K8s Services in Memory")
        ret = self.v1.list_service_for_all_namespaces(watch=False)
        for i in ret.items:
            if i.metadata.namespace not in self.topology['services']:
                self.topology['services'][i.metadata.namespace] = []
            svc_info = {
                'name': i.metadata.name,
                'cluster_ip':i.spec.cluster_ip,
                'external_i_ps': i.spec.external_i_ps, 
                'prefix': None
            }
            svc_info = self.add_prefix(svc_info)
            self.topology['services'][i.metadata.namespace].append(svc_info)
        
        logger.info("Pods, Nodes and Services Loaded")
        logger.debug("Current Topology %s", pformat(self.topology))
        

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
        #for k,v in self.topology['nodes'].items():
        #    self.update_node(node=v)

        #Threaded to single APIC 50 nodes takes ~ 11 seconds
        #Threaded picking APIC randomly 50 nodes takes ~ 8 seconds
        logger.info("Start querying ACI")
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor() as executor:            
            for k,v in self.topology['nodes'].items():
                logger.info("Updating node %s", k)
                #find the mac for the IP of the node and add it to the topology file.
                for ep in eps:
                    for ip in ep.Children:
                        if ip.addr == v['node_ip']:
                            logger.debug("Node %s: Updated MAC address %s", ip.addr, ep.mac)
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
    
    def get_bgp_info(self):
        '''return the bgp info'''
        return self.bgp_info

    def get_leafs(self):
        '''return all the ACI leaves'''
        leafs = []
        for node in self.topology['nodes'].keys():
            for v in self.topology['nodes'][node]["bgp_peers"]:
                leafs.append(v)
            for v, n in self.topology['nodes'][node]["neighbours"].items():
                leafs.extend(n['switches'].keys())    
        return natsorted(list(set(leafs)))

    def get_nodes(self):
        '''return all the K8s nodes'''
        return natsorted(list(self.topology['nodes'].keys()))
             
    def get_pods(self, ns = None):
        '''return all the pods in all namespaces by default or filtered by ns'''
        pod_names = []
        for node in self.topology['nodes'].keys():
            for pod, v in self.topology['nodes'][node]["pods"].items():
                if ns == None or ns == v["ns"]:
                    pod_names.append(pod)
        return natsorted(pod_names)

    def get_svc(self, ns = None):
        '''return all the service names in all namespaces by default or filtered by ns'''
        service_names = []
        for namespace in self.topology['services'].keys():
            if ns == None or ns == namespace:
                for s in self.topology["services"][namespace]:
                    if s['prefix']:
                        service_names.append(s["name"])
        return natsorted(service_names)

    def get_namespaces(self):
        '''return all the namespaces'''
        namespaces = []
        for node in self.topology['nodes'].keys():
            for k,v in self.topology['nodes'][node]["pods"].items():
                namespaces.append(v["ns"])
        return natsorted(list(set(namespaces)))
        
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

    MERGE (node:Node {name:n.node_name}) ON CREATE
    SET node.ip = n.node_ip, node.mac = n.node_mac

    FOREACH (p IN n.pods | MERGE (pod:Pod {name:p.name}) ON CREATE
    SET pod.ip = p.ip, pod.ns = p.ns 
    MERGE (pod)-[:RUNNING_ON]->(node))

    FOREACH (b IN n.bgp_peers | MERGE (switch: Switch {name:b.name, prefix_count:b.prefix_count}) MERGE (node)-[:PEERED_INTO]->(switch))
    FOREACH (v IN n.vm_hosts | MERGE (vmh:VM_Host {name:v.host_name, description:v.description}) MERGE (node)-[:RUNNING_IN]->(vmh))
    """

    query2 = """
    WITH $json as data
    UNWIND data.items as s
    WITH s, SIZE(s.nodes) as ncount
    UNWIND s.vm_hosts as v
    MATCH (vmh:VM_Host) WHERE vmh.name = v
    MERGE (switch:Switch {name:s.name})
    MERGE (vmh)-[:CONNECTED_TO {interface:s.interface, nodes:s.nodes, node_count:ncount}]->(switch)
    """
    #FOREACH (s IN v.switches | MERGE (switch:Switch {name:s.name}) MERGE (vmh)-[:CONNECTED_TO {interface:s.interface, nodes:s.node}]->(switch)))

    def update_database(self):
        '''Update the neo4j database with the data collected from ACI and K8s'''
        graph = Graph(self.env.neo4j_url, auth=(self.env.neo4j_user, self.env.neo4j_password))
        topology = self.topology.update()
        data, switch_data = self.build_graph_data(topology)

        graph.run("MATCH (n) DETACH DELETE n")
        results = graph.run(self.query,json=data)
        results = graph.run(self.query2,json=switch_data)
        tx = graph.begin()
        graph.commit(tx)

    def build_graph_data(self, topology):
        '''generate the neo4j data to insert in the DB'''
        data = { "items": [] }

        switch_items = {}
        for node in topology['nodes'].keys():
            for neighbour, neighbour_data in topology['nodes'][node]["neighbours"].items():
                for switchName, interfaces in neighbour_data['switches'].items():
                    if switchName not in switch_items.keys():
                        switch_items[switchName] = {"name": switchName, "vm_hosts": [], "interface": "<i>"+" | ".join(list(interfaces))+"</i>", "nodes": []}
                    switch_items[switchName]["nodes"].append(node)
                    switch_items[switchName]["vm_hosts"].append(neighbour)
        switch_data = { "items": list(switch_items.values()) }

        for node in topology['nodes'].keys():
            vm_hosts = []
            for neighbour, neighbour_data in topology['nodes'][node]["neighbours"].items():
                vm_hosts.append({"host_name": neighbour, "description": neighbour_data['Description']})
            
            pods = []
            for pod_name, pod in topology['nodes'][node]["pods"].items():
                pods.append({"name": pod_name, "ip": pod["ip"], "ns": pod["ns"]})
            
            bgp_peers = []
            for peer_name, peer in topology['nodes'][node]["bgp_peers"].items():
                bgp_peers.append({"name": peer_name, "prefix_count": peer["prefix_count"]})

            data["items"].append({
                "node_name": node,
                "node_ip": topology['nodes'][node]["node_ip"],
                "node_mac": topology['nodes'][node]["mac"],
                "pods": pods,
                "vm_hosts": vm_hosts,
                "bgp_peers": bgp_peers
            })
            
        return data, switch_data

class VkaciTable ():
    '''Handle the table view'''
    def __init__(self, topology: VkaciBuilTopology) -> None:
        super().__init__()
        self.topology = topology

    def get_leaf_table(self):
        topology=self.topology.get()
        leafs=self.topology.get_leafs()
        data = { "parent":0, "data": [] }
        for leaf_name in leafs: 
            bgp_peers = []
            vm_hosts = {}
            for node_name, node in topology['nodes'].items():
                if leaf_name in node["bgp_peers"]:
                    bgp_peers.append({"value": node_name, "ip": node["node_ip"], "ns": "", "image":"node.svg"})
                
                for neighbour_name, neighbour in node["neighbours"].items():
                    if leaf_name in neighbour['switches'].keys():
                        pods = []
                        for pod_name, pod in node["pods"].items():
                            pods.append({"value": pod_name, "ip": pod["ip"], "ns": pod["ns"], "image":"pod.svg"})
                        if neighbour_name not in vm_hosts:
                            vm_hosts[neighbour_name] = {"value": neighbour_name, "interface": list(neighbour['switches'][leaf_name]), "ns": "", "image":"esxi.png","data":[]}
                        vm_hosts[neighbour_name]["data"].append({"value": node_name, "ip": node["node_ip"], "ns": "", "image":"node.svg", "data": pods})
            
            leaf_data = list(vm_hosts.values())
            if len(bgp_peers) > 0:
                leaf_data.append({"value": "BGP peering", "image": "bgp.png", "data": bgp_peers})
            data["data"].append({
                "value": leaf_name,
                "ip"   : "",
                "image":"switch.png",
                "data" : leaf_data
            })
        logger.debug("Topology Table View:")
        logger.debug(pformat(data))
        return data 

    def get_svc_name(self, prefix):
        topology=self.topology.get()
        logger.debug('Finding Prexif Name for %s', prefix)
        for ns, svcs in topology['services'].items():
            for svc in svcs:
                if prefix == svc['prefix']:
                    return ns, svc['name']
        return "", ""

    def get_bgp_table(self):
        start = time.time()
        topology=self.topology.get()
        bgp_info=self.topology.get_bgp_info()
        leafs=self.topology.get_leafs()
        data = { "parent":0, "data": [] }
        for leaf_name in leafs: 
            bgp_peers = []
            for node_name, node in topology['nodes'].items():
                if leaf_name in node["bgp_peers"]:
                    bgp_peers.append({"value": node_name, "ip": node["node_ip"], "ns": "", "image":"node.svg"})
            bgp_prefixes = []
            if leaf_name in bgp_info.keys():
                sorted_items = sorted(bgp_info[leaf_name].items())
                for prefix, route in sorted_items:
                    ns, svc_name = self.get_svc_name(prefix)
                    if prefix != "prefix_count":
                        hosts = []
                        for host in route["hosts"]:
                            hosts.append({"value": host["hostname"], "ip": host['ip'], "image":host["image"]})
                        bgp_prefixes.append({"value": prefix, "image": "route.png", "k8s_route": str(
                            route["k8s_route"]), "ns": ns, "svc": svc_name, "data": hosts})
            data["data"].append({
                    "value": leaf_name,
                    "ip"   : "",
                    "image":"switch.png",
                    "data" : [
                        {"value": "BGP Peering", "image": "bgp.png", "data": bgp_peers},
                        {"value": "Prefixes", "image": "ip.png", "data": bgp_prefixes}]
                })
        logger.debug("BGP Table View:")
        logger.debug(pformat(data))
        logger.info("time %s", time.time() - start)
        return data

    def get_node_table(self):
        topology=self.topology.get()
        leafs=self.topology.get_leafs()
        data = { "parent":0, "data": [] }
        for leaf_name in leafs: 
            vm_hosts = {}
            for node_name, node in topology['nodes'].items():
                for neighbour_name, neighbour in node["neighbours"].items():
                    if leaf_name in neighbour['switches'].keys():
                        if neighbour_name not in vm_hosts:
                            vm_hosts[neighbour_name] = {"value": neighbour_name, "interface": list(neighbour['switches'][leaf_name]), "ns": "", "image":"esxi.png","data":[]}
                        vm_hosts[neighbour_name]["data"].append({"value": node_name, "ip": node["node_ip"], "ns": "", "image":"node.svg"})

            if len(vm_hosts) > 0:
                data["data"].append({
                        "value": leaf_name,
                        "ip"   : "",
                        "image":"switch.png",
                        "data" : list(vm_hosts.values())
                    })
        logger.debug("Node Table View:")
        logger.debug(pformat(data))
        return data

    def get_pod_table(self):
        topology=self.topology.get()
        leafs=self.topology.get_leafs()
        data = { "parent":0, "data": [] }
        for leaf_name in leafs: 
            pods = {}
            for node_name, node in topology['nodes'].items():
                 for neighbour_name, neighbour in node["neighbours"].items():
                    if leaf_name in neighbour['switches'].keys():
                        for pod_name, pod in node["pods"].items():
                            pods[pod_name] = {"value": pod_name, "ip": pod["ip"], "ns": pod["ns"], "image":"pod.svg"}
            
            if len(pods) > 0:
                data["data"].append({
                        "value": leaf_name,
                        "ip"   : "",
                        "image":"switch.png",
                        "data" : list(pods.values())
                    })
        logger.debug("Pod Table View:")
        logger.debug(pformat(data))
        return data
