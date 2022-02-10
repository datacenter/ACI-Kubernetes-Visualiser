from app.graph import apic_methods_resolve, vkaci_build_topology, vkaci_env_variables
import unittest
from pyaci import Node, core
from unittest.mock import patch, MagicMock
from kubernetes import client

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


def create_lldp_neighbour():
    n = Expando()
    n.operTxSt = n.operRxSt = "up"
    n.lldpAdjEp = [Expando()]
    n.lldpAdjEp[0].sysName = "esxi4.cam.ciscolabs.com"
    n.sysDesc = "topology/pod-1/node-204"
    n.id = "eth1/1"
    return n


def create_bgpPeer():
    b = Expando()
    b.operSt = "established"
    b.dn = "topology/pod-1/node-204"
    return b


class apic_methods_mock(apic_methods_resolve):
    def __init__(self) -> None:
        super().__init__()

    mo1 = MockMo("192.168.1.2", "MOCKMO1C", "pathA")
    eps = [mo1]

    lldps = [create_lldp_neighbour()]
    bgpPeers = [create_bgpPeer()]

    def get_fvcep(self, apic: Node, aci_vrf: str):
        return self.eps

    def get_fvcep_mac(self, apic: Node, mac: str):
        return self.eps[0]

    def get_lldpif(self, apic: Node, pathDn):
        return self.lldps

    def get_bgppeerentry(self, apic: Node, vrf: str, node_ip: str):
        return self.bgpPeers


class testvkacigraph(unittest.TestCase):

    def test_no_env_variables(self):
        """Test that no environment variables are handled"""
        # Arange
        build = vkaci_build_topology(
            vkaci_env_variables({}), apic_methods_mock())
        # Act
        result = build.update()
        # Assert
        self.assertIsNone(result)
        self.assertEqual(build.env.mode, 'None')
        self.assertIsNone(build.aci_vrf)
        self.assertEqual(len(build.env.apic_ip), 0)


    @patch('kubernetes.config.load_incluster_config', MagicMock(return_value=None))
    @patch('pyaci.Node.useX509CertAuth', MagicMock(return_value=None))
    @patch('kubernetes.client.CoreV1Api.list_pod_for_all_namespaces', MagicMock(return_value=client.V1PodList(api_version="1", items=pods)))
    def test_valid_topology(self):
        """Test that a valid topology is created"""
        # Arrange
        expected = {'1234abc': {'node_ip': '192.168.1.2', 'pods': {'dateformat': {
            'ip': '192.158.1.3', 'ns': 'dockerimage'}}, 'bgp_peers': {'node-204'}, 'lldp_neighbours': {'esxi4.cam.ciscolabs.com': {'node-204': {'eth1/1'}}}, 'mac': 'MOCKMO1C'}}

        vars = {"APIC_IPS": "192.168.25.192,192.168.1.2",
                "TENANT": "Ciscolive",
                "VRF": "vrf-01",
                "MODE": "cluster",
                "KUBE_CONFIG": "$HOME/.kube/config",
                "CERT_USER": "useX509",
                "CERT_NAME": "test",
                "KEY_PATH": " 101/1/1-2"
                }
        build = vkaci_build_topology(
            vkaci_env_variables(vars), apic_methods_mock())
        # Act
        result = build.update()
        # Assert
        self.assertDictEqual(result, expected)
        self.assertEqual(build.aci_vrf, "uni/tn-Ciscolive/ctx-vrf-01")


if __name__ == '__main__':
    unittest.main()
