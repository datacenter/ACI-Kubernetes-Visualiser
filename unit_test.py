import unittest
from pyaci import Node, core
from unittest.mock import patch, MagicMock
from kubernetes import client
from app.graph import ApicMethodsResolve, VkaciBuilTopology, VkaciEnvVariables, VkaciTable

core.aciClassMetas = {"topRoot": {
    "properties": {}, "rnFormat": "something"}}

# Fake k8s cluster data
pods = [
    client.V1Pod(
        status=client.V1PodStatus(
            host_ip="192.168.1.2", pod_ip="192.158.1.3"
        ),
        metadata=client.V1ObjectMeta(
            name="dateformat", namespace="dockerimage"
        ),
        spec=client.V1PodSpec(
            node_name="1234abc", containers=[]
        )
    )
]


class Expando(object):
    pass


class MockMo(object):
    def __init__(self, ip, mac, pathtDn) -> None:
        self.mac = mac
        self.fvRsCEpToPathEp = [Expando()]
        c = Expando()
        c.addr = ip
        self.Children = [c]
        self.fvRsCEpToPathEp[0].tDn = pathtDn


def create_lldp_neighbour(on: bool = True):
    n = Expando()
    n.operTxSt = n.operRxSt = "down"
    if (on):
        n.operTxSt = n.operRxSt = "up"
        n.lldpAdjEp = [Expando()]
        n.lldpAdjEp[0].sysName = "esxi4.cam.ciscolabs.com"
        n.lldpAdjEp[0].chassisIdV = "vmxnic1"
        n.sysDesc = n.dn = "topology/pod-1/node-204"
        n.id = "eth1/1"
    return n


def create_cdp_neighbour(on: bool = False):
    n = Expando()
    n.operSt = "down"
    if (on):
        n.operSt = "up"
        n.cdpAdjEp = [Expando()]
        n.cdpAdjEp[0].sysName = "esxi5"
        n.cdpAdjEp[0].chassisIdV = "vmxnic2"
        n.sysDesc = n.dn = "topology/pod-1/node-203"
        n.id = "eth1/1"
    return n


def create_cdp_no_neighbour(on: bool = False):
    n = Expando()
    n.operSt = "down"
    if (on):
        n.operSt = "up"
        n.cdpAdjEp = []
        n.sysDesc = n.dn = "topology/pod-1/node-203"
        n.id = "eth1/1"
    return n


def create_bgpPeer():
    b = Expando()
    b.operSt = "established"
    b.dn = "topology/pod-1/node-204"
    return b

def create_nextHop(route:str, next_hop:str, tag = "56001"):
    h = Expando()
    h.dn = "topology/pod-1/node-204/sys/uribv4/dom-calico1:vrf/db-rt/rt-["+route+"]/nh-[bgp-65002]-["+next_hop+"/32]-[unspecified]-[calico1:vrf]"
    h.addr = next_hop+"/32"
    h.tag = tag
    return h

class ApicMethodsMock(ApicMethodsResolve):
    def __init__(self) -> None:
        super().__init__()

    mo1 = MockMo("192.168.1.2", "MOCKMO1C", "pathA")
    eps = [mo1]

    lldps = [create_lldp_neighbour()]
    cdpns = [create_cdp_neighbour()]
    bgpPeers = [create_bgpPeer()]
    nextHops = [
        create_nextHop("192.168.5.1/32", "192.168.2.5"),
        create_nextHop("192.168.5.1/32", "192.168.1.2"),
        create_nextHop("0.0.0.0/0", "10.4.68.5", "65002")
        ]

    def get_fvcep(self, apic: Node, aci_vrf: str):
        return self.eps

    def get_fvcep_mac(self, apic: Node, mac: str):
        return self.eps[0]

    def get_lldpif(self, apic: Node, pathDn):
        return self.lldps

    def get_cdpif(self, apic: Node, pathDn):
        return self.cdpns

    def get_bgppeerentry(self, apic: Node, vrf: str, node_ip: str):
        return self.bgpPeers

    def get_all_nexthops(self, apic:Node, dn:str):
        return self.nextHops
    
    def path_fixup(self, apic:Node, path):
        return path
    
    def get_overlay_ip_to_switch_map(self, apic:Node):
        nodes = {"192.168.2.5":"leaf 203"}
        return nodes

@patch('kubernetes.config.load_incluster_config', MagicMock(return_value=None))
@patch('pyaci.Node.useX509CertAuth', MagicMock(return_value=None))
@patch('kubernetes.client.CoreV1Api.list_pod_for_all_namespaces', MagicMock(return_value=client.V1PodList(api_version="1", items=pods)))
@patch('kubernetes.client.CustomObjectsApi.get_cluster_custom_object', MagicMock(return_value={'spec': {'asNumber': 56001}}))
class TestVkaciGraph(unittest.TestCase):

    vars = {"APIC_IPS": "192.168.25.192,192.168.1.2",
            "TENANT": "Ciscolive",
            "VRF": "vrf-01",
            "MODE": "cluster",
            "KUBE_CONFIG": "$HOME/.kube/config",
            "CERT_USER": "useX509",
            "CERT_NAME": "test",
            "KEY_PATH": " 101/1/1-2"
            }

    def test_no_env_variables(self):
        """Test that no environment variables are handled"""
        # Arange
        build = VkaciBuilTopology(
            VkaciEnvVariables({}), ApicMethodsMock())
        # Act
        result = build.update()
        # Assert
        self.assertIsNone(result)
        self.assertEqual(build.env.mode, 'None')
        self.assertIsNone(build.aci_vrf)
        self.assertEqual(len(build.env.apic_ip), 0)


    def test_valid_topology(self):
        """Test that a valid topology is created"""
        # Arrange
        expected = {'1234abc': {'node_ip': '192.168.1.2', 'pods': {'dateformat': {
            'ip': '192.158.1.3', 'ns': 'dockerimage'}}, 'bgp_peers': {'leaf-204':{'prefix_count': 2}}, 'neighbours': {'esxi4.cam.ciscolabs.com': {'leaf-204': {'vmxnic1-eth1/1'}}}, 'mac': 'MOCKMO1C'}}

        build = VkaciBuilTopology(
            VkaciEnvVariables(self.vars), ApicMethodsMock())
        # Act
        result = build.update()
        # Assert
        self.assertDictEqual(result, expected)
        self.assertEqual(build.aci_vrf, "uni/tn-Ciscolive/ctx-vrf-01")


    def test_valid_topology_cdpn(self):
        """Test that a valid topology is created with cdp neighbours"""
        # Arrange
        expected = {'1234abc': {'node_ip': '192.168.1.2', 'pods': {'dateformat': {
            'ip': '192.158.1.3', 'ns': 'dockerimage'}}, 'bgp_peers': {'leaf-204':{'prefix_count': 2}}, 'neighbours': {'esxi5': {'leaf-203': {'vmxnic2-eth1/1'}}}, 'mac': 'MOCKMO1C'}}

        mock = ApicMethodsMock()
        mock.lldps = [create_lldp_neighbour(False)]
        mock.cdpns = [create_cdp_neighbour(True)]
        build = VkaciBuilTopology(
            VkaciEnvVariables(self.vars), mock)
        # Act
        result = build.update()
        # Assert
        self.assertDictEqual(result, expected)
        self.assertEqual(build.aci_vrf, "uni/tn-Ciscolive/ctx-vrf-01")


    def test_valid_topology_no_neighbours(self):
        """Test that a valid topology is created with no neighbours"""
        # Arrange
        expected = {'1234abc': {'node_ip': '192.168.1.2', 'pods': {'dateformat': {
            'ip': '192.158.1.3', 'ns': 'dockerimage'}}, 'bgp_peers': {'leaf-204':{'prefix_count': 2}}, 'neighbours': {}, 'mac': 'MOCKMO1C'}}

        mock = ApicMethodsMock()
        mock.lldps = []
        mock.cdpns = [create_cdp_no_neighbour(True)]
        build = VkaciBuilTopology(
            VkaciEnvVariables(self.vars), mock)
        # Act
        result = build.update()
        # Assert
        self.assertDictEqual(result, expected)
        self.assertEqual(build.aci_vrf, "uni/tn-Ciscolive/ctx-vrf-01")


    def test_leaf_table(self):
        """Test that a leaf table is correctly created"""
        # Arrange
        expected = {
            'data': [{'data': [{'data': [{'data': [{'image': 'pod.svg',
                                         'ip': '192.158.1.3',
                                                    'ns': 'dockerimage',
                                                    'value': 'dateformat'}],
                               'image': 'node.svg',
                                          'ip': '192.168.1.2',
                                          'ns': '',
                                          'value': '1234abc'}],
                     'image': 'esxi.png',
                                'interface': ['vmxnic1-eth1/1'],
                                'ns': '',
                                'value': 'esxi4.cam.ciscolabs.com'},
                               {'data': [{'image': 'node.svg',
                                          'ip': '192.168.1.2',
                                          'ns': '',
                                          'value': '1234abc'}],
                                'image': 'bgp.png',
                                'value': 'BGP peering'}],
                      'image': 'switch.png',
                      'ip': '',
                      'value': 'leaf-204'}],
            'parent': 0}

        build = VkaciBuilTopology(
            VkaciEnvVariables(self.vars), ApicMethodsMock())
        table = VkaciTable(build)
        # Act
        build.update()
        result = table.get_leaf_table()

        # Assert
        self.assertDictEqual(result, expected)


    def test_bgp_table(self):
        """Test that a bgp table is correctly created"""
        # Arrange
        expected = {'parent': 0, 'data': [{'value': 'leaf-204', 'ip': '', 'image': 'switch.png', 'data': 
        [{'value': 'BGP Peering', 'image': 'bgp.png', 'data':
        [{'value': '1234abc', 'ip': '192.168.1.2', 'ns': '', 'image': 'node.svg'}]}, {'value': 'Prefixes', 'image': 'ip.png', 'data': 
        [{'value': '0.0.0.0/0', 'image': 'route.png', 'k8s_route': 'False', 'data': 
        [{'value': '&lt;No Hostname&gt;', 'ip': '10.4.68.5', 'image': 'Nok8slogo.png'}]}, {'value': '192.168.5.1/32', 'image': 'route.png', 'k8s_route': 'True', 'data': 
        [{'value': 'leaf 203', 'ip': '192.168.2.5', 'image': 'switch.png'}, {'value': '1234abc', 'ip': '192.168.1.2', 'image': 'node.svg'}]}]}]}]}

        build = VkaciBuilTopology(
            VkaciEnvVariables(self.vars), ApicMethodsMock())
        table = VkaciTable(build)
        # Act
        build.update()
        result = table.get_bgp_table()
        # Assert
        self.assertDictEqual(result, expected)


    def test_node_table(self):
        """Test that a node table is correctly created"""
        # Arrange
        expected = {'parent': 0, 'data': [{'value': 'leaf-204', 'ip': '', 'image': 'switch.png', 'data': 
        [{'value': 'esxi4.cam.ciscolabs.com', 'interface': ['vmxnic1-eth1/1'], 'ns': '', 'image': 'esxi.png', 'data': 
        [{'value': '1234abc', 'ip': '192.168.1.2', 'ns': '', 'image': 'node.svg'}]}]}]}

        build = VkaciBuilTopology(
            VkaciEnvVariables(self.vars), ApicMethodsMock())
        table = VkaciTable(build)
        # Act
        build.update()
        result = table.get_node_table()
        
        # Assert
        self.assertDictEqual(result, expected)


    def test_pod_table(self):
        """Test that a pod table is correctly created"""
        # Arrange
        expected = {'parent': 0, 'data': [{'value': 'leaf-204', 'ip': '', 'image': 'switch.png', 'data': 
        [{'value': 'dateformat', 'ip': '192.158.1.3', 'ns': 'dockerimage', 'image': 'pod.svg'}]}]}

        build = VkaciBuilTopology(
            VkaciEnvVariables(self.vars), ApicMethodsMock())
        table = VkaciTable(build)
        # Act
        build.update()
        result = table.get_pod_table()
        
        # Assert
        self.assertDictEqual(result, expected)
        

if __name__ == '__main__':
    unittest.main()
