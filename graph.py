#!/usr/local/bin/python3
import sys
import os
import re
from kubernetes import client, config
from pyaci import Node
from pyaci import options
from pyaci import filters
import random
import logging
import pygraphviz as pgv
from pprint import pprint

def find_key(obj, key):
    if key in obj: return obj[key]
    for k, v in obj.items():
        if isinstance(v,dict):
            item = find_key(v, key)
            if item is not None:
                return True

#If you need to look at the API calls this is what you do
#logging.basicConfig(level=logging.INFO)
#logging.getLogger('pyaci').setLevel(logging.DEBUG)
if len(sys.argv) != 2:
    print("This commands takes only one argument, the pod name")
    exit()

#pod_name= sys.argv[1]
pod = {}

topology = {}

apic_ip="10.67.185.102,10.67.185.42,10.67.185.41".split(',')
tenant = 'common'
vrf = 'calico'

aci_vrf = 'uni/tn-' + tenant + '/ctx-' + vrf
apic = Node('https://' + random.choice(apic_ip))
apic.useX509CertAuth("ansible","ansible.crt",'/home/cisco/Coding/ansible.key')

## Configs can be set in Configuration class directly or using helper utility
config.load_kube_config(config_file="/home/cisco/.kube/config")
##config.load_incluster_config()
#
v1 = client.CoreV1Api()
ret = v1.list_pod_for_all_namespaces(watch=False)
##Load all the POD in Memory. 
for i in ret.items:
    #pod[i.metadata.name] = {"ip": i.status.pod_ip, "ns": i.metadata.namespace, "node_ip": i.status.host_ip, "node_name": i.spec.node_name }
    if i.spec.node_name not in topology.keys():
       topology[i.spec.node_name] = { "node_ip": i.status.host_ip, "pods" : {}, 'bgp_peers': set(), 'lldp_neighbours': {} }
    topology[i.spec.node_name]['pods'][i.metadata.name] = {"ip": i.status.pod_ip, "ns": i.metadata.namespace}

 #Find the K8s Node IP/Mac
for k,v in topology.items():
    ep = apic.methods.ResolveClass('fvCEp').GET(**options.rspSubtreeChildren & 
                                            options.subtreeFilter(filters.Eq('fvIp.addr', v['node_ip']) & filters.Eq('fvIp.vrfDn',aci_vrf)))
    if len(ep) > 1:
        print("Detected Duplicate node IP {} with Macs".format(v['node_ip']))
        for i in ep:
            print(i.mac)
        print("Terminating")
        exit()
    else:
        ep = ep[0]
    #Find the mac to interface mapping 
    path = apic.methods.ResolveClass('fvCEp').GET(**options.filter(filters.Eq('fvCEp.mac', ep.mac)) & options.rspSubtreeClass('fvRsCEpToPathEp'))[0]

    #Get Path, there should be only one...need to add checks
    for fvRsCEpToPathEp in path.fvRsCEpToPathEp:
        pathtDn = fvRsCEpToPathEp.tDn

    #print("The K8s Node is physically connected to: {}".format(pathtDn))
    #Get all LLDP Neighbors for that interface
    lldp_neighbours = apic.methods.ResolveClass('lldpIf').GET(**options.filter(filters.Eq('lldpIf.portDesc',pathtDn)) & options.rspSubtreeClass('lldpAdjEp'))
    for lldp_neighbour in lldp_neighbours:
        
        # Get the LLD Host that shoudl be either the same as the K8s node or a Hypervisor host name. 
        
        for lldp_neighbour_hostname in lldp_neighbour.lldpAdjEp:
            if lldp_neighbour_hostname.sysName not in v['lldp_neighbours'].keys():
                v['lldp_neighbours'][lldp_neighbour_hostname.sysName] = {}
        
        # Get the switch name and remove the topology and POD-1 topology/pod-1/node-204
        switch = lldp_neighbour.sysDesc.split('/')[2]
        if switch not in v['lldp_neighbours'][lldp_neighbour_hostname.sysName].keys():
            # Add the swithc ID as a key and create a set to hold the interfaces this shoudl be uniqe and I do not need to be an dictionary.
            v['lldp_neighbours'][lldp_neighbour_hostname.sysName][switch] = set()
        
        # lldp_neighbour.id == Interface ID
        v['lldp_neighbours'][lldp_neighbour_hostname.sysName][switch].add(lldp_neighbour.id)
    
        #Find the BGP Peer for the K8s Nodes, here I need to know the VRF of the K8s Node so that I can find the BGP entries in the right VRF. 
        # This is important as we might have IP reused in different VRFs. Luckilly the EP info has the VRF in it. 
        # The VRF format is  uni/tn-common/ctx-calico and we care about the tenant and ctx so we can split by / and - to get ['uni', 'tn', 'common', 'ctx', 'calico']
        #and extract the common and calico part. 
        vrf=re.split('/|-',ep.vrfDn)
        vrf = '.*/dom-' + vrf[2] + ':' + vrf[4] + '/.*'
        bgpPeerEntry = apic.methods.ResolveClass('bgpPeerEntry').GET(**options.filter(filters.Wcard('bgpPeerEntry.dn', vrf) & filters.Eq('bgpPeerEntry.addr',v['node_ip'])))
        for bgpPeer in bgpPeerEntry:
            v['bgp_peers'].add( bgpPeer.dn.split("/")[2] )
        
pprint(topology)




exit()
#try: 
#    print("Looking for pod {} with IP {} on node {}/{}".format(pod_name, pod[pod_name]['ip'], pod[pod_name]['node_ip'], pod[pod_name]['node_name'] ))
#except:
#    print("Pod does noex exist")
#    exit()
for pod_name in pod.keys():
    #If I already know the node_name I already built the LLDP adjagency and there is no need to query the APIC again!
    # I can't do recursion to check if a FUCKINHG FGOIEH KEY EXISTS   in a FUCKING PIECE OF SHIT OF A DICRTIONTUREY{WODU}       
    print(pod[pod_name]['node_name']) 
    print(find_key(topology, pod[pod_name]['node_name']))

    if find_key(topology, pod[pod_name]['node_name']) == None:
        #Find the K8s Node IP/Mac
        ep = apic.methods.ResolveClass('fvCEp').GET(**options.rspSubtreeChildren & 
                                                    options.subtreeFilter(filters.Eq('fvIp.addr', pod[pod_name]['node_ip'])))[0]

        #Find the mac to interface mapping 
        path = apic.methods.ResolveClass('fvCEp').GET(**options.filter(filters.Eq('fvCEp.mac', ep.mac)) & options.rspSubtreeClass('fvRsCEpToPathEp'))[0]

        #Get Path, there should be only one...need to add checks
        for fvRsCEpToPathEp in path.fvRsCEpToPathEp:
            pathtDn = fvRsCEpToPathEp.tDn

        #print("The K8s Node is physically connected to: {}".format(pathtDn))
        #Get all LLDP Neighbors for that interface
        lldp_neighbours = apic.methods.ResolveClass('lldpIf').GET(**options.filter(filters.Eq('lldpIf.portDesc',pathtDn)) & options.rspSubtreeClass('lldpAdjEp'))

        #print("LLDP Infos:")
        for lldp_neighbour in lldp_neighbours:
           # print("\t {} {}".format(lldp_neighbour.sysDesc, lldp_neighbour.id))
            # sysDesc should look like this: topology/pod-1/node-204 so I am gonna go down this tree
            # Not sure how multi tier wold look like... as I do nto have a multi tier setup
            node = lldp_neighbour.sysDesc.split('/')[2]
            
            # If the node does not exist add a new key
            if node not in topology.keys():
                topology[node] = {}
            
            # If the aci node (switch) interface does not exists add a new interface ID as a key.
            if lldp_neighbour.id not in topology[node].keys():
                topology[node][lldp_neighbour.id] = {}
            
            # If the lldp neighbour hostname does not exists add a new neighbour key. I can have multiple neighbours so I need to loop over all of them.
            # THe LLDP neighbour in my case is the ESXi host where the K8s node works. If there is no virtualization then the LLDP neighbour and the k8s node name will be the same.
            # Will have to test this a bit more.
            for neighbour in lldp_neighbour.lldpAdjEp:
                neighbour.sysName = neighbour.sysName.split('.')[0]
                if neighbour.sysName not in topology[node][lldp_neighbour.id].keys():
                    topology[node][lldp_neighbour.id][neighbour.sysName] = {}
            
            ## If the K8s nodes does not exists add a new node name as a key.
            #print('inserted node {}'.format(pod[pod_name]['node_name']))
            if pod[pod_name]['node_name'] not in topology[node][lldp_neighbour.id][neighbour.sysName].keys():
                topology[node][lldp_neighbour.id][neighbour.sysName][pod[pod_name]['node_name']] = {'node_ip': pod[pod_name]['node_ip']}
            #
            if pod[pod_name]['ip'] not in topology[node][lldp_neighbour.id][neighbour.sysName][pod[pod_name]['node_name']].keys():
                topology[node][lldp_neighbour.id][neighbour.sysName][pod[pod_name]['node_name']][pod_name] = {'pod_ip': pod[pod_name]['ip']} 
        
        #Find the BGP Peer for the K8s Nodes
        bgpPeerEntry = apic.methods.ResolveClass('bgpPeerEntry').GET(**options.filter(filters.Wcard('bgpPeerEntry.dn', '.*/dom-common:calico/.*') & filters.Eq('bgpPeerEntry.addr',pod[pod_name]['node_ip'])))
        for bgpPeer in bgpPeerEntry:
            if 'bgp_peer' not in topology[node][lldp_neighbour.id][neighbour.sysName][pod[pod_name]['node_name']].keys():
                topology[node][lldp_neighbour.id][neighbour.sysName][pod[pod_name]['node_name']] = {'bgp_peer': set() }
            topology[node][lldp_neighbour.id][neighbour.sysName][pod[pod_name]['node_name']]['bgp_peer'].add( bgpPeer.dn.split("/")[2] )
    
pprint(topology)

