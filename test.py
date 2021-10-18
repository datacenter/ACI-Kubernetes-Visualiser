#!/usr/local/bin/python3
from re import L
import sys
import os
from pyaci import Node
from pyaci import options
from pyaci import filters
import random
import logging
from pprint import pprint
import json

import pygraphviz as pgv
from six import add_metaclass



topology = {'master-1': {'bgp_peers': {'node-204', 'node-203'},
              'lldp_neighbours': {'esxi4.cam.ciscolabs.com': {'node-203': {'eth1/1'},
                                                              'node-204': {'eth1/1'}}},
              'node_ip': '192.168.2.1',
              'pods': {'calico-node-2nnv2': {'ip': '192.168.2.1',
                                             'ns': 'kube-system'},
                       'coredns-78fcd69978-4jgvj': {'ip': '10.1.39.3',
                                                    'ns': 'kube-system'},
                       'coredns-78fcd69978-vk4x9': {'ip': '10.1.39.4',
                                                    'ns': 'kube-system'},
                       'etcd-master-1': {'ip': '192.168.2.1',
                                         'ns': 'kube-system'},
                       'haproxy-master-1': {'ip': '192.168.2.1',
                                            'ns': 'kube-system'},
                       'keepalived-master-1': {'ip': '192.168.2.1',
                                               'ns': 'kube-system'},
                       'kube-apiserver-master-1': {'ip': '192.168.2.1',
                                                   'ns': 'kube-system'},
                       'kube-controller-manager-master-1': {'ip': '192.168.2.1',
                                                            'ns': 'kube-system'},
                       'kube-proxy-bnjn7': {'ip': '192.168.2.1',
                                            'ns': 'kube-system'},
                       'kube-scheduler-master-1': {'ip': '192.168.2.1',
                                                   'ns': 'kube-system'}}},
 'master-2': {'bgp_peers': {'node-201', 'node-202'},
              'lldp_neighbours': {'esxi4.cam.ciscolabs.com': {'node-203': {'eth1/1'},
                                                              'node-204': {'eth1/1'}}},
              'node_ip': '192.168.2.2',
              'pods': {'calico-node-479nk': {'ip': '192.168.2.2',
                                             'ns': 'kube-system'},
                       'etcd-master-2': {'ip': '192.168.2.2',
                                         'ns': 'kube-system'},
                       'haproxy-master-2': {'ip': '192.168.2.2',
                                            'ns': 'kube-system'},
                       'keepalived-master-2': {'ip': '192.168.2.2',
                                               'ns': 'kube-system'},
                       'kube-apiserver-master-2': {'ip': '192.168.2.2',
                                                   'ns': 'kube-system'},
                       'kube-controller-manager-master-2': {'ip': '192.168.2.2',
                                                            'ns': 'kube-system'},
                       'kube-proxy-p8bj6': {'ip': '192.168.2.2',
                                            'ns': 'kube-system'},
                       'kube-scheduler-master-2': {'ip': '192.168.2.2',
                                                   'ns': 'kube-system'}}},
 'master-3': {'bgp_peers': {'node-204', 'node-203'},
              'lldp_neighbours': {'esxi5': {'node-203': {'eth1/2'},
                                            'node-204': {'eth1/2'}}},
              'node_ip': '192.168.2.3',
              'pods': {'calico-node-g5rx7': {'ip': '192.168.2.3',
                                             'ns': 'kube-system'},
                       'etcd-master-3': {'ip': '192.168.2.3',
                                         'ns': 'kube-system'},
                       'haproxy-master-3': {'ip': '192.168.2.3',
                                            'ns': 'kube-system'},
                       'keepalived-master-3': {'ip': '192.168.2.3',
                                               'ns': 'kube-system'},
                       'kube-apiserver-master-3': {'ip': '192.168.2.3',
                                                   'ns': 'kube-system'},
                       'kube-controller-manager-master-3': {'ip': '192.168.2.3',
                                                            'ns': 'kube-system'},
                       'kube-proxy-7dtmj': {'ip': '192.168.2.3',
                                            'ns': 'kube-system'},
                       'kube-scheduler-master-3': {'ip': '192.168.2.3',
                                                   'ns': 'kube-system'}}},
 'worker-1': {'bgp_peers': {'node-201', 'node-202'},
              'lldp_neighbours': {'esxi5': {'node-203': {'eth1/2'},
                                            'node-204': {'eth1/2'}}},
              'node_ip': '192.168.2.4',
              'pods': {'calico-node-gnc84': {'ip': '192.168.2.4',
                                             'ns': 'kube-system'},
                       'dashboard-metrics-scraper-856586f554-ncskt': {'ip': '10.1.226.65',
                                                                      'ns': 'kubernetes-dashboard'},
                       'frontend-d7f77b577-fhsv8': {'ip': '10.1.226.67',
                                                    'ns': 'guestbook'},
                       'frontend-d7f77b577-ps7hp': {'ip': '10.1.226.66',
                                                    'ns': 'gb'},
                       'kube-proxy-dqn74': {'ip': '192.168.2.4',
                                            'ns': 'kube-system'}}},
 'worker-2': {'bgp_peers': {'node-204', 'node-203'},
              'lldp_neighbours': {'esxi5': {'node-203': {'eth1/2'},
                                            'node-204': {'eth1/2'}}},
              'node_ip': '192.168.2.5',
              'pods': {'calico-node-wx5k7': {'ip': '192.168.2.5',
                                             'ns': 'kube-system'},
                       'kube-proxy-tkxhk': {'ip': '192.168.2.5',
                                            'ns': 'kube-system'},
                       'redis-slave-5ff8876b77-blrpb': {'ip': '10.1.133.199',
                                                        'ns': 'gb'},
                       'redis-slave-5ff8876b77-cm44w': {'ip': '10.1.133.200',
                                                        'ns': 'guestbook'}}},
 'worker-3': {'bgp_peers': {'node-201', 'node-202'},
              'lldp_neighbours': {'esxi4.cam.ciscolabs.com': {'node-203': {'eth1/1'},
                                                              'node-204': {'eth1/1'}}},
              'node_ip': '192.168.2.6',
              'pods': {'calico-node-5cmhf': {'ip': '192.168.2.6',
                                             'ns': 'kube-system'},
                       'frontend-d7f77b577-hdvj8': {'ip': '10.1.97.194',
                                                    'ns': 'gb'},
                       'frontend-d7f77b577-lv6vc': {'ip': '10.1.97.196',
                                                    'ns': 'guestbook'},
                       'kube-proxy-42m9c': {'ip': '192.168.2.6',
                                            'ns': 'kube-system'},
                       'redis-master-84777845f-tqlmc': {'ip': '10.1.97.195',
                                                        'ns': 'gb'}}},
 'worker-4': {'bgp_peers': {'node-204', 'node-203'},
              'lldp_neighbours': {'esxi5': {'node-203': {'eth1/2'},
                                            'node-204': {'eth1/2'}}},
              'node_ip': '192.168.2.7',
              'pods': {'busybox-6c446876c6-9gfxz': {'ip': '10.1.38.67',
                                                    'ns': 'default'},
                       'calico-kube-controllers-58497c65d5-4z9k9': {'ip': '10.1.38.65',
                                                                    'ns': 'kube-system'},
                       'calico-node-cl2tw': {'ip': '192.168.2.7',
                                             'ns': 'kube-system'},
                       'kube-proxy-djlwt': {'ip': '192.168.2.7',
                                            'ns': 'kube-system'},
                       'redis-slave-5ff8876b77-jr6w4': {'ip': '10.1.38.66',
                                                        'ns': 'guestbook'}}},
 'worker-5': {'bgp_peers': {'node-201', 'node-202'},
              'lldp_neighbours': {'esxi4.cam.ciscolabs.com': {'node-203': {'eth1/1'},
                                                              'node-204': {'eth1/1'}}},
              'node_ip': '192.168.2.8',
              'pods': {'calico-node-2d47r': {'ip': '192.168.2.8',
                                             'ns': 'kube-system'},
                       'calico-typha-68857595fc-lr6d5': {'ip': '192.168.2.8',
                                                         'ns': 'kube-system'},
                       'kube-proxy-tdwl5': {'ip': '192.168.2.8',
                                            'ns': 'kube-system'},
                       'redis-master-84777845f-fn2kr': {'ip': '10.1.203.3',
                                                        'ns': 'guestbook'}}},
 'worker-6': {'bgp_peers': {'node-204', 'node-203'},
              'lldp_neighbours': {'esxi4.cam.ciscolabs.com': {'node-203': {'eth1/1'},
                                                              'node-204': {'eth1/1'}}},
              'node_ip': '192.168.2.9',
              'pods': {'calico-node-rm98z': {'ip': '192.168.2.9',
                                             'ns': 'kube-system'},
                       'frontend-d7f77b577-cvqp4': {'ip': '10.1.183.4',
                                                    'ns': 'guestbook'},
                       'frontend-d7f77b577-xvkqz': {'ip': '10.1.183.2',
                                                    'ns': 'gb'},
                       'kube-proxy-tj47m': {'ip': '192.168.2.9',
                                            'ns': 'kube-system'},
                       'redis-slave-5ff8876b77-ncrtz': {'ip': '10.1.183.3',
                                                        'ns': 'gb'}}},
 'worker-7': {'bgp_peers': {'node-201', 'node-202'},
              'lldp_neighbours': {'esxi5': {'node-203': {'eth1/2','eth1/3'},
                                            'node-204': {'eth1/2'}}},
              'node_ip': '192.168.2.10',
              'pods': {'calico-node-jcrg8': {'ip': '192.168.2.10',
                                             'ns': 'kube-system'},
                       'kube-proxy-5g8lc': {'ip': '192.168.2.10',
                                            'ns': 'kube-system'},
                       'kubernetes-dashboard-78c79f97b4-nntv8': {'ip': '10.1.40.192',
                                                                 'ns': 'kubernetes-dashboard'},
                       'vkaci': {'ip': '10.1.40.195', 'ns': 'default'}}}}

#There is too much data to visualize in a single graph so we have a few options:

class vkaci_topology(object):
    def __init__(self) -> None:
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
        for node, nodeV in topology.items():
            pods = '\n'.join(map(str, list(nodeV['pods'].keys())))
            self.add_node(node, nodeV,pods)
            
    def add_pod(self, pod_name):
        for node, nodeV in topology.items():
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
        print(self.gRoot.string())
        self.gRoot.layout("dot")  # layout with dot
        self.gRoot.draw(fn + ".svg")  # write to file
    
    
    
    
    #add_nodes(topology)
#svg('template/assets/cluster')

#gRoot = pgv.AGraph(directed=True)
#gBgpPeers = gRoot.add_subgraph(name='BgpPeers')
#gLldpHost = gRoot.add_subgraph(name='LldpHost', rank ='same')
#gLldpSwitch = gRoot.add_subgraph(name='LldpSwitch', rank ='same')
#gLldpAdj = gRoot.add_subgraph(name='LldpAdj')
#gK8sNodes = gRoot.add_subgraph(name='K8sNodes', rank ='same')
#gPods = gRoot.add_subgraph(name='Pods', rank ='min')
#gPodsToNodes = gRoot.add_subgraph(name='PodsToNodes')
#gBgpPeering = gRoot.add_subgraph(name='BgpPeering')

#add_pod(topology,'vkaci')
#svg('template/assets/pod')