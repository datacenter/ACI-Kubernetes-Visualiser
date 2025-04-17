import json
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
#If you need to look at the API cal


query = """
WITH $json AS data
UNWIND data.items AS n
MERGE (node:Node {name: n.node_name})
ON CREATE SET node.ip = n.node_ip, node.mac = n.node_mac

FOREACH (p IN n.pods | 
    MERGE (pod:Pod {name: p.name})
    ON CREATE SET pod.ip = p.ip, pod.ns = p.ns
    MERGE (pod)-[:RUNNING_ON {interface: p.primary_iface + " "}]->(node)
    FOREACH (l IN p.labels | 
        MERGE (lab:Label {name: l}) 
        MERGE (lab)-[:ATTACHED_TO]->(pod))
    FOREACH (a IN p.annotations | 
        MERGE (ann:Annotations {name: a}) 
        MERGE (ann)-[:ATTACHED_TO]->(pod))
)"""


graph = Graph(self.env.neo4j_url, auth=(self.env.neo4j_user, self.env.neo4j_password))
topology = self.topology.update()
data, switch_data = self.build_graph_data(topology)

graph.run("MATCH (n) DETACH DELETE n")
graph.run(self.query,json=data)