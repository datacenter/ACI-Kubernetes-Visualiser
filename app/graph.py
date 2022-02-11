#!/usr/local/bin/python3
import os
import re
from kubernetes import client, config
from pyaci import Node, options, filters
import random
import pygraphviz as pgv
import logging
import concurrent.futures
import time

#If you need to look at the API calls this is what you do
#logging.basicConfig(level=logger.info)
#logging.getLogger('pyaci').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-1s %(levelname)-1s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class vkaci_env_variables(object):
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

    def enviro(self):
        if self.dict_env == None:
            return os.environ
        else:
            return self.dict_env

class apic_methods_resolve(object):
    def __init__(self) -> None:
        super().__init__()
        
    def get_fvcep(self, apic: Node, aci_vrf: str): 
        return apic.methods.ResolveClass('fvCEp').GET(**options.rspSubtreeChildren & options.subtreeFilter(filters.Eq('fvIp.vrfDn', aci_vrf)))

    def get_fvcep_mac(self, apic: Node, mac: str): 
        return apic.methods.ResolveClass('fvCEp').GET(**options.filter(filters.Eq('fvCEp.mac', mac)) & options.rspSubtreeClass('fvRsCEpToPathEp'))[0]

    def get_lldpif(self, apic:Node, pathDn): 
        return apic.methods.ResolveClass('lldpIf').GET(**options.filter(filters.Eq('lldpIf.portDesc',pathDn)) & options.rspSubtreeClass('lldpAdjEp'))

    def get_bgppeerentry(self, apic:Node, vrf: str, node_ip: str): 
        return apic.methods.ResolveClass('bgpPeerEntry').GET(**options.filter(filters.Wcard('bgpPeerEntry.dn', vrf) & filters.Eq('bgpPeerEntry.addr', node_ip)))
    

class vkaci_build_topology(object):
    def __init__(self, env:vkaci_env_variables, apic_methods:apic_methods_resolve) -> None:
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
            logger.error("Invalid Mode, %s. Only LOCAL or CLUSTER is supported." % self.env.mode)
        
        #
        self.v1 = client.CoreV1Api()

    def is_local_mode(self): 
        return self.env.mode.casefold() == "LOCAL".casefold()

    def is_cluster_mode(self): 
        return self.env.mode.casefold() == "CLUSTER".casefold()

    def update_node(self, apic, node):

        # double filter is very slow, not sure why but retuirning all the enpoints and child is 
        #ep = apic.methods.ResolveClass('fvCEp').GET(**options.rspSubtreeChildren & 
        #                                            options.subtreeFilter(filters.Eq('fvIp.vrfDn',self.aci_vrf) & filters.Eq('fvIp.addr', node['node_ip'])))
        #if len(ep) > 1:
        #    logger.info("Detected Duplicate node IP {} with Macs".format(node['node_ip']))
        #    for i in ep:
        #        logger.info(i.mac)
        #    logger.info("Terminating")
        #    exit()
        #elif len(ep) == 0:
        #    logger.info("No nodes found, please check that the Tenant {} and VRF {} are correct".format(self.tenant, self.vrf))
        #else:
        #    ep = ep[0]
        
        #Find the mac to interface mapping 
        path =  self.apic_methods.get_fvcep_mac(apic, node['mac'])
        
        #Get Path, there should be only one...need to add checks
        for fvRsCEpToPathEp in path.fvRsCEpToPathEp:
            pathtDn = fvRsCEpToPathEp.tDn

        #logger.info("The K8s Node is physically connected to: {}".format(pathtDn))
        #Get all LLDP Neighbors for that interface
        lldp_neighbours = self.apic_methods.get_lldpif(apic, pathtDn)

        for lldp_neighbour in lldp_neighbours:
            if lldp_neighbour.operRxSt == "up" and lldp_neighbour.operTxSt == 'up':

                # Get the LLD Host that shoudl be either the same as the K8s node or a Hypervisor host name. 

                for lldp_neighbour_hostname in lldp_neighbour.lldpAdjEp:
                    if lldp_neighbour_hostname.sysName not in node['lldp_neighbours'].keys():
                        node['lldp_neighbours'][lldp_neighbour_hostname.sysName] = {}

                # Get the switch name and remove the topology and POD-1 topology/pod-1/node-204
                switch = lldp_neighbour.sysDesc.split('/')[2].replace("node", "leaf")
                if switch not in node['lldp_neighbours'][lldp_neighbour_hostname.sysName].keys() and lldp_neighbour_hostname:
                    # Add the swithc ID as a key and create a set to hold the interfaces this shoudl be uniqe and I do not need to be an dictionary.
                    node['lldp_neighbours'][lldp_neighbour_hostname.sysName][switch] = set()

            # lldp_neighbour.id == Interface ID 
                    
                node['lldp_neighbours'][lldp_neighbour_hostname.sysName][switch].add(lldp_neighbour.id)

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
        
        self.topology = { }
        self.apics = []
        
        # Check APIC Ips
        if self.env.apic_ip is None or len(self.env.apic_ip) == 0:
            logger.error("Invalid APIC IP addresses.")
            return

        #Create list of APICs and set the useX509CertAuth parameters
        for i in self.env.apic_ip:
            self.apics.append(Node('https://' + i))
        for apic in self.apics:
            if self.is_local_mode():
                apic.useX509CertAuth(self.env.cert_user, self.env.cert_name, self.env.key_path)
            elif self.is_cluster_mode():
                apic.useX509CertAuth(self.env.cert_user, self.env.cert_name, '/usr/local/etc/aci-cert/user.key')
            else:
                logger.error("MODE can only be LOCAL or CLUSTER but {} was given".format(self.env.mode))
                return
        
        ##Load all the POD and Nodes in Memory. 
        ret = self.v1.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            if i.spec.node_name not in self.topology.keys():
               self.topology[i.spec.node_name] = { "node_ip": i.status.host_ip, "pods" : {}, 'bgp_peers': set(), 'lldp_neighbours': {} }
            self.topology[i.spec.node_name]['pods'][i.metadata.name] = {"ip": i.status.pod_ip, "ns": i.metadata.namespace}
        
        start = time.time()
        #Get all the mac and ips in the Cluster VRF, and map the node_ip to Mac. This is faster done locally. The same query where I filter by IP and VRF takes 0.4s per node
        # Dumping 900 EPs takes 1.3s in total. 
        eps = self.apic_methods.get_fvcep(self.apics[0], self.aci_vrf)
        logger.info("ACI EP completed after: {} seconds".format(time.time() - start))
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
        #logger.info("Topology:")
        #logger.info(self.topology)
        return self.topology

    def get(self):
        return self.topology
#There is too much data to visualize in a single graph so we have a few options:

class vkaci_draw(object):
    def __init__(self, topology) -> None:
        super().__init__()
        self.gRoot = pgv.AGraph(directed=True)
        self.gBgpPeers = self.gRoot.add_subgraph(name='BgpPeers')
        self.gLldpHost = self.gRoot.add_subgraph(name='LldpHost', rank ='same')
        self.gLldpSwitch = self.gRoot.add_subgraph(name='LldpSwitch', rank ='same')
        self.gLldpAdj = self.gRoot.add_subgraph(name='LldpAdj')
        self.gK8sNodes = self.gRoot.add_subgraph(name='K8sNodes', rank ='same')
        self.gPods = self.gRoot.add_subgraph(name='Pods', rank ='min')
        self.gPodsToNodes = self.gRoot.add_subgraph(name='PodsToNodes')
        self.gBgpPeering = self.gRoot.add_subgraph(name='BgpPeering')
        self.topology = topology

    def add_node(self, node, nodeV, pods):
        self.gK8sNodes.add_node(node, tooltip="Pods on the node:\n" + pods, label = node + '\n' + nodeV['node_ip'])
        for bgp_peer in nodeV['bgp_peers']:
            ebgpNodeName = 'eBGP Peer\n' + bgp_peer
            self.gBgpPeers.add_node(ebgpNodeName, shape='box')
            self.gBgpPeering.add_edge(node,ebgpNodeName,style='dotted',color='red', tooltip='eBGP Peering' )
        for lldp_host, lldpV in nodeV['lldp_neighbours'].items():
            self.gLldpHost.add_node(lldp_host)
            self.gLldpAdj.add_edge(node,lldp_host, color='blue')
            for switch, interface in lldpV.items():
                self.gLldpSwitch.add_node(switch, shape='box')
                self.gLldpAdj.add_edge(lldp_host, switch, color='blue', tooltip='\n'.join(map(str, list(interface))))
    
    def add_nodes(self):
        for node, nodeV in self.topology.items():
            pods = '\n'.join(map(str, list(nodeV['pods'].keys())))
            self.add_node(node, nodeV,pods)
            
    def add_pod(self, pod_name):
        for node, nodeV in self.topology.items():
            if pod_name in nodeV['pods'].keys():
                pods = '\n'.join(map(str, list(nodeV['pods'].keys())))
                self.add_node(node, nodeV,pods)
                self.gPods.add_node(pod_name, label=pod_name + '\n ip=' + nodeV['pods'][pod_name]['ip'] + '\n ns=' + nodeV['pods'][pod_name]['ns'])
                self.gPodsToNodes.add_edge(pod_name,node)
        if self.gPods.number_of_nodes() == 0:
            self.gRoot.clear()
            if not pod_name:
                pod_name = "Pod Name Not Specified"
                # THis is the graphiz add_node function :D 
                self.gRoot.add_node(pod_name, label=pod_name +'\nNOT FOUND')
            else:
                self.gRoot.add_node(pod_name, label=pod_name +'\nNOT FOUND')

            
    
    def svg(self, fn):
        #logger.info(self.gRoot.string())
        self.gRoot.layout("dot")  # layout with dot
        self.gRoot.draw(fn + ".svg")  # write to file
    
    def get_gRoot(self):
        return self.gRoot

