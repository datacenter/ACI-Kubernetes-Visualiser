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
            name="dateformat", namespace="dockerimage", labels={"guest":"frontend"}
        ),
        spec=client.V1PodSpec(
            node_name="1234abc", containers=[]
        )
    ),
    client.V1Pod(
        status=client.V1PodStatus(
            host_ip="192.168.1.2", pod_ip="192.168.1.2"
        ),
        metadata=client.V1ObjectMeta(
            name="kube-router-xfgr", namespace="kube-system"
        ),
        spec=client.V1PodSpec(
            node_name="1234abc", containers=[client.V1Container(name="kube-router",
                args=[
                    "--run-router=true",
                    "--run-firewall=true",
                    "--run-service-proxy=true",
                    "--bgp-graceful-restart=true",
                    "--bgp-holdtime=3s",
                    "--kubeconfig=/var/lib/kube-router/kubeconfig",
                    "--cluster-asn=56002",
                    "--advertise-external-ip",
                    "--advertise-loadbalancer-ip",
                    "--advertise-pod-cidr=true",
                    "--enable-ibgp=false",
                    "--enable-overlay=false",
                    "--enable-pod-egress=false",
                    "--override-nexthop=true"
                ])]
            )
    )
]

# Fake k8s cluster data for nodes
nodes = [
    client.V1Node(
        metadata=client.V1ObjectMeta(
            name="1234abc", labels = {"app":"redis"}
        )    
    )
]

# Fake k8s cluster data for services
services = [
    client.V1Service(
        metadata=client.V1ObjectMeta(
            name="example service", namespace="appx", labels = {"app":"guestbook"}
        ),
        spec=client.V1ServiceSpec(
            cluster_ip="192.168.25.5", external_i_ps=["192.168.5.1"], 
        ),
        status=client.V1ServiceStatus(
        load_balancer=client.V1LoadBalancerStatus(
            ingress=[
                client.V1LoadBalancerIngress(ip='192.168.5.2')
                ]
        )
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


def create_lldp_neighbour(on: bool = True, desc: bool = True):
    n = Expando()
    n.operTxSt = n.operRxSt = "down"
    if (on):
        n.operTxSt = n.operRxSt = "up"
        n.lldpAdjEp = [Expando()]
        n.lldpAdjEp[0].sysName = "esxi4.cam.ciscolabs.com"
        n.lldpAdjEp[0].chassisIdV = "vmxnic1"
        if desc:
            n.lldpAdjEp[0].sysDesc = "VMware version 123"
        n.sysDesc = n.dn = "topology/pod-1/node-204"
        n.id = "eth1/1"
    return n


def create_cdp_neighbour(on: bool = False):
    n = Expando()
    n.operSt = "down"
    if (on):
        n.operSt = "up"
        n.cdpAdjEp = [Expando()]
        n.cdpAdjEp[0].sysName = "CiscoLabs5"
        n.cdpAdjEp[0].chassisIdV = n.cdpAdjEp[0].portIdV = "vmxnic2"
        n.cdpAdjEp[0].ver = "Cisco version 123"
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
@patch('kubernetes.client.CustomObjectsApi.list_namespaced_custom_object', MagicMock(return_value={"items":[]}))
@patch('kubernetes.client.CoreV1Api.list_service_for_all_namespaces', MagicMock(return_value=client.V1ServiceList(api_version="1", items=services)))
@patch('kubernetes.client.CoreV1Api.list_node', MagicMock(return_value=client.V1NodeList(api_version="1", items=nodes)))
@patch('app.graph.VkaciBuilTopology.get_calico_custom_object', MagicMock(return_value={'spec': {'asNumber': 56001}}))
class TestVkaciGraph(unittest.TestCase):
    maxDiff = None
    vars = {"APIC_IPS": "192.168.25.192,192.168.1.2",
            "TENANT": "Ciscolive",
            "VRF": "vrf-01",
            "MODE": "cluster",
            "KUBE_CONFIG": "$HOME/.kube/config",
            "CERT_USER": "useX509",
            "CERT_NAME": "test",
            "KEY_PATH": " 101/1/1-2",
            "ACI_META_FILE": None
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
        expected = {'nodes': {'1234abc': {'node_ip': '192.168.1.2',
                                          'pods': {'dateformat': {'ip': '192.158.1.3', 'primary_iface': '','ns': 'dockerimage', 'labels': {'guest': 'frontend'}, 'other_ifaces': {}, 'annotations': {}},
                                                   'kube-router-xfgr': {'ip': '192.168.1.2', 'primary_iface': '', 'ns': 'kube-system', 'labels': {}, 'other_ifaces': {}, 'annotations': {}}},
                                          'bgp_peers': {'leaf-204': {'prefix_count': 2}}, 'neighbours': {'esxi4.cam.ciscolabs.com':
                                                                                                         {'switches': {'leaf-204': {'vmxnic1-eth1/1'}}, 'Description': 'VMware version 123'}},
                                          'labels': {'app': 'redis'}, 'node_leaf_sec_iface_conn': [], 'node_pod_sec_iface_conn': [], 'node_leaf_ter_iface_conn': [], 'node_pod_ter_iface_conn': [], 'node_leaf_all_iface_conn': [], 'mac': 'MOCKMO1C'}},
                    'services': {'appx': [{'name': 'example service', 'cluster_ip': '192.168.25.5', 'external_i_ps': ['192.168.5.1'], 'load_balancer_ip': '192.168.5.2','ns':'appx',
                                           'labels': {'app': 'guestbook'}}]}}

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
        expected = {'nodes': {'1234abc': {'bgp_peers': {'leaf-204': {'prefix_count': 2}},
                                          'labels': {'app': 'redis'},
                                          'node_leaf_sec_iface_conn': [], 'node_pod_sec_iface_conn': [], 'node_leaf_ter_iface_conn': [], 'node_pod_ter_iface_conn': [], 'node_leaf_all_iface_conn': [],
                                          'mac': 'MOCKMO1C',
                                          'neighbours': {'CiscoLabs5': {'Description': 'Cisco '
                                                                        'version '
                                                                        '123',
                                                                        'switches': {'leaf-203': {'vmxnic2-eth1/1'}}}},
                                          'node_ip': '192.168.1.2',
                                          'pods': {'dateformat': {'ip': '192.158.1.3',
                                                                  'primary_iface': '',
                                                                  'labels': {'guest': 'frontend'},
                                                                  'other_ifaces': {}, 'annotations': {},
                                                                  'ns': 'dockerimage'},
                                                    'kube-router-xfgr': {'ip': '192.168.1.2',
                                                                  'primary_iface': '',
                                                                  'labels': {},
                                                                  'other_ifaces': {}, 'annotations': {},
                                                                  'ns': 'kube-system'}

                                                                  }}},
                    'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                           'external_i_ps': ['192.168.5.1'],
                                           'load_balancer_ip': '192.168.5.2',
                                           'labels': {'app': 'guestbook'},
                                           'name': 'example service',
                                           'ns':'appx'}]}}

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
        expected = {'nodes': {'1234abc': {'bgp_peers': {'leaf-204': {'prefix_count': 2}},
                                          'labels': {'app': 'redis'},
                                          'node_leaf_sec_iface_conn': [], 'node_pod_sec_iface_conn': [], 'node_leaf_ter_iface_conn': [], 'node_pod_ter_iface_conn': [], 'node_leaf_all_iface_conn': [],
                                          'mac': 'MOCKMO1C',
                                          'neighbours': {},
                                          'node_ip': '192.168.1.2',
                                          'pods': {'dateformat': {'ip': '192.158.1.3',
                                                                  'primary_iface': '',
                                                                  'labels': {'guest': 'frontend'},
                                                                  'other_ifaces': {}, 'annotations': {},
                                                                  'ns': 'dockerimage'},
                                                   'kube-router-xfgr': {'ip': '192.168.1.2',
                                                                  'primary_iface': '',
                                                                  'labels': {},
                                                                  'other_ifaces': {}, 'annotations': {},
                                                                  'ns': 'kube-system'}
                                                                  }}},
                    'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                           'external_i_ps': ['192.168.5.1'],
                                           'load_balancer_ip': '192.168.5.2',
                                           'labels': {'app': 'guestbook'},
                                           'name': 'example service',
                                           'ns':'appx'}]}}

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


    def test_valid_topology_no_desc_neighbour(self):
        """Test that a neighbour with no description will not crash"""
        # Arrange
        expected = {'nodes': {'1234abc': {'bgp_peers': {'leaf-204': {'prefix_count': 2}},
                                          'labels': {'app': 'redis'},
                                          'node_leaf_sec_iface_conn': [], 'node_pod_sec_iface_conn': [], 'node_leaf_ter_iface_conn': [], 'node_pod_ter_iface_conn': [], 'node_leaf_all_iface_conn': [],
                                          'mac': 'MOCKMO1C',
                                          'neighbours': {'esxi4.cam.ciscolabs.com': {'Description': '',
                                                                        'switches': {'leaf-204': set()}}},
                                          'node_ip': '192.168.1.2',
                                          'pods': {'dateformat': {'ip': '192.158.1.3',
                                                                  'primary_iface': '',
                                                                  'labels': {'guest': 'frontend'},
                                                                  'other_ifaces': {}, 'annotations': {},
                                                                  'ns': 'dockerimage'},
                                                    'kube-router-xfgr': {'ip': '192.168.1.2',
                                                                  'primary_iface': '',
                                                                  'labels': {},
                                                                  'other_ifaces': {}, 'annotations': {},
                                                                  'ns': 'kube-system'},
                                                                  }}},
                    'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                           'external_i_ps': ['192.168.5.1'],
                                           'load_balancer_ip': '192.168.5.2',
                                           'labels': {'app': 'guestbook'},
                                           'name': 'example service',
                                           'ns':'appx'}]}}

        mock = ApicMethodsMock()
        mock.lldps = [create_lldp_neighbour(desc=False)]
        mock.cdpns = []
        build = VkaciBuilTopology(
            VkaciEnvVariables(self.vars), mock)
        # Act
        result = build.update()
        print(result)
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
                                                    'value': 'dateformat'},
                                                    {'image': 'pod.svg',
                                         'ip': '192.168.1.2',
                                                    'ns': 'kube-system',
                                                    'value': 'kube-router-xfgr'}],
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
        expected = {'parent': 0, 'data': [{'value': 'leaf-204', 'ip': '', 'image': 'switch.png', 
        'data': [{'value': 'BGP Peering', 'image': 'bgp.png', 
        'data': [{'value': '1234abc', 'ip': '192.168.1.2', 'ns': '', 'image': 'node.svg'}]}, {'value': 'Prefixes', 'image': 'ip.png', 
        'data': [{'value': '0.0.0.0/0', 'image': 'route.png', 'k8s_route': 'False', 'ns': '', 'svc': '', 
        'data': [{'value': '&lt;No Hostname&gt;', 'ip': '10.4.68.5', 'image': 'Nok8slogo.png'}]}, {'value': '192.168.5.1/32', 'image': 'route.png', 'k8s_route': 'True', 'ns': 'appx', 'svc': 'example service', 
        'data': [{'value': 'leaf 203', 'ip': '192.168.2.5', 'image': 'switch.png'}, {'value': '1234abc', 'ip': '192.168.1.2', 'image': 'node.svg'}]}]}]}]}

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
        expected = {'parent': 0, 'data': [{'value': 'leaf-204', 'ip': '', 'image': 'switch.png', 
        'data': [{'value': 'esxi4.cam.ciscolabs.com', 'interface': ['vmxnic1-eth1/1'], 'ns': '', 'image': 'esxi.png', 
        'data': [{'value': '1234abc', 'ip': '192.168.1.2', 'ns': '', 'image': 'node.svg', 
        'data': [{'value': 'app', 'label_value': 'redis', 'image': 'label.svg'}]}]}]}]}

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
        expected = {'parent': 0, 'data': [{'value': 'leaf-204', 'ip': '', 'image': 'switch.png', 
        'data': [{'value': 'dateformat', 'ip': '192.158.1.3','ns': 'dockerimage', 'image': 'pod.svg', 
        'data': [{'value': 'guest', 'label_value': 'frontend', 'image': 'label.svg'}]},
                {'value': 'kube-router-xfgr', 'ip': '192.168.1.2','ns': 'kube-system', 'image': 'pod.svg', 
        'data': []}
        ]}]}

        build = VkaciBuilTopology(
            VkaciEnvVariables(self.vars), ApicMethodsMock())
        table = VkaciTable(build)
        # Act
        build.update()
        result = table.get_pod_table()
       
        # Assert
        self.assertDictEqual(result, expected)


    def test_services_table(self):
        """Test that a services table is correctly created"""
        # Arrange
        expected = {'parent': 0, 'data': [{'name': 'example service', 'cluster_ip': '192.168.25.5', 'external_i_ps': ['192.168.5.1'],'load_balancer_ip': '192.168.5.2', 
        'labels': {'app': 'guestbook'}, 'value': 'example service', 'ns': 'appx', 
        'image': 'svc.svg', 'data': [{'value': 'app', 'label_value': 'guestbook', 'image': 'label.svg'}]}]}

        build = VkaciBuilTopology(
            VkaciEnvVariables(self.vars), ApicMethodsMock())
        table = VkaciTable(build)
        # Act
        build.update()
        result = table.get_services_table()
        
        # Assert
        self.assertDictEqual(result, expected)


    def assert_cluster_as(self, expected):
        build = VkaciBuilTopology(
            VkaciEnvVariables(self.vars), ApicMethodsMock())
        build.update()
        asn = build.get_cluster_as()
        self.assertEqual(asn, expected)


    def test_calico_bgp_as_detection(self):
        """Test that the bgp AS is detected with calico"""
        """This is the default used on other tests but better be explicit so no one thinks it hasn't been tested"""
        self.assert_cluster_as('56001')


    @patch('kubernetes.client.CoreV1Api.read_namespaced_pod', MagicMock(return_value=pods[1]))
    def test_kube_router_bgp_as_detection(self):
        """Test that the bgp AS is detected with kube-router"""
        with patch('app.graph.VkaciBuilTopology.get_calico_custom_object', MagicMock(return_value={})):
            self.assert_cluster_as('56002')


    # AS numbers are intentionally repeated for testing.
    cilium_policies = {
        "items": [
            {"spec": {"virtualRouters": [
                {'localASN': 56003}, {'localASN': 56003}]}},
            {"spec": {"virtualRouters": [{'localASN': 56003}]}}
        ]
    }
    @patch('kubernetes.client.CoreV1Api.read_namespaced_pod', MagicMock(return_value=None))
    @patch('app.graph.VkaciBuilTopology.list_cilium_custom_objects', MagicMock(return_value=cilium_policies))
    def test_cilium_bgp_as_detection(self):
        """Test that the bgp AS is detected with cilium"""
        with patch('app.graph.VkaciBuilTopology.get_calico_custom_object', MagicMock(return_value={})):
            self.assert_cluster_as('56003')


    # Different AS numbers in Cilium is not supported.
    invalid_cilium_policies = {
        "items": [
            {"spec": {"virtualRouters": [
                {'localASN': 56003}, {'localASN': 56004}]}},
            {"spec": {"virtualRouters": [{'localASN': 56005}]}}
        ]
    }
    @patch('kubernetes.client.CoreV1Api.read_namespaced_pod', MagicMock(return_value=None))
    @patch('app.graph.VkaciBuilTopology.list_cilium_custom_objects', MagicMock(return_value=invalid_cilium_policies))
    def test_invalid_cilium_bgp_as_detection(self):
        """Test that the bgp AS is not detected with invalid cilium config"""
        with patch('app.graph.VkaciBuilTopology.get_calico_custom_object', MagicMock(return_value={})):
            self.assert_cluster_as(None)


    @patch('kubernetes.client.CoreV1Api.read_namespaced_pod', MagicMock(return_value=None))
    @patch('app.graph.VkaciBuilTopology.list_cilium_custom_objects', MagicMock(return_value=[]))
    def test_invalid_as_detection(self):
        """Test that the bgp AS is not detected with no valid config"""
        with patch('app.graph.VkaciBuilTopology.get_calico_custom_object', MagicMock(return_value={})):
            self.assert_cluster_as(None)


if __name__ == '__main__':
    unittest.main()
