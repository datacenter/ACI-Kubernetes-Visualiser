import unittest
import json
from pyaci import Node, core
from unittest.mock import patch, MagicMock
from kubernetes import client
from app.graph import ApicMethodsResolve, VkaciBuilTopology, VkaciEnvVariables, VkaciTable

core.aciClassMetas = {"topRoot": {
    "properties": {}, "rnFormat": "something"}}

nfna = {
    "items": [{
        "spec": {
            "aciTopology": {
                "ens1f2":
                    {
                        "fabricLink": [
                            "abc/def/node-101/[eth1/3]"
                        ],
                        "pods": [
                            {
                                "localIface": "ens1f2v12",
                                "podRef": {
                                    "name": "sriov-pod"
                                }
                            }
                        ]
                    }
            },
            "nodeName": "1234abc",
            "encapVlan": {
                    "encapRef": {
                        "key": "",
                        "nadVlanMap": ""
                    },
                    "mode": "Trunk",
                    "vlanList": "[3456]"
            },
            "networkRef": {
                "name": "sriov-net1"
            },
            "primaryCni": "sriov"
        },
        "metadata": {
            "name": "sriov"
        }
    },
        {
        "spec": {
            "aciTopology": {
                "bond1":
                    {
                        "fabricLink": [
                            "abc/def/node-101/[eth1/37]"
                        ],
                        "pods": [
                            {
                                "localIface": "net1",
                                "podRef": {
                                    "name": "macvlan-pod"
                                }
                            }
                        ]
                    }
            },
            "nodeName": "1234abc",
            "encapVlan": {
                    "encapRef": {
                        "key": "",
                        "nadVlanMap": ""
                    },
                    "mode": "Trunk",
                    "vlanList": "[3456]"
            },
            "networkRef": {
                "name": "macvlan-net1"
            },
            "primaryCni": "macvlan"
        },
        "metadata": {
            "name": "macvlan"
        }
    }, {
        "spec": {
            "aciTopology": {
                "br1":
                    {
                        "fabricLink": [
                            "abc/def/node-101/[eth1/38]"
                        ],
                        "pods": [
                            {
                                "localIface": "br-net1",
                                "podRef": {
                                    "name": "bridge-pod"
                                }
                            }
                        ]
                    }
            },
            "nodeName": "1234abc",
            "encapVlan": {
                    "encapRef": {
                        "key": "",
                        "nadVlanMap": ""
                    },
                    "mode": "Trunk",
                    "vlanList": "[3456]"
            },
            "networkRef": {
                "name": "bridge-net1"
            },
            "primaryCni": "bridge"
        },
        "metadata": {
            "name": "bridge"
        }
    }]
}
# Fake k8s cluster data
pods = [
    client.V1Pod(
        status=client.V1PodStatus(
            host_ip="192.168.1.2", pod_ip="192.158.1.3"
        ),
        metadata=client.V1ObjectMeta(
            name="dateformat", namespace="dockerimage", labels={"guest": "frontend"}
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
    ),
    client.V1Pod(
        status=client.V1PodStatus(
            host_ip="192.168.1.2", pod_ip="192.158.1.4"
        ),
        metadata=client.V1ObjectMeta(
            name="sriov-pod", namespace="dockerimage", labels={"guest": "frontend"}, annotations={"k8s.v1.cni.cncf.io/network-status": json.dumps([{"ips": ["192.158.1.5"], "mac": "02:a0:e8:00:00:0a", "name": "sriov-net1", "interface": "ens1f2v12"}])}
        ),
        spec=client.V1PodSpec(
            node_name="1234abc", containers=[]
        )
    ),
    client.V1Pod(
        status=client.V1PodStatus(
            host_ip="192.168.1.2", pod_ip="192.158.1.6"
        ),
        metadata=client.V1ObjectMeta(
            name="macvlan-pod", namespace="dockerimage", labels={"guest": "frontend"}, annotations={"k8s.v1.cni.cncf.io/network-status": json.dumps([{"ips": ["192.158.1.7"], "mac": "02:a0:e8:00:00:0a", "name": "macvlan-net1", "interface": "net1"}])}
        ),
        spec=client.V1PodSpec(
            node_name="1234abc", containers=[]
        )
    ),
    client.V1Pod(
        status=client.V1PodStatus(
            host_ip="192.168.1.2", pod_ip="192.158.1.7"
        ),
        metadata=client.V1ObjectMeta(
            name="bridge-pod", namespace="dockerimage", labels={"guest": "frontend"}, annotations={"k8s.v1.cni.cncf.io/network-status": json.dumps([{"ips": ["192.158.1.8"], "mac": "02:a0:e8:00:00:0a", "name": "br-net1", "interface": "br-net1"}])}
        ),
        spec=client.V1PodSpec(
            node_name="1234abc", containers=[]
        )
    )
]

# Fake k8s cluster data for nodes
nodes = [
    client.V1Node(
        metadata=client.V1ObjectMeta(
            name="1234abc", labels={"app": "redis"}
        )
    )
]

# Fake k8s cluster data for services
services = [
    client.V1Service(
        metadata=client.V1ObjectMeta(
            name="example service", namespace="appx", labels={"app": "guestbook"}
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

# Fake VMI cluster data for vmis
vmis = {
    "apiVersion": "v1",
    "items": [
        {
            "apiVersion": "kubevirt.io/v1",
            "kind": "VirtualMachineInstance",
            "metadata": {
                "annotations": {
                    "kubevirt.io/cluster-instancetype-name": "o1.xlarge",
                    "kubevirt.io/cluster-preference-name": "rhel.9",
                    "kubevirt.io/latest-observed-api-version": "v1",
                    "kubevirt.io/storage-observed-api-version": "v1",
                    "kubevirt.io/vm-generation": "10",
                    "vm.kubevirt.io/os": "linux"
                },
                "creationTimestamp": "2025-04-15T04:48:49Z",
                "finalizers": [
                    "kubevirt.io/virtualMachineControllerFinalize",
                    "foregroundDeleteVirtualMachine"
                ],
                "generation": 53,
                "labels": {
                    "kubevirt.io/nodeName": "1234abc",
                    "network.kubevirt.io/headlessService": "headless"
                },
                "name": "cp-1",
                "namespace": "ocp-cilium-c1",
                "ownerReferences": [
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "blockOwnerDeletion": "true",
                        "controller": "true",
                        "kind": "VirtualMachine",
                        "name": "cp-1",
                        "uid": "91f7cf7b-c58c-42f8-9ca3-c955da7afda8"
                    }
                ],
                "resourceVersion": "1422388059",
                "uid": "a86e43a8-1504-4a7e-833c-6a50db0c5562"
            },
            "spec": {
                "architecture": "amd64",
                "domain": {
                    "cpu": {
                        "cores": 1,
                        "maxSockets": 16,
                        "model": "Cascadelake-Server-noTSX",
                        "sockets": 4,
                        "threads": 1
                    },
                    "devices": {
                        "autoattachPodInterface": "false",
                        "disks": [
                            {
                                "bootOrder": 2,
                                "cdrom": {
                                    "bus": "scsi",
                                    "readonly": "true",
                                    "tray": "closed"
                                },
                                "name": "cdrom",
                                "shareable": "true"
                            },
                            {
                                "bootOrder": 1,
                                "dedicatedIOThread": "true",
                                "disk": {
                                    "bus": "virtio"
                                },
                                "name": "disk-fuchsia-lobster-69"
                            },
                            {
                                "dedicatedIOThread": "true",
                                "disk": {
                                    "bus": "virtio"
                                },
                                "name": "cloudinitdisk"
                            }
                        ],
                        "interfaces": [
                            {
                                "bridge": {},
                                "macAddress": "02:a0:e8:00:00:0a",
                                "model": "virtio",
                                "name": "nic-gray-guineafowl-45"
                            }
                        ],
                        "rng": {}
                    },
                    "features": {
                        "acpi": {
                            "enabled": "true"
                        },
                        "smm": {
                            "enabled": "true"
                        }
                    },
                    "firmware": {
                        "bootloader": {
                            "efi": {
                                "secureBoot": "true"
                            }
                        },
                        "uuid": "97a11ff5-4318-5f0a-a6b9-d3078356700b"
                    },
                    "machine": {
                        "type": "pc-q35-rhel9.4.0"
                    },
                    "memory": {
                        "guest": "16Gi",
                        "maxGuest": "64Gi"
                    },
                    "resources": {
                        "requests": {
                            "memory": "8Gi"
                        }
                    }
                },
                "evictionStrategy": "LiveMigrate",
                "networks": [
                    {
                        "multus": {
                            "networkName": "node"
                        },
                        "name": "nic-gray-guineafowl-45"
                    }
                ],
                "subdomain": "headless",
                "volumes": [
                    {
                        "cloudInitNoCloud": {
                            "userData": "#cloud-config\nchpasswd:\n  expire: false\npassword: 7u1u-4ppf-hkob\nuser: rhel\n"
                        },
                        "name": "cloudinitdisk"
                    },
                    {
                        "name": "cdrom",
                        "persistentVolumeClaim": {
                            "claimName": "ocp-cilium-c1-agent"
                        }
                    },
                    {
                        "dataVolume": {
                            "name": "dv-cp-1-orange-kiwi-46"
                        },
                        "name": "disk-fuchsia-lobster-69"
                    }
                ]
            },
            "status": {
                "activePods": {
                    "c3703363-6062-4d23-9926-e63927357116": "1234abc"
                },
                "conditions": [
                    {
                        "lastProbeTime": "null",
                        "lastTransitionTime": "2025-04-15T04:48:55Z",
                        "status": "True",
                        "type": "Ready"
                    },
                    {
                        "lastProbeTime": "null",
                        "lastTransitionTime": "null",
                        "message": "All of the VMI's DVs are bound and not running",
                        "reason": "AllDVsReady",
                        "status": "True",
                        "type": "DataVolumesReady"
                    },
                    {
                        "lastProbeTime": "null",
                        "lastTransitionTime": "null",
                        "message": "cannot migrate VMI: PVC dv-cp-1-orange-kiwi-46 is not shared, live migration requires that all PVCs must be shared (using ReadWriteMany access mode)",
                        "reason": "DisksNotLiveMigratable",
                        "status": "False",
                        "type": "LiveMigratable"
                    },
                    {
                        "lastProbeTime": "null",
                        "lastTransitionTime": "null",
                        "status": "True",
                        "type": "StorageLiveMigratable"
                    },
                    {
                        "lastProbeTime": "2025-04-15T04:49:39Z",
                        "lastTransitionTime": "null",
                        "status": "True",
                        "type": "AgentConnected"
                    }
                ],
                "currentCPUTopology": {
                    "cores": 1,
                    "sockets": 4,
                    "threads": 1
                },
                "guestOSInfo": {
                    "id": "rhcos",
                    "kernelRelease": "5.14.0-427.61.1.el9_4.x86_64",
                    "kernelVersion": "#1 SMP PREEMPT_DYNAMIC Fri Mar 14 15:21:35 EDT 2025",
                    "machine": "x86_64",
                    "name": "Red Hat Enterprise Linux CoreOS",
                    "prettyName": "Red Hat Enterprise Linux CoreOS 417.94.202503172033-0",
                    "version": "417.94.202503172033-0",
                    "versionId": "4.17"
                },
                "interfaces": [
                    {
                        "infoSource": "domain, guest-agent, multus-status",
                        "interfaceName": "enp1s0",
                        "ipAddress": "192.168.2.35",
                        "ipAddresses": [
                            "192.168.2.35"
                        ],
                        "mac": "02:a0:e8:00:00:0a",
                        "name": "nic-gray-guineafowl-45",
                        "queueCount": 1
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "cilium_net",
                        "ipAddress": "fe80::1c54:48ff:fe8f:4f3",
                        "ipAddresses": [
                            "fe80::1c54:48ff:fe8f:4f3"
                        ],
                        "mac": "1e:54:48:8f:04:f3"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "cilium_host",
                        "ipAddress": "10.56.2.15",
                        "ipAddresses": [
                            "10.56.2.15",
                            "fe80::6813:20ff:fe60:62d0"
                        ],
                        "mac": "6a:13:20:60:62:d0"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "cilium_vxlan",
                        "ipAddress": "fe80::3cae:64ff:fe77:ae49",
                        "ipAddresses": [
                            "fe80::3cae:64ff:fe77:ae49"
                        ],
                        "mac": "3e:ae:64:77:ae:49"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc_health",
                        "ipAddress": "fe80::c33:82ff:fe9e:ab8d",
                        "ipAddresses": [
                            "fe80::c33:82ff:fe9e:ab8d"
                        ],
                        "mac": "0e:33:82:9e:ab:8d"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc5ddbe81e1850",
                        "ipAddress": "fe80::3c7f:26ff:fe28:e04f",
                        "ipAddresses": [
                            "fe80::3c7f:26ff:fe28:e04f"
                        ],
                        "mac": "3e:7f:26:28:e0:4f"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc5ffab20e7ca3",
                        "ipAddress": "fe80::fc67:7ff:fe87:a3e9",
                        "ipAddresses": [
                            "fe80::fc67:7ff:fe87:a3e9"
                        ],
                        "mac": "fe:67:07:87:a3:e9"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc8c131b5a3601",
                        "ipAddress": "fe80::9c4f:3aff:fe70:bb8b",
                        "ipAddresses": [
                            "fe80::9c4f:3aff:fe70:bb8b"
                        ],
                        "mac": "9e:4f:3a:70:bb:8b"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc7e004d719d6d",
                        "ipAddress": "fe80::b8f9:48ff:fe08:b070",
                        "ipAddresses": [
                            "fe80::b8f9:48ff:fe08:b070"
                        ],
                        "mac": "ba:f9:48:08:b0:70"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc4c2a740873ed",
                        "ipAddress": "fe80::e41a:27ff:fe60:3300",
                        "ipAddresses": [
                            "fe80::e41a:27ff:fe60:3300"
                        ],
                        "mac": "e6:1a:27:60:33:00"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc9de097b07fdb",
                        "ipAddress": "fe80::8004:d0ff:fe7b:970e",
                        "ipAddresses": [
                            "fe80::8004:d0ff:fe7b:970e"
                        ],
                        "mac": "82:04:d0:7b:97:0e"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcfd72d490aae2",
                        "ipAddress": "fe80::101f:7eff:feea:1881",
                        "ipAddresses": [
                            "fe80::101f:7eff:feea:1881"
                        ],
                        "mac": "12:1f:7e:ea:18:81"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcff10fd01910a",
                        "ipAddress": "fe80::1cd7:62ff:fe0b:2e14",
                        "ipAddresses": [
                            "fe80::1cd7:62ff:fe0b:2e14"
                        ],
                        "mac": "1e:d7:62:0b:2e:14"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcf67850a1700c",
                        "ipAddress": "fe80::54d6:c4ff:fe95:5c5e",
                        "ipAddresses": [
                            "fe80::54d6:c4ff:fe95:5c5e"
                        ],
                        "mac": "56:d6:c4:95:5c:5e"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc40ac0b8cd9cc",
                        "ipAddress": "fe80::1400:86ff:fe6a:2db4",
                        "ipAddresses": [
                            "fe80::1400:86ff:fe6a:2db4"
                        ],
                        "mac": "16:00:86:6a:2d:b4"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcdc82aa2b9d0e",
                        "ipAddress": "fe80::9cf2:e6ff:fe44:b97a",
                        "ipAddresses": [
                            "fe80::9cf2:e6ff:fe44:b97a"
                        ],
                        "mac": "9e:f2:e6:44:b9:7a"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcb03107ef1d4e",
                        "ipAddress": "fe80::ac39:f0ff:fe7d:2c85",
                        "ipAddresses": [
                            "fe80::ac39:f0ff:fe7d:2c85"
                        ],
                        "mac": "ae:39:f0:7d:2c:85"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcd868aadd5730",
                        "ipAddress": "fe80::f44c:90ff:feec:de81",
                        "ipAddresses": [
                            "fe80::f44c:90ff:feec:de81"
                        ],
                        "mac": "f6:4c:90:ec:de:81"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc223308086a88",
                        "ipAddress": "fe80::e4a6:8bff:feb4:5bfe",
                        "ipAddresses": [
                            "fe80::e4a6:8bff:feb4:5bfe"
                        ],
                        "mac": "e6:a6:8b:b4:5b:fe"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc0c7ec4a2d9cd",
                        "ipAddress": "fe80::705f:d4ff:fe47:1609",
                        "ipAddresses": [
                            "fe80::705f:d4ff:fe47:1609"
                        ],
                        "mac": "72:5f:d4:47:16:09"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc2b3678f1fcbb",
                        "ipAddress": "fe80::84d8:90ff:fed6:964",
                        "ipAddresses": [
                            "fe80::84d8:90ff:fed6:964"
                        ],
                        "mac": "86:d8:90:d6:09:64"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcb077c0642d3c",
                        "ipAddress": "fe80::48d1:e1ff:fe28:e70d",
                        "ipAddresses": [
                            "fe80::48d1:e1ff:fe28:e70d"
                        ],
                        "mac": "4a:d1:e1:28:e7:0d"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc7bfe9bb3221e",
                        "ipAddress": "fe80::4481:aaff:fe98:b21c",
                        "ipAddresses": [
                            "fe80::4481:aaff:fe98:b21c"
                        ],
                        "mac": "46:81:aa:98:b2:1c"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc9ed5704e5738",
                        "ipAddress": "fe80::c036:2bff:fed6:25e4",
                        "ipAddresses": [
                            "fe80::c036:2bff:fed6:25e4"
                        ],
                        "mac": "c2:36:2b:d6:25:e4"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcac4d6702a2e0",
                        "ipAddress": "fe80::1c27:cdff:fef4:1fdf",
                        "ipAddresses": [
                            "fe80::1c27:cdff:fef4:1fdf"
                        ],
                        "mac": "1e:27:cd:f4:1f:df"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc25e04bdd6fb1",
                        "ipAddress": "fe80::1c89:1fff:fe7c:2d1e",
                        "ipAddresses": [
                            "fe80::1c89:1fff:fe7c:2d1e"
                        ],
                        "mac": "1e:89:1f:7c:2d:1e"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc7072b3ec8414",
                        "ipAddress": "fe80::64d1:31ff:fe9c:8837",
                        "ipAddresses": [
                            "fe80::64d1:31ff:fe9c:8837"
                        ],
                        "mac": "66:d1:31:9c:88:37"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc7584c264d4a9",
                        "ipAddress": "fe80::ccad:6eff:fea3:e96b",
                        "ipAddresses": [
                            "fe80::ccad:6eff:fea3:e96b"
                        ],
                        "mac": "ce:ad:6e:a3:e9:6b"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcc9b5566456c9",
                        "ipAddress": "fe80::4492:1fff:fe3a:275c",
                        "ipAddresses": [
                            "fe80::4492:1fff:fe3a:275c"
                        ],
                        "mac": "46:92:1f:3a:27:5c"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc37e80c382e8a",
                        "ipAddress": "fe80::6cbc:a6ff:fe14:ba64",
                        "ipAddresses": [
                            "fe80::6cbc:a6ff:fe14:ba64"
                        ],
                        "mac": "6e:bc:a6:14:ba:64"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcfca6cefcbcda",
                        "ipAddress": "fe80::ac11:9ff:fe7b:3f3e",
                        "ipAddresses": [
                            "fe80::ac11:9ff:fe7b:3f3e"
                        ],
                        "mac": "ae:11:09:7b:3f:3e"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcfcf3e2251f9e",
                        "ipAddress": "fe80::685d:3dff:fe22:357a",
                        "ipAddresses": [
                            "fe80::685d:3dff:fe22:357a"
                        ],
                        "mac": "6a:5d:3d:22:35:7a"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc5bdc57cdfe91",
                        "ipAddress": "fe80::c9:29ff:febe:7ca1",
                        "ipAddresses": [
                            "fe80::c9:29ff:febe:7ca1"
                        ],
                        "mac": "02:c9:29:be:7c:a1"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc5b2349af4ef5",
                        "ipAddress": "fe80::684b:9fff:fedb:ee9e",
                        "ipAddresses": [
                            "fe80::684b:9fff:fedb:ee9e"
                        ],
                        "mac": "6a:4b:9f:db:ee:9e"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc5c8cc9c83b18",
                        "ipAddress": "fe80::3c21:bff:fe43:96ce",
                        "ipAddresses": [
                            "fe80::3c21:bff:fe43:96ce"
                        ],
                        "mac": "3e:21:0b:43:96:ce"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc4b45befa18b2",
                        "ipAddress": "fe80::9482:e9ff:febb:2d76",
                        "ipAddresses": [
                            "fe80::9482:e9ff:febb:2d76"
                        ],
                        "mac": "96:82:e9:bb:2d:76"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc36cf989e79c8",
                        "ipAddress": "fe80::9874:4ff:fe50:fc3d",
                        "ipAddresses": [
                            "fe80::9874:4ff:fe50:fc3d"
                        ],
                        "mac": "9a:74:04:50:fc:3d"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcefd1f8aa3abf",
                        "ipAddress": "fe80::7cb3:a1ff:fe57:b0f8",
                        "ipAddresses": [
                            "fe80::7cb3:a1ff:fe57:b0f8"
                        ],
                        "mac": "7e:b3:a1:57:b0:f8"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcda142dfb0af9",
                        "ipAddress": "fe80::dccc:92ff:fe61:fac8",
                        "ipAddresses": [
                            "fe80::dccc:92ff:fe61:fac8"
                        ],
                        "mac": "de:cc:92:61:fa:c8"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxca2b05696faa8",
                        "ipAddress": "fe80::18a1:fcff:fe07:30e",
                        "ipAddresses": [
                            "fe80::18a1:fcff:fe07:30e"
                        ],
                        "mac": "1a:a1:fc:07:03:0e"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc4bcd8693a3c3",
                        "ipAddress": "fe80::5c29:29ff:fe66:5b7e",
                        "ipAddresses": [
                            "fe80::5c29:29ff:fe66:5b7e"
                        ],
                        "mac": "5e:29:29:66:5b:7e"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxceba2fb3e49b7",
                        "ipAddress": "fe80::3810:ffff:fe78:652e",
                        "ipAddresses": [
                            "fe80::3810:ffff:fe78:652e"
                        ],
                        "mac": "3a:10:ff:78:65:2e"
                    }
                ],
                "launcherContainerImageVersion": "registry.redhat.io/container-native-virtualization/virt-launcher-rhel9@sha256:480f4dbd779497881b837aebe501c44078f74e1c6cef4dceb1ca617dbe38ea31",
                "machine": {
                    "type": "pc-q35-rhel9.4.0"
                },
                "memory": {
                    "guestAtBoot": "16Gi",
                    "guestCurrent": "16Gi",
                    "guestRequested": "16Gi"
                },
                "migrationMethod": "BlockMigration",
                "migrationTransport": "Unix",
                "nodeName": "1234abc",
                "phase": "Running",
                "phaseTransitionTimestamps": [
                    {
                        "phase": "Pending",
                        "phaseTransitionTimestamp": "2025-04-15T04:48:49Z"
                    },
                    {
                        "phase": "Scheduling",
                        "phaseTransitionTimestamp": "2025-04-15T04:48:49Z"
                    },
                    {
                        "phase": "Scheduled",
                        "phaseTransitionTimestamp": "2025-04-15T04:48:55Z"
                    },
                    {
                        "phase": "Running",
                        "phaseTransitionTimestamp": "2025-04-15T04:48:57Z"
                    }
                ],
                "qosClass": "Burstable",
                "runtimeUser": 107,
                "selinuxContext": "system_u:object_r:container_file_t:s0:c195,c353",
                "virtualMachineRevisionName": "revision-start-vm-91f7cf7b-c58c-42f8-9ca3-c955da7afda8-10",
                "volumeStatus": [
                    {
                        "name": "cdrom",
                        "persistentVolumeClaimInfo": {
                            "accessModes": [
                                "ReadWriteMany"
                            ],
                            "capacity": {
                                "storage": "2Gi"
                            },
                            "claimName": "ocp-cilium-c1-agent",
                            "filesystemOverhead": "0",
                            "requests": {
                                "storage": "2G"
                            },
                            "volumeMode": "Block"
                        },
                        "target": "sda"
                    },
                    {
                        "name": "cloudinitdisk",
                        "size": 1048576,
                        "target": "vdb"
                    },
                    {
                        "name": "disk-fuchsia-lobster-69",
                        "persistentVolumeClaimInfo": {
                            "accessModes": [
                                "ReadWriteOnce"
                            ],
                            "capacity": {
                                "storage": "110960424Ki"
                            },
                            "claimName": "dv-cp-1-orange-kiwi-46",
                            "filesystemOverhead": "0.055",
                            "requests": {
                                "storage": "113623473440"
                            },
                            "volumeMode": "Filesystem"
                        },
                        "target": "vda"
                    }
                ]
            }
        },
        {
            "apiVersion": "kubevirt.io/v1",
            "kind": "VirtualMachineInstance",
            "metadata": {
                "annotations": {
                    "kubevirt.io/cluster-instancetype-name": "o1.xlarge",
                    "kubevirt.io/cluster-preference-name": "rhel.9",
                    "kubevirt.io/latest-observed-api-version": "v1",
                    "kubevirt.io/storage-observed-api-version": "v1",
                    "kubevirt.io/vm-generation": "12",
                    "vm.kubevirt.io/os": "linux"
                },
                "creationTimestamp": "2025-04-15T04:48:51Z",
                "finalizers": [
                    "kubevirt.io/virtualMachineControllerFinalize",
                    "foregroundDeleteVirtualMachine"
                ],
                "generation": 15,
                "labels": {
                    "kubevirt.io/nodeName": "1234abc",
                    "network.kubevirt.io/headlessService": "headless"
                },
                "name": "cp-2",
                "namespace": "ocp-cilium-c1",
                "ownerReferences": [
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "blockOwnerDeletion": "true",
                        "controller": "true",
                        "kind": "VirtualMachine",
                        "name": "cp-2",
                        "uid": "2861c69e-b6bf-4c18-9cfe-19fed4fec0a0"
                    }
                ],
                "resourceVersion": "1422391806",
                "uid": "00b74ab2-dda8-4ddf-b5c2-75981f6a276c"
            },
            "spec": {
                "architecture": "amd64",
                "domain": {
                    "cpu": {
                        "cores": 1,
                        "maxSockets": 16,
                        "model": "Cascadelake-Server-noTSX",
                        "sockets": 4,
                        "threads": 1
                    },
                    "devices": {
                        "autoattachPodInterface": "false",
                        "disks": [
                            {
                                "bootOrder": 2,
                                "cdrom": {
                                    "bus": "scsi",
                                    "readonly": "true",
                                    "tray": "closed"
                                },
                                "name": "cdrom",
                                "shareable": "true"
                            },
                            {
                                "bootOrder": 1,
                                "dedicatedIOThread": "true",
                                "disk": {
                                    "bus": "virtio"
                                },
                                "name": "disk-gold-spider-93"
                            },
                            {
                                "dedicatedIOThread": "true",
                                "disk": {
                                    "bus": "virtio"
                                },
                                "name": "cloudinitdisk"
                            }
                        ],
                        "interfaces": [
                            {
                                "bridge": {},
                                "macAddress": "02:a0:e8:00:00:0c",
                                "model": "virtio",
                                "name": "node"
                            }
                        ],
                        "rng": {}
                    },
                    "features": {
                        "acpi": {
                            "enabled": "true"
                        },
                        "smm": {
                            "enabled": "true"
                        }
                    },
                    "firmware": {
                        "bootloader": {
                            "efi": {
                                "secureBoot": "true"
                            }
                        },
                        "uuid": "97d51f22-101c-5360-9f94-02015dc344a0"
                    },
                    "machine": {
                        "type": "pc-q35-rhel9.4.0"
                    },
                    "memory": {
                        "guest": "16Gi",
                        "maxGuest": "64Gi"
                    },
                    "resources": {
                        "requests": {
                            "memory": "8Gi"
                        }
                    }
                },
                "evictionStrategy": "LiveMigrate",
                "networks": [
                    {
                        "multus": {
                            "networkName": "node"
                        },
                        "name": "node"
                    }
                ],
                "subdomain": "headless",
                "volumes": [
                    {
                        "cloudInitNoCloud": {
                            "userData": "#cloud-config\nchpasswd:\n  expire: false\npassword: 7u1u-4ppf-hkob\nuser: rhel\n"
                        },
                        "name": "cloudinitdisk"
                    },
                    {
                        "name": "cdrom",
                        "persistentVolumeClaim": {
                            "claimName": "ocp-cilium-c1-agent"
                        }
                    },
                    {
                        "dataVolume": {
                            "name": "dv-cp-2-green-whale-28"
                        },
                        "name": "disk-gold-spider-93"
                    }
                ]
            },
            "status": {
                "activePods": {
                    "6579970c-76ab-4436-8f0f-b142ec6b73a0": "1234abc"
                },
                "conditions": [
                    {
                        "lastProbeTime": "null",
                        "lastTransitionTime": "2025-04-15T04:48:55Z",
                        "status": "True",
                        "type": "Ready"
                    },
                    {
                        "lastProbeTime": "null",
                        "lastTransitionTime": "null",
                        "message": "All of the VMI's DVs are bound and not running",
                        "reason": "AllDVsReady",
                        "status": "True",
                        "type": "DataVolumesReady"
                    },
                    {
                        "lastProbeTime": "null",
                        "lastTransitionTime": "null",
                        "message": "cannot migrate VMI: PVC dv-cp-2-green-whale-28 is not shared, live migration requires that all PVCs must be shared (using ReadWriteMany access mode)",
                        "reason": "DisksNotLiveMigratable",
                        "status": "False",
                        "type": "LiveMigratable"
                    },
                    {
                        "lastProbeTime": "null",
                        "lastTransitionTime": "null",
                        "status": "True",
                        "type": "StorageLiveMigratable"
                    },
                    {
                        "lastProbeTime": "2025-04-15T04:49:39Z",
                        "lastTransitionTime": "null",
                        "status": "True",
                        "type": "AgentConnected"
                    }
                ],
                "currentCPUTopology": {
                    "cores": 1,
                    "sockets": 4,
                    "threads": 1
                },
                "guestOSInfo": {
                    "id": "rhcos",
                    "kernelRelease": "5.14.0-427.61.1.el9_4.x86_64",
                    "kernelVersion": "#1 SMP PREEMPT_DYNAMIC Fri Mar 14 15:21:35 EDT 2025",
                    "machine": "x86_64",
                    "name": "Red Hat Enterprise Linux CoreOS",
                    "prettyName": "Red Hat Enterprise Linux CoreOS 417.94.202503172033-0",
                    "version": "417.94.202503172033-0",
                    "versionId": "4.17"
                },
                "interfaces": [
                    {
                        "infoSource": "domain, guest-agent, multus-status",
                        "interfaceName": "enp1s0",
                        "ipAddress": "192.168.2.36",
                        "ipAddresses": [
                            "192.168.2.36"
                        ],
                        "mac": "02:a0:e8:00:00:0c",
                        "name": "node",
                        "queueCount": 1
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxce3050c4b696e",
                        "ipAddress": "fe80::4c74:beff:fee4:7a1d",
                        "ipAddresses": [
                            "fe80::4c74:beff:fee4:7a1d"
                        ],
                        "mac": "4e:74:be:e4:7a:1d"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc834d19edd952",
                        "ipAddress": "fe80::e0a8:9ff:fe5e:b5b",
                        "ipAddresses": [
                            "fe80::e0a8:9ff:fe5e:b5b"
                        ],
                        "mac": "e2:a8:09:5e:0b:5b"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "cilium_net",
                        "ipAddress": "fe80::cc63:a2ff:fe27:b1e7",
                        "ipAddresses": [
                            "fe80::cc63:a2ff:fe27:b1e7"
                        ],
                        "mac": "ce:63:a2:27:b1:e7"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "cilium_host",
                        "ipAddress": "10.56.1.213",
                        "ipAddresses": [
                            "10.56.1.213",
                            "fe80::6c17:e6ff:fed5:ba2b"
                        ],
                        "mac": "6e:17:e6:d5:ba:2b"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc3bd854ca0eb2",
                        "ipAddress": "fe80::70e5:e2ff:fe57:aff2",
                        "ipAddresses": [
                            "fe80::70e5:e2ff:fe57:aff2"
                        ],
                        "mac": "72:e5:e2:57:af:f2"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "cilium_vxlan",
                        "ipAddress": "fe80::848a:64ff:fe2a:22fd",
                        "ipAddresses": [
                            "fe80::848a:64ff:fe2a:22fd"
                        ],
                        "mac": "86:8a:64:2a:22:fd"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxce61ad9b1033e",
                        "ipAddress": "fe80::f8a4:f9ff:febd:907c",
                        "ipAddresses": [
                            "fe80::f8a4:f9ff:febd:907c"
                        ],
                        "mac": "fa:a4:f9:bd:90:7c"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc_health",
                        "ipAddress": "fe80::4c09:edff:fe6d:2cb3",
                        "ipAddresses": [
                            "fe80::4c09:edff:fe6d:2cb3"
                        ],
                        "mac": "4e:09:ed:6d:2c:b3"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc58377f23f52e",
                        "ipAddress": "fe80::cda:a5ff:feae:a60c",
                        "ipAddresses": [
                            "fe80::cda:a5ff:feae:a60c"
                        ],
                        "mac": "0e:da:a5:ae:a6:0c"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc400e7c4872ce",
                        "ipAddress": "fe80::7486:61ff:fe05:9a7e",
                        "ipAddresses": [
                            "fe80::7486:61ff:fe05:9a7e"
                        ],
                        "mac": "76:86:61:05:9a:7e"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc5ce4295ded2d",
                        "ipAddress": "fe80::14b0:f3ff:fe70:e1df",
                        "ipAddresses": [
                            "fe80::14b0:f3ff:fe70:e1df"
                        ],
                        "mac": "16:b0:f3:70:e1:df"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc9a1e33b7f0b0",
                        "ipAddress": "fe80::dccd:e3ff:fe2d:5e1",
                        "ipAddresses": [
                            "fe80::dccd:e3ff:fe2d:5e1"
                        ],
                        "mac": "de:cd:e3:2d:05:e1"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcd50bc361e6ca",
                        "ipAddress": "fe80::68f5:4fff:febd:9a3d",
                        "ipAddresses": [
                            "fe80::68f5:4fff:febd:9a3d"
                        ],
                        "mac": "6a:f5:4f:bd:9a:3d"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc82be2e22242d",
                        "ipAddress": "fe80::b09d:c0ff:fe99:282b",
                        "ipAddresses": [
                            "fe80::b09d:c0ff:fe99:282b"
                        ],
                        "mac": "b2:9d:c0:99:28:2b"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc36ced5a196c6",
                        "ipAddress": "fe80::e87f:2aff:feb8:3aa9",
                        "ipAddresses": [
                            "fe80::e87f:2aff:feb8:3aa9"
                        ],
                        "mac": "ea:7f:2a:b8:3a:a9"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc1c1bfb17992b",
                        "ipAddress": "fe80::f04f:8eff:fe59:e8f2",
                        "ipAddresses": [
                            "fe80::f04f:8eff:fe59:e8f2"
                        ],
                        "mac": "f2:4f:8e:59:e8:f2"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc6a3063f770f6",
                        "ipAddress": "fe80::a8b3:59ff:fe99:4427",
                        "ipAddresses": [
                            "fe80::a8b3:59ff:fe99:4427"
                        ],
                        "mac": "aa:b3:59:99:44:27"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcf1d4a36199af",
                        "ipAddress": "fe80::d417:9aff:fe90:91ef",
                        "ipAddresses": [
                            "fe80::d417:9aff:fe90:91ef"
                        ],
                        "mac": "d6:17:9a:90:91:ef"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc9eb03b404903",
                        "ipAddress": "fe80::1438:17ff:fe47:cbac",
                        "ipAddresses": [
                            "fe80::1438:17ff:fe47:cbac"
                        ],
                        "mac": "16:38:17:47:cb:ac"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc524565cdc263",
                        "ipAddress": "fe80::4ca4:c1ff:fe94:6281",
                        "ipAddresses": [
                            "fe80::4ca4:c1ff:fe94:6281"
                        ],
                        "mac": "4e:a4:c1:94:62:81"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc79335d64ac23",
                        "ipAddress": "fe80::34e5:13ff:feeb:137",
                        "ipAddresses": [
                            "fe80::34e5:13ff:feeb:137"
                        ],
                        "mac": "36:e5:13:eb:01:37"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc1373bc6d6429",
                        "ipAddress": "fe80::44d3:68ff:fed9:d9e1",
                        "ipAddresses": [
                            "fe80::44d3:68ff:fed9:d9e1"
                        ],
                        "mac": "46:d3:68:d9:d9:e1"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc6d0d00839e5f",
                        "ipAddress": "fe80::b8c2:7aff:fe0b:4cac",
                        "ipAddresses": [
                            "fe80::b8c2:7aff:fe0b:4cac"
                        ],
                        "mac": "ba:c2:7a:0b:4c:ac"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcfd2812ab73dc",
                        "ipAddress": "fe80::4023:90ff:fe6a:bfb6",
                        "ipAddresses": [
                            "fe80::4023:90ff:fe6a:bfb6"
                        ],
                        "mac": "42:23:90:6a:bf:b6"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc5425c468a2e7",
                        "ipAddress": "fe80::f0be:3aff:fe40:ca91",
                        "ipAddresses": [
                            "fe80::f0be:3aff:fe40:ca91"
                        ],
                        "mac": "f2:be:3a:40:ca:91"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcca1ac808369c",
                        "ipAddress": "fe80::8091:4fff:fef8:b52a",
                        "ipAddresses": [
                            "fe80::8091:4fff:fef8:b52a"
                        ],
                        "mac": "82:91:4f:f8:b5:2a"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxced1597169e3d",
                        "ipAddress": "fe80::10db:f1ff:fec8:f5ae",
                        "ipAddresses": [
                            "fe80::10db:f1ff:fec8:f5ae"
                        ],
                        "mac": "12:db:f1:c8:f5:ae"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc103da4cb6617",
                        "ipAddress": "fe80::d45d:bff:fefd:f4dd",
                        "ipAddresses": [
                            "fe80::d45d:bff:fefd:f4dd"
                        ],
                        "mac": "d6:5d:0b:fd:f4:dd"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc2b45d8963541",
                        "ipAddress": "fe80::e81a:ff:fe12:f70d",
                        "ipAddresses": [
                            "fe80::e81a:ff:fe12:f70d"
                        ],
                        "mac": "ea:1a:00:12:f7:0d"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc4210a269775c",
                        "ipAddress": "fe80::101e:e2ff:fef6:2669",
                        "ipAddresses": [
                            "fe80::101e:e2ff:fef6:2669"
                        ],
                        "mac": "12:1e:e2:f6:26:69"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcd94a164ef967",
                        "ipAddress": "fe80::c42a:1bff:fe7c:d1d4",
                        "ipAddresses": [
                            "fe80::c42a:1bff:fe7c:d1d4"
                        ],
                        "mac": "c6:2a:1b:7c:d1:d4"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc43ea0cbcc4c3",
                        "ipAddress": "fe80::a8ae:1ff:fe6b:647c",
                        "ipAddresses": [
                            "fe80::a8ae:1ff:fe6b:647c"
                        ],
                        "mac": "aa:ae:01:6b:64:7c"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc381b6388f1ac",
                        "ipAddress": "fe80::d0d2:77ff:feec:63d2",
                        "ipAddresses": [
                            "fe80::d0d2:77ff:feec:63d2"
                        ],
                        "mac": "d2:d2:77:ec:63:d2"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxca9fc6d3f4e2a",
                        "ipAddress": "fe80::4806:47ff:fee4:ffcf",
                        "ipAddresses": [
                            "fe80::4806:47ff:fee4:ffcf"
                        ],
                        "mac": "4a:06:47:e4:ff:cf"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcabd853f4ab10",
                        "ipAddress": "fe80::b434:5fff:fe38:8f6",
                        "ipAddresses": [
                            "fe80::b434:5fff:fe38:8f6"
                        ],
                        "mac": "b6:34:5f:38:08:f6"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxca14f4f782627",
                        "ipAddress": "fe80::7048:c9ff:fefc:fa19",
                        "ipAddresses": [
                            "fe80::7048:c9ff:fefc:fa19"
                        ],
                        "mac": "72:48:c9:fc:fa:19"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcb8e602cbe65c",
                        "ipAddress": "fe80::d0de:5cff:fe4d:fc5",
                        "ipAddresses": [
                            "fe80::d0de:5cff:fe4d:fc5"
                        ],
                        "mac": "d2:de:5c:4d:0f:c5"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc4ece43aeb3a4",
                        "ipAddress": "fe80::38b5:1bff:fe97:ab15",
                        "ipAddresses": [
                            "fe80::38b5:1bff:fe97:ab15"
                        ],
                        "mac": "3a:b5:1b:97:ab:15"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc3f362d21fb30",
                        "ipAddress": "fe80::a817:aff:feb8:1719",
                        "ipAddresses": [
                            "fe80::a817:aff:feb8:1719"
                        ],
                        "mac": "aa:17:0a:b8:17:19"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc603a868efbdf",
                        "ipAddress": "fe80::ac85:13ff:fe7b:8d95",
                        "ipAddresses": [
                            "fe80::ac85:13ff:fe7b:8d95"
                        ],
                        "mac": "ae:85:13:7b:8d:95"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc465a4d19a588",
                        "ipAddress": "fe80::14fe:5bff:fea9:122",
                        "ipAddresses": [
                            "fe80::14fe:5bff:fea9:122"
                        ],
                        "mac": "16:fe:5b:a9:01:22"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc9f0ccbcc0c43",
                        "ipAddress": "fe80::8c00:aeff:fea0:d065",
                        "ipAddresses": [
                            "fe80::8c00:aeff:fea0:d065"
                        ],
                        "mac": "8e:00:ae:a0:d0:65"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxcbc55cf927e9c",
                        "ipAddress": "fe80::20d2:3dff:fe38:212",
                        "ipAddresses": [
                            "fe80::20d2:3dff:fe38:212"
                        ],
                        "mac": "22:d2:3d:38:02:12"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc02ca47460b12",
                        "ipAddress": "fe80::e478:dfff:fe23:f028",
                        "ipAddresses": [
                            "fe80::e478:dfff:fe23:f028"
                        ],
                        "mac": "e6:78:df:23:f0:28"
                    },
                    {
                        "infoSource": "guest-agent",
                        "interfaceName": "lxc956627b8cd78",
                        "ipAddress": "fe80::94d2:19ff:fece:424",
                        "ipAddresses": [
                            "fe80::94d2:19ff:fece:424"
                        ],
                        "mac": "96:d2:19:ce:04:24"
                    }
                ],
                "launcherContainerImageVersion": "registry.redhat.io/container-native-virtualization/virt-launcher-rhel9@sha256:480f4dbd779497881b837aebe501c44078f74e1c6cef4dceb1ca617dbe38ea31",
                "machine": {
                    "type": "pc-q35-rhel9.4.0"
                },
                "memory": {
                    "guestAtBoot": "16Gi",
                    "guestCurrent": "16Gi",
                    "guestRequested": "16Gi"
                },
                "migrationMethod": "BlockMigration",
                "migrationTransport": "Unix",
                "nodeName": "1234abc",
                "phase": "Running",
                "phaseTransitionTimestamps": [
                    {
                        "phase": "Pending",
                        "phaseTransitionTimestamp": "2025-04-15T04:48:51Z"
                    },
                    {
                        "phase": "Scheduling",
                        "phaseTransitionTimestamp": "2025-04-15T04:48:51Z"
                    },
                    {
                        "phase": "Scheduled",
                        "phaseTransitionTimestamp": "2025-04-15T04:48:55Z"
                    },
                    {
                        "phase": "Running",
                        "phaseTransitionTimestamp": "2025-04-15T04:48:58Z"
                    }
                ],
                "qosClass": "Burstable",
                "runtimeUser": 107,
                "selinuxContext": "system_u:object_r:container_file_t:s0:c58,c385",
                "virtualMachineRevisionName": "revision-start-vm-2861c69e-b6bf-4c18-9cfe-19fed4fec0a0-12",
                "volumeStatus": [
                    {
                        "name": "cdrom",
                        "persistentVolumeClaimInfo": {
                            "accessModes": [
                                "ReadWriteMany"
                            ],
                            "capacity": {
                                "storage": "2Gi"
                            },
                            "claimName": "ocp-cilium-c1-agent",
                            "filesystemOverhead": "0",
                            "requests": {
                                "storage": "2G"
                            },
                            "volumeMode": "Block"
                        },
                        "target": "sda"
                    },
                    {
                        "name": "cloudinitdisk",
                        "size": 1048576,
                        "target": "vdb"
                    },
                    {
                        "name": "disk-gold-spider-93",
                        "persistentVolumeClaimInfo": {
                            "accessModes": [
                                "ReadWriteOnce"
                            ],
                            "capacity": {
                                "storage": "110960424Ki"
                            },
                            "claimName": "dv-cp-2-green-whale-28",
                            "filesystemOverhead": "0.055",
                            "requests": {
                                "storage": "113623473440"
                            },
                            "volumeMode": "Filesystem"
                        },
                        "target": "vda"
                    }
                ]
            }
        }
    ],
    "kind": "List",
    "metadata": {
        "resourceVersion": ""
    }
}


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


def create_nextHop(route: str, next_hop: str, tag="56001"):
    h = Expando()
    h.dn = "topology/pod-1/node-204/sys/uribv4/dom-calico1:vrf/db-rt/rt-[" + \
        route+"]/nh-[bgp-65002]-["+next_hop+"/32]-[unspecified]-[calico1:vrf]"
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

    def get_all_nexthops(self, apic: Node, dn: str):
        return self.nextHops

    def path_fixup(self, apic: Node, path):
        return path

    def get_overlay_ip_to_switch_map(self, apic: Node):
        nodes = {"192.168.2.5": "leaf 203"}
        return nodes


@patch('kubernetes.config.load_incluster_config', MagicMock(return_value=None))
@patch('pyaci.Node.useX509CertAuth', MagicMock(return_value=None))
@patch('kubernetes.client.CoreV1Api.list_pod_for_all_namespaces', MagicMock(return_value=client.V1PodList(api_version="1", items=pods)))
@patch('kubernetes.client.CustomObjectsApi.list_namespaced_custom_object', MagicMock(return_value=nfna))
@patch('kubernetes.client.CoreV1Api.list_service_for_all_namespaces', MagicMock(return_value=client.V1ServiceList(api_version="1", items=services)))
@patch('kubernetes.client.CustomObjectsApi.list_cluster_custom_object', MagicMock(return_value=vmis))
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
                                          'pods': {'dateformat': {'ip': '192.158.1.3', 'primary_iface': '', 'ns': 'dockerimage', 'labels': {'guest': 'frontend'}, 'other_ifaces': {}, 'annotations': {}},
                                                   'kube-router-xfgr': {'ip': '192.168.1.2', 'primary_iface': '', 'ns': 'kube-system', 'labels': {}, 'other_ifaces': {}, 'annotations': {}},
                                                   'sriov-pod': {'ip': '192.158.1.4', 'primary_iface': '', 'ns': 'dockerimage', 'labels': {'guest': 'frontend'}, 'other_ifaces': {'sriov-net1': 'ens1f2v12'}, 'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": ["192.158.1.5"], "mac": "02:a0:e8:00:00:0a", "name": "sriov-net1", "interface": "ens1f2v12"}]'}},
                                                   'macvlan-pod': {'ip': '192.158.1.6', 'primary_iface': '', 'ns': 'dockerimage', 'labels': {'guest': 'frontend'}, 'other_ifaces': {'macvlan-net1': 'net1'}, 'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": ["192.158.1.7"], "mac": "02:a0:e8:00:00:0a", "name": "macvlan-net1", "interface": "net1"}]'}},
                                                   'bridge-pod': {'ip': '192.158.1.7', 'primary_iface': '', 'ns': 'dockerimage', 'labels': {'guest': 'frontend'}, 'other_ifaces': {'br-net1': 'br-net1'}, 'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": ["192.158.1.8"], "mac": "02:a0:e8:00:00:0a", "name": "br-net1", "interface": "br-net1"}]'}}
                                                   },
                                          'vmis': {'cp-1': {'interfaces': [{'infoSource': 'domain, '
                                                                            'guest-agent, '
                                                                            'multus-status',
                                                                            'interfaceName': 'enp1s0',
                                                                            'ipAddress': '192.168.2.35',
                                                                            'ipAddresses': ['192.168.2.35'],
                                                                            'mac': '02:a0:e8:00:00:0a',
                                                                            'name': 'nic-gray-guineafowl-45',
                                                                            'queueCount': 1}],
                                                            'ns': 'ocp-cilium-c1'},
                                                   'cp-2': {'interfaces': [{'infoSource': 'domain, '
                                                                            'guest-agent, '
                                                                            'multus-status',
                                                                            'interfaceName': 'enp1s0',
                                                                            'ipAddress': '192.168.2.36',
                                                                            'ipAddresses': ['192.168.2.36'],
                                                                            'mac': '02:a0:e8:00:00:0c',
                                                                            'name': 'node',
                                                                            'queueCount': 1}],
                                                            'ns': 'ocp-cilium-c1'}},
                                          'bgp_peers': {'leaf-204': {'prefix_count': 2}}, 'neighbours': {'esxi4.cam.ciscolabs.com':
                                                                                                         {'switches': {'leaf-204': {'vmxnic1-eth1/1'}}, 'Description': 'VMware version 123'}},
                                          'labels': {'app': 'redis'}, 'node_leaf_sriov_iface_conn': [{
                                              'switch_name': 'leaf-101',
                                              'switch_interface': 'eth1/3',
                                              'node_iface': 'PF-ens1f2'
                                          }], 'node_pod_sriov_iface_conn': [{'node_iface': 'VF-ens1f2v12', 'pod_name': 'sriov-pod', 'node_network': 'sriov-net1', 'pod_iface': 'ens1f2v12', 'vlan': '[3456]'}],
                                          'node_leaf_macvlan_iface_conn': [{
                                              'switch_name': 'leaf-101',
                                              'switch_interface': 'eth1/37',
                                              'node_iface': 'bond1'}],
                                          'node_leaf_br_iface_conn': [{
                                              'switch_name': 'leaf-101',
                                              'switch_interface': 'eth1/38',
                                              'node_iface': 'br1'}],
                                          'node_pod_macvlan_iface_conn': [{'node_iface': 'net1', 'pod_name': 'macvlan-pod', 'node_network': 'macvlan-net1', 'pod_iface': 'net1', 'vlan': '[3456]'}],
                                          'node_pod_br_iface_conn': [{'ips': '192.158.1.8',
                                                                      'mac': '02:a0:e8:00:00:0a',
                                                                      'node_iface': 'br1',
                                                                      'node_network': 'bridge-net1',
                                                                      'pod_iface': 'br-net1',
                                                                      'pod_name': 'bridge-pod',
                                                                      'vlan': '[3456]'}
                                                                     ],
                                          'node_leaf_all_iface_conn': [{'switch_name': 'leaf-101', 'switch_interface': 'eth1/3', 'node_iface': 'PF-ens1f2'}, {'switch_name': 'leaf-101', 'switch_interface': 'eth1/37', 'node_iface': 'bond1'}, {'switch_name': 'leaf-101', 'switch_interface': 'eth1/38', 'node_iface': 'br1'}], 'mac': 'MOCKMO1C'}},
                    'services': {'appx': [{'name': 'example service', 'cluster_ip': '192.168.25.5', 'external_i_ps': ['192.168.5.1'], 'load_balancer_ip': '192.168.5.2', 'ns': 'appx',
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
                                          'mac': 'MOCKMO1C',
                                          'neighbours': {'CiscoLabs5': {'Description': 'Cisco '
                                                                        'version '
                                                                        '123',
                                                                        'switches': {'leaf-203': {'vmxnic2-eth1/1'}}}},
                                          'node_ip': '192.168.1.2',
                                          'node_leaf_all_iface_conn': [{'node_iface': 'PF-ens1f2',
                                                                        'switch_interface': 'eth1/3',
                                                                        'switch_name': 'leaf-101'},
                                                                       {'node_iface': 'bond1',
                                                                        'switch_interface': 'eth1/37',
                                                                        'switch_name': 'leaf-101'},
                                                                       {'node_iface': 'br1',
                                                                        'switch_interface': 'eth1/38',
                                                                        'switch_name': 'leaf-101'}],
                                          'node_leaf_br_iface_conn': [{'node_iface': 'br1',
                                                                       'switch_interface': 'eth1/38',
                                                                       'switch_name': 'leaf-101'}],
                                          'node_leaf_macvlan_iface_conn': [{'node_iface': 'bond1',
                                                                            'switch_interface': 'eth1/37',
                                                                            'switch_name': 'leaf-101'}],
                                          'node_leaf_sriov_iface_conn': [{'node_iface': 'PF-ens1f2',
                                                                          'switch_interface': 'eth1/3',
                                                                          'switch_name': 'leaf-101'}],
                                          'node_pod_br_iface_conn': [{'ips': '192.158.1.8',
                                                                      'mac': '02:a0:e8:00:00:0a',
                                                                      'node_iface': 'br1',
                                                                      'node_network': 'bridge-net1',
                                                                      'pod_iface': 'br-net1',
                                                                      'pod_name': 'bridge-pod',
                                                                      'vlan': '[3456]'}],
                                          'node_pod_macvlan_iface_conn': [{'node_iface': 'net1',
                                                                           'node_network': 'macvlan-net1',
                                                                           'pod_iface': 'net1',
                                                                           'pod_name': 'macvlan-pod',
                                                                           'vlan': '[3456]'}],
                                          'node_pod_sriov_iface_conn': [{'node_iface': 'VF-ens1f2v12',
                                                                         'node_network': 'sriov-net1',
                                                                         'pod_iface': 'ens1f2v12',
                                                                         'pod_name': 'sriov-pod',
                                                                         'vlan': '[3456]'}],
                                          'pods': {'bridge-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                  '["192.158.1.8"], '
                                                                                  '"mac": '
                                                                                  '"02:a0:e8:00:00:0a", '
                                                                                  '"name": '
                                                                                  '"br-net1", '
                                                                                  '"interface": '
                                                                                  '"br-net1"}]'},
                                                                  'ip': '192.158.1.7',
                                                                  'labels': {'guest': 'frontend'},
                                                                  'ns': 'dockerimage',
                                                                  'other_ifaces': {'br-net1': 'br-net1'},
                                                                  'primary_iface': ''},
                                                   'dateformat': {'annotations': {},
                                                                  'ip': '192.158.1.3',
                                                                  'labels': {'guest': 'frontend'},
                                                                  'ns': 'dockerimage',
                                                                  'other_ifaces': {},
                                                                  'primary_iface': ''},
                                                   'kube-router-xfgr': {'annotations': {},
                                                                        'ip': '192.168.1.2',
                                                                        'labels': {},
                                                                        'ns': 'kube-system',
                                                                        'other_ifaces': {},
                                                                        'primary_iface': ''},
                                                   'macvlan-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                   '["192.158.1.7"], '
                                                                                   '"mac": '
                                                                                   '"02:a0:e8:00:00:0a", '
                                                                                   '"name": '
                                                                                   '"macvlan-net1", '
                                                                                   '"interface": '
                                                                                   '"net1"}]'},
                                                                   'ip': '192.158.1.6',
                                                                   'labels': {'guest': 'frontend'},
                                                                   'ns': 'dockerimage',
                                                                   'other_ifaces': {'macvlan-net1': 'net1'},
                                                                   'primary_iface': ''},
                                                   'sriov-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                 '["192.158.1.5"], '
                                                                                 '"mac": '
                                                                                 '"02:a0:e8:00:00:0a", '
                                                                                 '"name": '
                                                                                 '"sriov-net1", '
                                                                                 '"interface": '
                                                                                 '"ens1f2v12"}]'},
                                                                 'ip': '192.158.1.4',
                                                                 'labels': {'guest': 'frontend'},
                                                                 'ns': 'dockerimage',
                                                                 'other_ifaces': {'sriov-net1': 'ens1f2v12'},
                                                                 'primary_iface': ''}},
                                          'vmis': {'cp-1': {'interfaces': [{'infoSource': 'domain, '
                                                                            'guest-agent, '
                                                                            'multus-status',
                                                                            'interfaceName': 'enp1s0',
                                                                            'ipAddress': '192.168.2.35',
                                                                            'ipAddresses': ['192.168.2.35'],
                                                                            'mac': '02:a0:e8:00:00:0a',
                                                                            'name': 'nic-gray-guineafowl-45',
                                                                            'queueCount': 1}],
                                                            'ns': 'ocp-cilium-c1'},
                                                   'cp-2': {'interfaces': [{'infoSource': 'domain, '
                                                                            'guest-agent, '
                                                                            'multus-status',
                                                                            'interfaceName': 'enp1s0',
                                                                            'ipAddress': '192.168.2.36',
                                                                            'ipAddresses': ['192.168.2.36'],
                                                                            'mac': '02:a0:e8:00:00:0c',
                                                                            'name': 'node',
                                                                            'queueCount': 1}],
                                                            'ns': 'ocp-cilium-c1'}}}},
                    'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                           'external_i_ps': ['192.168.5.1'],
                                           'labels': {'app': 'guestbook'},
                                           'load_balancer_ip': '192.168.5.2',
                                           'name': 'example service',
                                           'ns': 'appx'}]}}

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
                                          'mac': 'MOCKMO1C',
                                          'neighbours': {},
                                          'node_ip': '192.168.1.2',
                                          'node_leaf_all_iface_conn': [{'node_iface': 'PF-ens1f2',
                                                                        'switch_interface': 'eth1/3',
                                                                        'switch_name': 'leaf-101'},
                                                                       {'node_iface': 'bond1',
                                                                        'switch_interface': 'eth1/37',
                                                                        'switch_name': 'leaf-101'},
                                                                       {'node_iface': 'br1',
                                                                        'switch_interface': 'eth1/38',
                                                                        'switch_name': 'leaf-101'}],
                                          'node_leaf_br_iface_conn': [{'node_iface': 'br1',
                                                                       'switch_interface': 'eth1/38',
                                                                       'switch_name': 'leaf-101'}],
                                          'node_leaf_macvlan_iface_conn': [{'node_iface': 'bond1',
                                                                            'switch_interface': 'eth1/37',
                                                                            'switch_name': 'leaf-101'}],
                                          'node_leaf_sriov_iface_conn': [{'node_iface': 'PF-ens1f2',
                                                                          'switch_interface': 'eth1/3',
                                                                          'switch_name': 'leaf-101'}],
                                          'node_pod_br_iface_conn': [{'ips': '192.158.1.8',
                                                                      'mac': '02:a0:e8:00:00:0a',
                                                                      'node_iface': 'br1',
                                                                      'node_network': 'bridge-net1',
                                                                      'pod_iface': 'br-net1',
                                                                      'pod_name': 'bridge-pod',
                                                                      'vlan': '[3456]'}],
                                          'node_pod_macvlan_iface_conn': [{'node_iface': 'net1',
                                                                           'node_network': 'macvlan-net1',
                                                                           'pod_iface': 'net1',
                                                                           'pod_name': 'macvlan-pod',
                                                                           'vlan': '[3456]'}],
                                          'node_pod_sriov_iface_conn': [{'node_iface': 'VF-ens1f2v12',
                                                                         'node_network': 'sriov-net1',
                                                                         'pod_iface': 'ens1f2v12',
                                                                         'pod_name': 'sriov-pod',
                                                                         'vlan': '[3456]'}],
                                          'pods': {'bridge-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                  '["192.158.1.8"], '
                                                                                  '"mac": '
                                                                                  '"02:a0:e8:00:00:0a", '
                                                                                  '"name": '
                                                                                  '"br-net1", '
                                                                                  '"interface": '
                                                                                  '"br-net1"}]'},
                                                                  'ip': '192.158.1.7',
                                                                  'labels': {'guest': 'frontend'},
                                                                  'ns': 'dockerimage',
                                                                  'other_ifaces': {'br-net1': 'br-net1'},
                                                                  'primary_iface': ''},
                                                   'dateformat': {'annotations': {},
                                                                  'ip': '192.158.1.3',
                                                                  'labels': {'guest': 'frontend'},
                                                                  'ns': 'dockerimage',
                                                                  'other_ifaces': {},
                                                                  'primary_iface': ''},
                                                   'kube-router-xfgr': {'annotations': {},
                                                                        'ip': '192.168.1.2',
                                                                        'labels': {},
                                                                        'ns': 'kube-system',
                                                                        'other_ifaces': {},
                                                                        'primary_iface': ''},
                                                   'macvlan-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                   '["192.158.1.7"], '
                                                                                   '"mac": '
                                                                                   '"02:a0:e8:00:00:0a", '
                                                                                   '"name": '
                                                                                   '"macvlan-net1", '
                                                                                   '"interface": '
                                                                                   '"net1"}]'},
                                                                   'ip': '192.158.1.6',
                                                                   'labels': {'guest': 'frontend'},
                                                                   'ns': 'dockerimage',
                                                                   'other_ifaces': {'macvlan-net1': 'net1'},
                                                                   'primary_iface': ''},
                                                   'sriov-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                 '["192.158.1.5"], '
                                                                                 '"mac": '
                                                                                 '"02:a0:e8:00:00:0a", '
                                                                                 '"name": '
                                                                                 '"sriov-net1", '
                                                                                 '"interface": '
                                                                                 '"ens1f2v12"}]'},
                                                                 'ip': '192.158.1.4',
                                                                 'labels': {'guest': 'frontend'},
                                                                 'ns': 'dockerimage',
                                                                 'other_ifaces': {'sriov-net1': 'ens1f2v12'},
                                                                 'primary_iface': ''}},
                                          'vmis': {'cp-1': {'interfaces': [{'infoSource': 'domain, '
                                                                            'guest-agent, '
                                                                            'multus-status',
                                                                            'interfaceName': 'enp1s0',
                                                                            'ipAddress': '192.168.2.35',
                                                                            'ipAddresses': ['192.168.2.35'],
                                                                            'mac': '02:a0:e8:00:00:0a',
                                                                            'name': 'nic-gray-guineafowl-45',
                                                                            'queueCount': 1}],
                                                            'ns': 'ocp-cilium-c1'},
                                                   'cp-2': {'interfaces': [{'infoSource': 'domain, '
                                                                            'guest-agent, '
                                                                            'multus-status',
                                                                            'interfaceName': 'enp1s0',
                                                                            'ipAddress': '192.168.2.36',
                                                                            'ipAddresses': ['192.168.2.36'],
                                                                            'mac': '02:a0:e8:00:00:0c',
                                                                            'name': 'node',
                                                                            'queueCount': 1}],
                                                            'ns': 'ocp-cilium-c1'}}}},
                    'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                           'external_i_ps': ['192.168.5.1'],
                                           'labels': {'app': 'guestbook'},
                                           'load_balancer_ip': '192.168.5.2',
                                           'name': 'example service',
                                           'ns': 'appx'}]}}

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
                                          'mac': 'MOCKMO1C',
                                          'neighbours': {'esxi4.cam.ciscolabs.com': {'Description': '',
                                                                                     'switches': {'leaf-204': set()}}},
                                          'node_ip': '192.168.1.2',
                                          'node_leaf_all_iface_conn': [{'node_iface': 'PF-ens1f2',
                                                                        'switch_interface': 'eth1/3',
                                                                        'switch_name': 'leaf-101'},
                                                                       {'node_iface': 'bond1',
                                                                        'switch_interface': 'eth1/37',
                                                                        'switch_name': 'leaf-101'},
                                                                       {'node_iface': 'br1',
                                                                        'switch_interface': 'eth1/38',
                                                                        'switch_name': 'leaf-101'}],
                                          'node_leaf_br_iface_conn': [{'node_iface': 'br1',
                                                                       'switch_interface': 'eth1/38',
                                                                       'switch_name': 'leaf-101'}],
                                          'node_leaf_macvlan_iface_conn': [{'node_iface': 'bond1',
                                                                            'switch_interface': 'eth1/37',
                                                                            'switch_name': 'leaf-101'}],
                                          'node_leaf_sriov_iface_conn': [{'node_iface': 'PF-ens1f2',
                                                                          'switch_interface': 'eth1/3',
                                                                          'switch_name': 'leaf-101'}],
                                          'node_pod_br_iface_conn': [{'ips': '192.158.1.8',
                                                                      'mac': '02:a0:e8:00:00:0a',
                                                                      'node_iface': 'br1',
                                                                      'node_network': 'bridge-net1',
                                                                      'pod_iface': 'br-net1',
                                                                      'pod_name': 'bridge-pod',
                                                                      'vlan': '[3456]'}],
                                          'node_pod_macvlan_iface_conn': [{'node_iface': 'net1',
                                                                           'node_network': 'macvlan-net1',
                                                                           'pod_iface': 'net1',
                                                                           'pod_name': 'macvlan-pod',
                                                                           'vlan': '[3456]'}],
                                          'node_pod_sriov_iface_conn': [{'node_iface': 'VF-ens1f2v12',
                                                                         'node_network': 'sriov-net1',
                                                                         'pod_iface': 'ens1f2v12',
                                                                         'pod_name': 'sriov-pod',
                                                                         'vlan': '[3456]'}],
                                          'pods': {'bridge-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                  '["192.158.1.8"], '
                                                                                  '"mac": '
                                                                                  '"02:a0:e8:00:00:0a", '
                                                                                  '"name": '
                                                                                  '"br-net1", '
                                                                                  '"interface": '
                                                                                  '"br-net1"}]'},
                                                                  'ip': '192.158.1.7',
                                                                  'labels': {'guest': 'frontend'},
                                                                  'ns': 'dockerimage',
                                                                  'other_ifaces': {'br-net1': 'br-net1'},
                                                                  'primary_iface': ''},
                                                   'dateformat': {'annotations': {},
                                                                  'ip': '192.158.1.3',
                                                                  'labels': {'guest': 'frontend'},
                                                                  'ns': 'dockerimage',
                                                                  'other_ifaces': {},
                                                                  'primary_iface': ''},
                                                   'kube-router-xfgr': {'annotations': {},
                                                                        'ip': '192.168.1.2',
                                                                        'labels': {},
                                                                        'ns': 'kube-system',
                                                                        'other_ifaces': {},
                                                                        'primary_iface': ''},
                                                   'macvlan-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                   '["192.158.1.7"], '
                                                                                   '"mac": '
                                                                                   '"02:a0:e8:00:00:0a", '
                                                                                   '"name": '
                                                                                   '"macvlan-net1", '
                                                                                   '"interface": '
                                                                                   '"net1"}]'},
                                                                   'ip': '192.158.1.6',
                                                                   'labels': {'guest': 'frontend'},
                                                                   'ns': 'dockerimage',
                                                                   'other_ifaces': {'macvlan-net1': 'net1'},
                                                                   'primary_iface': ''},
                                                   'sriov-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                 '["192.158.1.5"], '
                                                                                 '"mac": '
                                                                                 '"02:a0:e8:00:00:0a", '
                                                                                 '"name": '
                                                                                 '"sriov-net1", '
                                                                                 '"interface": '
                                                                                 '"ens1f2v12"}]'},
                                                                 'ip': '192.158.1.4',
                                                                 'labels': {'guest': 'frontend'},
                                                                 'ns': 'dockerimage',
                                                                 'other_ifaces': {'sriov-net1': 'ens1f2v12'},
                                                                 'primary_iface': ''}},
                                          'vmis': {'cp-1': {'interfaces': [{'infoSource': 'domain, '
                                                                            'guest-agent, '
                                                                            'multus-status',
                                                                            'interfaceName': 'enp1s0',
                                                                            'ipAddress': '192.168.2.35',
                                                                            'ipAddresses': ['192.168.2.35'],
                                                                            'mac': '02:a0:e8:00:00:0a',
                                                                            'name': 'nic-gray-guineafowl-45',
                                                                            'queueCount': 1}],
                                                            'ns': 'ocp-cilium-c1'},
                                                   'cp-2': {'interfaces': [{'infoSource': 'domain, '
                                                                            'guest-agent, '
                                                                            'multus-status',
                                                                            'interfaceName': 'enp1s0',
                                                                            'ipAddress': '192.168.2.36',
                                                                            'ipAddresses': ['192.168.2.36'],
                                                                            'mac': '02:a0:e8:00:00:0c',
                                                                            'name': 'node',
                                                                            'queueCount': 1}],
                                                            'ns': 'ocp-cilium-c1'}}}},
                    'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                           'external_i_ps': ['192.168.5.1'],
                                           'labels': {'app': 'guestbook'},
                                           'load_balancer_ip': '192.168.5.2',
                                           'name': 'example service',
                                           'ns': 'appx'}]}}

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
                                                    'value': 'kube-router-xfgr'},
                                                   {'value': 'sriov-pod', 'ip': '192.158.1.4',
                                                    'ns': 'dockerimage', 'image': 'pod.svg'},
                                                   {'value': 'macvlan-pod', 'ip': '192.158.1.6',
                                                       'ns': 'dockerimage', 'image': 'pod.svg'},
                                                   {'value': 'bridge-pod', 'ip': '192.158.1.7',
                                                       'ns': 'dockerimage', 'image': 'pod.svg'}
                                                   ],
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
                                           'data': [{'value': 'dateformat', 'ip': '192.158.1.3', 'ns': 'dockerimage', 'image': 'pod.svg',
                                                     'data': [{'value': 'guest', 'label_value': 'frontend', 'image': 'label.svg'}]},
                                                    {'value': 'kube-router-xfgr', 'ip': '192.168.1.2', 'ns': 'kube-system', 'image': 'pod.svg',
                                                     'data': []},
                                                    {
                                                        'value': 'sriov-pod', 'ip': '192.158.1.4', 'ns': 'dockerimage', 'image': 'pod.svg', 'data': [{'value': 'guest', 'label_value': 'frontend', 'image': 'label.svg'}]
                                           },
                                               {
                                                        'value': 'macvlan-pod', 'ip': '192.158.1.6', 'ns': 'dockerimage', 'image': 'pod.svg', 'data': [{'value': 'guest', 'label_value': 'frontend', 'image': 'label.svg'}]
                                           },
                                               {
                                                        'value': 'bridge-pod', 'ip': '192.158.1.7', 'ns': 'dockerimage', 'image': 'pod.svg', 'data': [{'value': 'guest', 'label_value': 'frontend', 'image': 'label.svg'}]
                                           }
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
        expected = {'parent': 0, 'data': [{'name': 'example service', 'cluster_ip': '192.168.25.5', 'external_i_ps': ['192.168.5.1'], 'load_balancer_ip': '192.168.5.2',
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
            {"spec": {"bgpInstances": [
                {'localASN': 56003}, {'localASN': 56003}]}}
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
            {"spec": {"bgpInstances": [
                {'localASN': 56003}, {'localASN': 56004}]}}
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

    def test_sriov(self):
        sriov_pod = [
            client.V1Pod(
                status=client.V1PodStatus(
                    host_ip="192.168.1.2", pod_ip="192.158.1.4"
                ),
                metadata=client.V1ObjectMeta(
                    name="sriov-pod", namespace="dockerimage", labels={"guest": "frontend"}, annotations={"k8s.v1.cni.cncf.io/network-status": json.dumps([{"ips": ["192.158.1.5"], "mac": "02:a0:e8:00:00:0a", "name": "sriov-net1", "interface": "ens1f2v12"}])}
                ),

                spec=client.V1PodSpec(
                    node_name="1234abc", containers=[]
                )
            )
        ]
        sriov_nfna = {
            "items": [{
                "spec": {
                    "aciTopology": {
                        "ens1f2":
                            {
                                "fabricLink": [
                                    "abc/def/node-101/[eth1/3]"
                                ],
                                "pods": [
                                    {
                                        "localIface": "ens1f2v12",
                                        "podRef": {
                                            "name": "sriov-pod"
                                        }
                                    }
                                ]
                            }
                    },
                    "nodeName": "1234abc",
                    "encapVlan": {
                        "encapRef": {
                            "key": "",
                            "nadVlanMap": ""
                        },
                        "mode": "Trunk",
                        "vlanList": "[3456]"
                    },
                    "networkRef": {
                        "name": "sriov-net1"
                    },
                    "primaryCni": "sriov"
                },
                "metadata": {
                    "name": "sriov"
                }
            }]
        }
        with patch('kubernetes.client.CoreV1Api.list_pod_for_all_namespaces', MagicMock(return_value=client.V1PodList(api_version="1", items=sriov_pod))):
            with patch('kubernetes.client.CustomObjectsApi.list_namespaced_custom_object', MagicMock(return_value=sriov_nfna)):
                expected = {'nodes': {'1234abc': {'bgp_peers': {'leaf-204': {'prefix_count': 2}},
                                                  'labels': {'app': 'redis'},
                                                  'mac': 'MOCKMO1C',
                                                  'neighbours': {'esxi4.cam.ciscolabs.com': {'Description': 'VMware '
                                                                                             'version '
                                                                                             '123',
                                                                                             'switches': {'leaf-204': {'vmxnic1-eth1/1'}}}},
                                                  'node_ip': '192.168.1.2',
                                                  'node_leaf_all_iface_conn': [{'node_iface': 'PF-ens1f2',
                                                                                'switch_interface': 'eth1/3',
                                                                                'switch_name': 'leaf-101'}],
                                                  'node_leaf_br_iface_conn': [],
                                                  'node_leaf_macvlan_iface_conn': [],
                                                  'node_leaf_sriov_iface_conn': [{'node_iface': 'PF-ens1f2',
                                                                                  'switch_interface': 'eth1/3',
                                                                                  'switch_name': 'leaf-101'}],
                                                  'node_pod_br_iface_conn': [],
                                                  'node_pod_macvlan_iface_conn': [],
                                                  'node_pod_sriov_iface_conn': [{'node_iface': 'VF-ens1f2v12',
                                                                                 'node_network': 'sriov-net1',
                                                                                 'pod_iface': 'ens1f2v12',
                                                                                 'pod_name': 'sriov-pod',
                                                                                 'vlan': '[3456]'}],
                                                  'pods': {'sriov-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                         '["192.158.1.5"], '
                                                                                         '"mac": '
                                                                                         '"02:a0:e8:00:00:0a", '
                                                                                         '"name": '
                                                                                         '"sriov-net1", '
                                                                                         '"interface": '
                                                                                         '"ens1f2v12"}]'},
                                                                         'ip': '192.158.1.4',
                                                                         'labels': {'guest': 'frontend'},
                                                                         'ns': 'dockerimage',
                                                                         'other_ifaces': {'sriov-net1': 'ens1f2v12'},
                                                                         'primary_iface': ''}},
                                                  'vmis': {'cp-1': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.35',
                                                                                    'ipAddresses': ['192.168.2.35'],
                                                                                    'mac': '02:a0:e8:00:00:0a',
                                                                                    'name': 'nic-gray-guineafowl-45',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'},
                                                           'cp-2': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.36',
                                                                                    'ipAddresses': ['192.168.2.36'],
                                                                                    'mac': '02:a0:e8:00:00:0c',
                                                                                    'name': 'node',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'}}}},
                            'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                                   'external_i_ps': ['192.168.5.1'],
                                                   'labels': {'app': 'guestbook'},
                                                   'load_balancer_ip': '192.168.5.2',
                                                   'name': 'example service',
                                                   'ns': 'appx'}]}}

                build = VkaciBuilTopology(
                    VkaciEnvVariables(self.vars), ApicMethodsMock())
                # Act
                result = build.update()
                # Assert
                self.assertDictEqual(result, expected)
                self.assertEqual(build.aci_vrf, "uni/tn-Ciscolive/ctx-vrf-01")

    def test_macvlan(self):
        macvlan_pod = [
            client.V1Pod(
                status=client.V1PodStatus(
                    host_ip="192.168.1.2", pod_ip="192.158.1.6"
                ),
                metadata=client.V1ObjectMeta(
                    name="macvlan-pod", namespace="dockerimage", labels={"guest": "frontend"}, annotations={"k8s.v1.cni.cncf.io/network-status": json.dumps([{"ips": ["192.158.1.7"], "mac": "02:a0:e8:00:00:0a", "name": "macvlan-net1", "interface": "net1"}])}
                ),
                spec=client.V1PodSpec(
                    node_name="1234abc", containers=[]
                )
            )
        ]
        macvlan_nfna = {
            "items": [{
                "spec": {
                    "aciTopology": {
                        "bond1":
                            {
                                "fabricLink": [
                                    "abc/def/node-101/[eth1/37]"
                                ],
                                "pods": [
                                    {
                                        "localIface": "net1",
                                        "podRef": {
                                            "name": "macvlan-pod"
                                        }
                                    }
                                ]
                            }
                    },
                    "nodeName": "1234abc",
                    "encapVlan": {
                        "encapRef": {
                            "key": "",
                            "nadVlanMap": ""
                        },
                        "mode": "Trunk",
                        "vlanList": "[3456]"
                    },
                    "networkRef": {
                        "name": "macvlan-net1"
                    },
                    "primaryCni": "macvlan"
                },
                "metadata": {
                    "name": "macvlan"
                }
            }]
        }
        with patch('kubernetes.client.CoreV1Api.list_pod_for_all_namespaces', MagicMock(return_value=client.V1PodList(api_version="1", items=macvlan_pod))):
            with patch('kubernetes.client.CustomObjectsApi.list_namespaced_custom_object', MagicMock(return_value=macvlan_nfna)):
                expected = {'nodes': {'1234abc': {'bgp_peers': {'leaf-204': {'prefix_count': 2}},
                                                  'labels': {'app': 'redis'},
                                                  'mac': 'MOCKMO1C',
                                                  'neighbours': {'esxi4.cam.ciscolabs.com': {'Description': 'VMware '
                                                                                             'version '
                                                                                             '123',
                                                                                             'switches': {'leaf-204': {'vmxnic1-eth1/1'}}}},
                                                  'node_ip': '192.168.1.2',
                                                  'node_leaf_all_iface_conn': [{'node_iface': 'bond1',
                                                                                'switch_interface': 'eth1/37',
                                                                                'switch_name': 'leaf-101'}],
                                                  'node_leaf_br_iface_conn': [],
                                                  'node_leaf_macvlan_iface_conn': [{'node_iface': 'bond1',
                                                                                    'switch_interface': 'eth1/37',
                                                                                    'switch_name': 'leaf-101'}],
                                                  'node_leaf_sriov_iface_conn': [],
                                                  'node_pod_br_iface_conn': [],
                                                  'node_pod_macvlan_iface_conn': [{'node_iface': 'net1',
                                                                                   'node_network': 'macvlan-net1',
                                                                                   'pod_iface': 'net1',
                                                                                   'pod_name': 'macvlan-pod',
                                                                                   'vlan': '[3456]'}],
                                                  'node_pod_sriov_iface_conn': [],
                                                  'pods': {'macvlan-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                           '["192.158.1.7"], '
                                                                                           '"mac": '
                                                                                           '"02:a0:e8:00:00:0a", '
                                                                                           '"name": '
                                                                                           '"macvlan-net1", '
                                                                                           '"interface": '
                                                                                           '"net1"}]'},
                                                                           'ip': '192.158.1.6',
                                                                           'labels': {'guest': 'frontend'},
                                                                           'ns': 'dockerimage',
                                                                           'other_ifaces': {'macvlan-net1': 'net1'},
                                                                           'primary_iface': ''}},
                                                  'vmis': {'cp-1': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.35',
                                                                                    'ipAddresses': ['192.168.2.35'],
                                                                                    'mac': '02:a0:e8:00:00:0a',
                                                                                    'name': 'nic-gray-guineafowl-45',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'},
                                                           'cp-2': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.36',
                                                                                    'ipAddresses': ['192.168.2.36'],
                                                                                    'mac': '02:a0:e8:00:00:0c',
                                                                                    'name': 'node',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'}}}},
                            'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                                   'external_i_ps': ['192.168.5.1'],
                                                   'labels': {'app': 'guestbook'},
                                                   'load_balancer_ip': '192.168.5.2',
                                                   'name': 'example service',
                                                   'ns': 'appx'}]}}

                build = VkaciBuilTopology(
                    VkaciEnvVariables(self.vars), ApicMethodsMock())
                # Act
                result = build.update()
                # Assert
                self.assertDictEqual(result, expected)
                self.assertEqual(build.aci_vrf, "uni/tn-Ciscolive/ctx-vrf-01")

    def test_bridge(self):
        br_pod = [
            client.V1Pod(
                status=client.V1PodStatus(
                    host_ip="192.168.1.2", pod_ip="192.158.1.8"
                ),
                metadata=client.V1ObjectMeta(
                    name="bridge-pod", namespace="dockerimage", labels={"guest": "frontend"}, annotations={"k8s.v1.cni.cncf.io/network-status": json.dumps([{"ips": ["192.158.1.8"], "mac": "02:a0:e8:00:00:0a", "name": "br-net1", "interface": "br-net1"}])}
                ),
                spec=client.V1PodSpec(
                    node_name="1234abc", containers=[]
                )
            )
        ]
        br_nfna = {
            "items": [{
                "spec": {
                    "aciTopology": {
                        "br0":
                            {
                                "fabricLink": [
                                    "abc/def/node-101/[eth1/38]"
                                ],
                                "pods": [
                                    {
                                        "localIface": "br-net1",
                                        "podRef": {
                                            "name": "bridge-pod"
                                        }
                                    }
                                ]
                            }
                    },
                    "nodeName": "1234abc",
                    "encapVlan": {
                        "encapRef": {
                            "key": "",
                            "nadVlanMap": ""
                        },
                        "mode": "Trunk",
                        "vlanList": "[3456]"
                    },
                    "networkRef": {
                        "name": "br-net1"
                    },
                    "primaryCni": "bridge"
                },
                "metadata": {
                    "name": "bridge"
                }
            }]
        }
        with patch('kubernetes.client.CoreV1Api.list_pod_for_all_namespaces', MagicMock(return_value=client.V1PodList(api_version="1", items=br_pod))):
            with patch('kubernetes.client.CustomObjectsApi.list_namespaced_custom_object', MagicMock(return_value=br_nfna)):
                expected = {'nodes': {'1234abc': {'bgp_peers': {'leaf-204': {'prefix_count': 2}},
                                                  'labels': {'app': 'redis'},
                                                  'mac': 'MOCKMO1C',
                                                  'neighbours': {'esxi4.cam.ciscolabs.com': {'Description': 'VMware '
                                                                                             'version '
                                                                                             '123',
                                                                                             'switches': {'leaf-204': {'vmxnic1-eth1/1'}}}},
                                                  'node_ip': '192.168.1.2',
                                                  'node_leaf_all_iface_conn': [{'node_iface': 'br0',
                                                                                'switch_interface': 'eth1/38',
                                                                                'switch_name': 'leaf-101'}],
                                                  'node_leaf_br_iface_conn': [{'node_iface': 'br0',
                                                                               'switch_interface': 'eth1/38',
                                                                               'switch_name': 'leaf-101'}],
                                                  'node_leaf_macvlan_iface_conn': [],
                                                  'node_leaf_sriov_iface_conn': [],
                                                  'node_pod_br_iface_conn': [{'ips': '192.158.1.8',
                                                                              'mac': '02:a0:e8:00:00:0a',
                                                                              'node_iface': 'br0',
                                                                              'node_network': 'br-net1',
                                                                              'pod_iface': 'br-net1',
                                                                              'pod_name': 'bridge-pod',
                                                                              'vlan': '[3456]'}],
                                                  'node_pod_macvlan_iface_conn': [],
                                                  'node_pod_sriov_iface_conn': [],
                                                  'pods': {'bridge-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                          '["192.158.1.8"], '
                                                                                          '"mac": '
                                                                                          '"02:a0:e8:00:00:0a", '
                                                                                          '"name": '
                                                                                          '"br-net1", '
                                                                                          '"interface": '
                                                                                          '"br-net1"}]'},
                                                                          'ip': '192.158.1.8',
                                                                          'labels': {'guest': 'frontend'},
                                                                          'ns': 'dockerimage',
                                                                          'other_ifaces': {'br-net1': 'br-net1'},
                                                                          'primary_iface': ''}},
                                                  'vmis': {'cp-1': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.35',
                                                                                    'ipAddresses': ['192.168.2.35'],
                                                                                    'mac': '02:a0:e8:00:00:0a',
                                                                                    'name': 'nic-gray-guineafowl-45',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'},
                                                           'cp-2': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.36',
                                                                                    'ipAddresses': ['192.168.2.36'],
                                                                                    'mac': '02:a0:e8:00:00:0c',
                                                                                    'name': 'node',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'}}}},
                            'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                                   'external_i_ps': ['192.168.5.1'],
                                                   'labels': {'app': 'guestbook'},
                                                   'load_balancer_ip': '192.168.5.2',
                                                   'name': 'example service',
                                                   'ns': 'appx'}]}}

                build = VkaciBuilTopology(
                    VkaciEnvVariables(self.vars), ApicMethodsMock())
                # Act
                result = build.update()
                # Assert
                self.assertDictEqual(result, expected)
                self.assertEqual(build.aci_vrf, "uni/tn-Ciscolive/ctx-vrf-01")

    def test_sriov_macvlan_br_only(self):
        pods = [
            client.V1Pod(
                status=client.V1PodStatus(
                    host_ip="192.168.1.2", pod_ip="192.158.1.4"
                ),
                metadata=client.V1ObjectMeta(
                    name="sriov-pod", namespace="dockerimage", labels={"guest": "frontend"}, annotations={"k8s.v1.cni.cncf.io/network-status": json.dumps([{"ips": ["192.158.1.5"], "mac": "02:a0:e8:00:00:0a", "name": "sriov-net1", "interface": "ens1f2v12"}])}
                ),
                spec=client.V1PodSpec(
                    node_name="1234abc", containers=[]
                )
            ),
            client.V1Pod(
                status=client.V1PodStatus(
                    host_ip="192.168.1.2", pod_ip="192.158.1.8"
                ),
                metadata=client.V1ObjectMeta(
                    name="bridge-pod", namespace="dockerimage", labels={"guest": "frontend"}, annotations={"k8s.v1.cni.cncf.io/network-status": json.dumps([{"ips": ["192.158.1.8"], "mac": "02:a0:e8:00:00:0a", "name": "br-net1", "interface": "br-net1"}])}
                ),
                spec=client.V1PodSpec(
                    node_name="1234abc", containers=[]
                )
            ),
            client.V1Pod(
                status=client.V1PodStatus(
                    host_ip="192.168.1.2", pod_ip="192.158.1.6"
                ),
                metadata=client.V1ObjectMeta(
                    name="macvlan-pod", namespace="dockerimage", labels={"guest": "frontend"}, annotations={"k8s.v1.cni.cncf.io/network-status": json.dumps([{"ips": ["192.158.1.7"], "mac": "02:a0:e8:00:00:0a", "name": "macvlan-net1", "interface": "net1"}])}
                ),
                spec=client.V1PodSpec(
                    node_name="1234abc", containers=[]
                )
            )
        ]

        with patch('kubernetes.client.CoreV1Api.list_pod_for_all_namespaces', MagicMock(return_value=client.V1PodList(api_version="1", items=pods))):
            with patch('kubernetes.client.CustomObjectsApi.list_namespaced_custom_object', MagicMock(return_value=nfna)):
                expected = {'nodes': {'1234abc': {'bgp_peers': {'leaf-204': {'prefix_count': 2}},
                                                  'labels': {'app': 'redis'},
                                                  'mac': 'MOCKMO1C',
                                                  'neighbours': {'esxi4.cam.ciscolabs.com': {'Description': 'VMware '
                                                                                             'version '
                                                                                             '123',
                                                                                             'switches': {'leaf-204': {'vmxnic1-eth1/1'}}}},
                                                  'node_ip': '192.168.1.2',
                                                  'node_leaf_all_iface_conn': [{'node_iface': 'PF-ens1f2',
                                                                                'switch_interface': 'eth1/3',
                                                                                'switch_name': 'leaf-101'},
                                                                               {'node_iface': 'bond1',
                                                                                'switch_interface': 'eth1/37',
                                                                                'switch_name': 'leaf-101'},
                                                                               {'node_iface': 'br1',
                                                                                'switch_interface': 'eth1/38',
                                                                                'switch_name': 'leaf-101'}],
                                                  'node_leaf_br_iface_conn': [{'node_iface': 'br1',
                                                                               'switch_interface': 'eth1/38',
                                                                               'switch_name': 'leaf-101'}],
                                                  'node_leaf_macvlan_iface_conn': [{'node_iface': 'bond1',
                                                                                    'switch_interface': 'eth1/37',
                                                                                    'switch_name': 'leaf-101'}],
                                                  'node_leaf_sriov_iface_conn': [{'node_iface': 'PF-ens1f2',
                                                                                  'switch_interface': 'eth1/3',
                                                                                  'switch_name': 'leaf-101'}],
                                                  'node_pod_br_iface_conn': [{'ips': '192.158.1.8',
                                                                              'mac': '02:a0:e8:00:00:0a',
                                                                              'node_iface': 'br1',
                                                                              'node_network': 'bridge-net1',
                                                                              'pod_iface': 'br-net1',
                                                                              'pod_name': 'bridge-pod',
                                                                              'vlan': '[3456]'}],
                                                  'node_pod_macvlan_iface_conn': [{'node_iface': 'net1',
                                                                                   'node_network': 'macvlan-net1',
                                                                                   'pod_iface': 'net1',
                                                                                   'pod_name': 'macvlan-pod',
                                                                                   'vlan': '[3456]'}],
                                                  'node_pod_sriov_iface_conn': [{'node_iface': 'VF-ens1f2v12',
                                                                                 'node_network': 'sriov-net1',
                                                                                 'pod_iface': 'ens1f2v12',
                                                                                 'pod_name': 'sriov-pod',
                                                                                 'vlan': '[3456]'}],
                                                  'pods': {'bridge-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                          '["192.158.1.8"], '
                                                                                          '"mac": '
                                                                                          '"02:a0:e8:00:00:0a", '
                                                                                          '"name": '
                                                                                          '"br-net1", '
                                                                                          '"interface": '
                                                                                          '"br-net1"}]'},
                                                                          'ip': '192.158.1.8',
                                                                          'labels': {'guest': 'frontend'},
                                                                          'ns': 'dockerimage',
                                                                          'other_ifaces': {'br-net1': 'br-net1'},
                                                                          'primary_iface': ''},
                                                           'macvlan-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                           '["192.158.1.7"], '
                                                                                           '"mac": '
                                                                                           '"02:a0:e8:00:00:0a", '
                                                                                           '"name": '
                                                                                           '"macvlan-net1", '
                                                                                           '"interface": '
                                                                                           '"net1"}]'},
                                                                           'ip': '192.158.1.6',
                                                                           'labels': {'guest': 'frontend'},
                                                                           'ns': 'dockerimage',
                                                                           'other_ifaces': {'macvlan-net1': 'net1'},
                                                                           'primary_iface': ''},
                                                           'sriov-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                         '["192.158.1.5"], '
                                                                                         '"mac": '
                                                                                         '"02:a0:e8:00:00:0a", '
                                                                                         '"name": '
                                                                                         '"sriov-net1", '
                                                                                         '"interface": '
                                                                                         '"ens1f2v12"}]'},
                                                                         'ip': '192.158.1.4',
                                                                         'labels': {'guest': 'frontend'},
                                                                         'ns': 'dockerimage',
                                                                         'other_ifaces': {'sriov-net1': 'ens1f2v12'},
                                                                         'primary_iface': ''}},
                                                  'vmis': {'cp-1': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.35',
                                                                                    'ipAddresses': ['192.168.2.35'],
                                                                                    'mac': '02:a0:e8:00:00:0a',
                                                                                    'name': 'nic-gray-guineafowl-45',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'},
                                                           'cp-2': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.36',
                                                                                    'ipAddresses': ['192.168.2.36'],
                                                                                    'mac': '02:a0:e8:00:00:0c',
                                                                                    'name': 'node',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'}}}},
                            'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                                   'external_i_ps': ['192.168.5.1'],
                                                   'labels': {'app': 'guestbook'},
                                                   'load_balancer_ip': '192.168.5.2',
                                                   'name': 'example service',
                                                   'ns': 'appx'}]}}

                build = VkaciBuilTopology(
                    VkaciEnvVariables(self.vars), ApicMethodsMock())
                # Act
                result = build.update()
                # Assert
                self.assertDictEqual(result, expected)
                self.assertEqual(build.aci_vrf, "uni/tn-Ciscolive/ctx-vrf-01")

    def test_sriov_macvlan_br_only_diff_ns(self):
        pods = [
            client.V1Pod(
                status=client.V1PodStatus(
                    host_ip="192.168.1.2", pod_ip="192.158.1.4"
                ),
                metadata=client.V1ObjectMeta(
                    name="sriov-pod", namespace="sriov", labels={"guest": "frontend"}, annotations={"k8s.v1.cni.cncf.io/network-status": json.dumps([{"ips": ["192.158.1.5"], "mac": "02:a0:e8:00:00:0a", "name": "sriov-net1", "interface": "ens1f2v12"}])}
                ),
                spec=client.V1PodSpec(
                    node_name="1234abc", containers=[]
                )
            ),
            client.V1Pod(
                status=client.V1PodStatus(
                    host_ip="192.168.1.2", pod_ip="192.158.1.8"
                ),
                metadata=client.V1ObjectMeta(
                    name="bridge-pod", namespace="bridge", labels={"guest": "frontend"}, annotations={"k8s.v1.cni.cncf.io/network-status": json.dumps([{"ips": ["192.158.1.8"], "mac": "02:a0:e8:00:00:0a", "name": "br-net1", "interface": "br-net1"}])}
                ),
                spec=client.V1PodSpec(
                    node_name="1234abc", containers=[]
                )
            ),
            client.V1Pod(
                status=client.V1PodStatus(
                    host_ip="192.168.1.2", pod_ip="192.158.1.6"
                ),
                metadata=client.V1ObjectMeta(
                    name="macvlan-pod", namespace="macvlan", labels={"guest": "frontend"}, annotations={"k8s.v1.cni.cncf.io/network-status": json.dumps([{"ips": ["192.158.1.7"], "mac": "02:a0:e8:00:00:0a", "name": "macvlan-net1", "interface": "net1"}])}
                ),
                spec=client.V1PodSpec(
                    node_name="1234abc", containers=[]
                )
            )
        ]

        with patch('kubernetes.client.CoreV1Api.list_pod_for_all_namespaces', MagicMock(return_value=client.V1PodList(api_version="1", items=pods))):
            with patch('kubernetes.client.CustomObjectsApi.list_namespaced_custom_object', MagicMock(return_value=nfna)):
                expected = {'nodes': {'1234abc': {'bgp_peers': {'leaf-204': {'prefix_count': 2}},
                                                  'labels': {'app': 'redis'},
                                                  'mac': 'MOCKMO1C',
                                                  'neighbours': {'esxi4.cam.ciscolabs.com': {'Description': 'VMware '
                                                                                             'version '
                                                                                             '123',
                                                                                             'switches': {'leaf-204': {'vmxnic1-eth1/1'}}}},
                                                  'node_ip': '192.168.1.2',
                                                  'node_leaf_all_iface_conn': [{'node_iface': 'PF-ens1f2',
                                                                                'switch_interface': 'eth1/3',
                                                                                'switch_name': 'leaf-101'},
                                                                               {'node_iface': 'bond1',
                                                                                'switch_interface': 'eth1/37',
                                                                                'switch_name': 'leaf-101'},
                                                                               {'node_iface': 'br1',
                                                                                'switch_interface': 'eth1/38',
                                                                                'switch_name': 'leaf-101'}],
                                                  'node_leaf_br_iface_conn': [{'node_iface': 'br1',
                                                                               'switch_interface': 'eth1/38',
                                                                               'switch_name': 'leaf-101'}],
                                                  'node_leaf_macvlan_iface_conn': [{'node_iface': 'bond1',
                                                                                    'switch_interface': 'eth1/37',
                                                                                    'switch_name': 'leaf-101'}],
                                                  'node_leaf_sriov_iface_conn': [{'node_iface': 'PF-ens1f2',
                                                                                  'switch_interface': 'eth1/3',
                                                                                  'switch_name': 'leaf-101'}],
                                                  'node_pod_br_iface_conn': [{'ips': '192.158.1.8',
                                                                              'mac': '02:a0:e8:00:00:0a',
                                                                              'node_iface': 'br1',
                                                                              'node_network': 'bridge-net1',
                                                                              'pod_iface': 'br-net1',
                                                                              'pod_name': 'bridge-pod',
                                                                              'vlan': '[3456]'}],
                                                  'node_pod_macvlan_iface_conn': [{'node_iface': 'net1',
                                                                                   'node_network': 'macvlan-net1',
                                                                                   'pod_iface': 'net1',
                                                                                   'pod_name': 'macvlan-pod',
                                                                                   'vlan': '[3456]'}],
                                                  'node_pod_sriov_iface_conn': [{'node_iface': 'VF-ens1f2v12',
                                                                                 'node_network': 'sriov-net1',
                                                                                 'pod_iface': 'ens1f2v12',
                                                                                 'pod_name': 'sriov-pod',
                                                                                 'vlan': '[3456]'}],
                                                  'pods': {'bridge-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                          '["192.158.1.8"], '
                                                                                          '"mac": '
                                                                                          '"02:a0:e8:00:00:0a", '
                                                                                          '"name": '
                                                                                          '"br-net1", '
                                                                                          '"interface": '
                                                                                          '"br-net1"}]'},
                                                                          'ip': '192.158.1.8',
                                                                          'labels': {'guest': 'frontend'},
                                                                          'ns': 'bridge',
                                                                          'other_ifaces': {'br-net1': 'br-net1'},
                                                                          'primary_iface': ''},
                                                           'macvlan-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                           '["192.158.1.7"], '
                                                                                           '"mac": '
                                                                                           '"02:a0:e8:00:00:0a", '
                                                                                           '"name": '
                                                                                           '"macvlan-net1", '
                                                                                           '"interface": '
                                                                                           '"net1"}]'},
                                                                           'ip': '192.158.1.6',
                                                                           'labels': {'guest': 'frontend'},
                                                                           'ns': 'macvlan',
                                                                           'other_ifaces': {'macvlan-net1': 'net1'},
                                                                           'primary_iface': ''},
                                                           'sriov-pod': {'annotations': {'k8s.v1.cni.cncf.io/network-status': '[{"ips": '
                                                                                         '["192.158.1.5"], '
                                                                                         '"mac": '
                                                                                         '"02:a0:e8:00:00:0a", '
                                                                                         '"name": '
                                                                                         '"sriov-net1", '
                                                                                         '"interface": '
                                                                                         '"ens1f2v12"}]'},
                                                                         'ip': '192.158.1.4',
                                                                         'labels': {'guest': 'frontend'},
                                                                         'ns': 'sriov',
                                                                         'other_ifaces': {'sriov-net1': 'ens1f2v12'},
                                                                         'primary_iface': ''}},
                                                  'vmis': {'cp-1': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.35',
                                                                                    'ipAddresses': ['192.168.2.35'],
                                                                                    'mac': '02:a0:e8:00:00:0a',
                                                                                    'name': 'nic-gray-guineafowl-45',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'},
                                                           'cp-2': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.36',
                                                                                    'ipAddresses': ['192.168.2.36'],
                                                                                    'mac': '02:a0:e8:00:00:0c',
                                                                                    'name': 'node',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'}}}},
                            'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                                   'external_i_ps': ['192.168.5.1'],
                                                   'labels': {'app': 'guestbook'},
                                                   'load_balancer_ip': '192.168.5.2',
                                                   'name': 'example service',
                                                   'ns': 'appx'}]}}

                build = VkaciBuilTopology(
                    VkaciEnvVariables(self.vars), ApicMethodsMock())
                # Act
                result = build.update()
                # Assert
                self.assertDictEqual(result, expected)
                self.assertEqual(build.aci_vrf, "uni/tn-Ciscolive/ctx-vrf-01")

    def test_sriov_without_pod(self):
        pods = [
            client.V1Pod(
                status=client.V1PodStatus(
                    host_ip="192.168.1.2", pod_ip="192.158.1.3"
                ),
                metadata=client.V1ObjectMeta(
                    name="dateformat", namespace="dockerimage", labels={"guest": "frontend"}
                ),
                spec=client.V1PodSpec(
                    node_name="1234abc", containers=[]
                )
            )
        ]
        nfna = {
            "items": [{
                "spec": {
                    "aciTopology": {
                        "ens1f2":
                            {
                                "fabricLink": [
                                    "abc/def/node-101/[eth1/3]"
                                ]
                            }
                    },
                    "nodeName": "1234abc",
                    "encapVlan": {
                        "encapRef": {
                            "key": "",
                            "nadVlanMap": ""
                        },
                        "mode": "Trunk",
                        "vlanList": "[3706]"
                    },
                    "networkRef": {
                        "name": "sriov-net1"
                    },
                    "primaryCni": "sriov"
                },
                "metadata": {
                    "name": "sriov"
                }
            }]
        }

        with patch('kubernetes.client.CoreV1Api.list_pod_for_all_namespaces', MagicMock(return_value=client.V1PodList(api_version="1", items=pods))):
            with patch('kubernetes.client.CustomObjectsApi.list_namespaced_custom_object', MagicMock(return_value=nfna)):
                expected = {'nodes': {'1234abc': {'bgp_peers': {'leaf-204': {'prefix_count': 2}},
                                                  'labels': {'app': 'redis'},
                                                  'mac': 'MOCKMO1C',
                                                  'neighbours': {'esxi4.cam.ciscolabs.com': {'Description': 'VMware '
                                                                                             'version '
                                                                                             '123',
                                                                                             'switches': {'leaf-204': {'vmxnic1-eth1/1'}}}},
                                                  'node_ip': '192.168.1.2',
                                                  'node_leaf_all_iface_conn': [],
                                                  'node_leaf_br_iface_conn': [],
                                                  'node_leaf_macvlan_iface_conn': [],
                                                  'node_leaf_sriov_iface_conn': [],
                                                  'node_pod_br_iface_conn': [],
                                                  'node_pod_macvlan_iface_conn': [],
                                                  'node_pod_sriov_iface_conn': [],
                                                  'pods': {'dateformat': {'annotations': {},
                                                                          'ip': '192.158.1.3',
                                                                          'labels': {'guest': 'frontend'},
                                                                          'ns': 'dockerimage',
                                                                          'other_ifaces': {},
                                                                          'primary_iface': ''}},
                                                  'vmis': {'cp-1': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.35',
                                                                                    'ipAddresses': ['192.168.2.35'],
                                                                                    'mac': '02:a0:e8:00:00:0a',
                                                                                    'name': 'nic-gray-guineafowl-45',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'},
                                                           'cp-2': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.36',
                                                                                    'ipAddresses': ['192.168.2.36'],
                                                                                    'mac': '02:a0:e8:00:00:0c',
                                                                                    'name': 'node',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'}}}},
                            'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                                   'external_i_ps': ['192.168.5.1'],
                                                   'labels': {'app': 'guestbook'},
                                                   'load_balancer_ip': '192.168.5.2',
                                                   'name': 'example service',
                                                   'ns': 'appx'}]}}

                build = VkaciBuilTopology(
                    VkaciEnvVariables(self.vars), ApicMethodsMock())
                # Act
                result = build.update()
                # Assert
                self.assertDictEqual(result, expected)
                self.assertEqual(build.aci_vrf, "uni/tn-Ciscolive/ctx-vrf-01")

    def test_macvlan_without_pod(self):
        pods = [
            client.V1Pod(
                status=client.V1PodStatus(
                    host_ip="192.168.1.2", pod_ip="192.158.1.3"
                ),
                metadata=client.V1ObjectMeta(
                    name="dateformat", namespace="dockerimage", labels={"guest": "frontend"}
                ),
                spec=client.V1PodSpec(
                    node_name="1234abc", containers=[]
                )
            )
        ]
        nfna = {
            "items": [{
                "spec": {
                    "aciTopology": {
                        "bond1":
                            {
                                "fabricLink": [
                                    "abc/def/node-101/[eth1/37]"
                                ]
                            }
                    },
                    "nodeName": "1234abc",
                    "encapVlan": {
                        "encapRef": {
                            "key": "",
                            "nadVlanMap": ""
                        },
                        "mode": "Trunk",
                        "vlanList": "[3708]"
                    },
                    "networkRef": {
                        "name": "macvlan-net1"
                    },
                    "primaryCni": "macvlan"
                },
                "metadata": {
                    "name": "macvlan"
                }
            }]
        }

        with patch('kubernetes.client.CoreV1Api.list_pod_for_all_namespaces', MagicMock(return_value=client.V1PodList(api_version="1", items=pods))):
            with patch('kubernetes.client.CustomObjectsApi.list_namespaced_custom_object', MagicMock(return_value=nfna)):
                expected = {'nodes': {'1234abc': {'bgp_peers': {'leaf-204': {'prefix_count': 2}},
                                                  'labels': {'app': 'redis'},
                                                  'mac': 'MOCKMO1C',
                                                  'neighbours': {'esxi4.cam.ciscolabs.com': {'Description': 'VMware '
                                                                                             'version '
                                                                                             '123',
                                                                                             'switches': {'leaf-204': {'vmxnic1-eth1/1'}}}},
                                                  'node_ip': '192.168.1.2',
                                                  'node_leaf_all_iface_conn': [],
                                                  'node_leaf_br_iface_conn': [],
                                                  'node_leaf_macvlan_iface_conn': [],
                                                  'node_leaf_sriov_iface_conn': [],
                                                  'node_pod_br_iface_conn': [],
                                                  'node_pod_macvlan_iface_conn': [],
                                                  'node_pod_sriov_iface_conn': [],
                                                  'pods': {'dateformat': {'annotations': {},
                                                                          'ip': '192.158.1.3',
                                                                          'labels': {'guest': 'frontend'},
                                                                          'ns': 'dockerimage',
                                                                          'other_ifaces': {},
                                                                          'primary_iface': ''}},
                                                  'vmis': {'cp-1': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.35',
                                                                                    'ipAddresses': ['192.168.2.35'],
                                                                                    'mac': '02:a0:e8:00:00:0a',
                                                                                    'name': 'nic-gray-guineafowl-45',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'},
                                                           'cp-2': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.36',
                                                                                    'ipAddresses': ['192.168.2.36'],
                                                                                    'mac': '02:a0:e8:00:00:0c',
                                                                                    'name': 'node',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'}}}},
                            'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                                   'external_i_ps': ['192.168.5.1'],
                                                   'labels': {'app': 'guestbook'},
                                                   'load_balancer_ip': '192.168.5.2',
                                                   'name': 'example service',
                                                   'ns': 'appx'}]}}

                build = VkaciBuilTopology(
                    VkaciEnvVariables(self.vars), ApicMethodsMock())
                # Act
                result = build.update()
                # Assert
                self.assertDictEqual(result, expected)
                self.assertEqual(build.aci_vrf, "uni/tn-Ciscolive/ctx-vrf-01")

    def test_br_without_pod(self):
        pods = [
            client.V1Pod(
                status=client.V1PodStatus(
                    host_ip="192.168.1.2", pod_ip="192.158.1.3"
                ),
                metadata=client.V1ObjectMeta(
                    name="dateformat", namespace="dockerimage", labels={"guest": "frontend"}
                ),
                spec=client.V1PodSpec(
                    node_name="1234abc", containers=[]
                )
            )
        ]
        nfna = {
            "items": [{
                "spec": {
                    "aciTopology": {
                        "br1":
                            {
                                "fabricLink": [
                                    "abc/def/node-101/[eth1/38]"
                                ]
                            }
                    },
                    "nodeName": "1234abc",
                    "encapVlan": {
                        "encapRef": {
                            "key": "",
                            "nadVlanMap": ""
                        },
                        "mode": "Trunk",
                        "vlanList": "[3708]"
                    },
                    "networkRef": {
                        "name": "bridge-net1"
                    },
                    "primaryCni": "bridge"
                },
                "metadata": {
                    "name": "bridge"
                }
            }]
        }

        with patch('kubernetes.client.CoreV1Api.list_pod_for_all_namespaces', MagicMock(return_value=client.V1PodList(api_version="1", items=pods))):
            with patch('kubernetes.client.CustomObjectsApi.list_namespaced_custom_object', MagicMock(return_value=nfna)):
                expected = {'nodes': {'1234abc': {'bgp_peers': {'leaf-204': {'prefix_count': 2}},
                                                  'labels': {'app': 'redis'},
                                                  'mac': 'MOCKMO1C',
                                                  'neighbours': {'esxi4.cam.ciscolabs.com': {'Description': 'VMware '
                                                                                             'version '
                                                                                             '123',
                                                                                             'switches': {'leaf-204': {'vmxnic1-eth1/1'}}}},
                                                  'node_ip': '192.168.1.2',
                                                  'node_leaf_all_iface_conn': [],
                                                  'node_leaf_br_iface_conn': [],
                                                  'node_leaf_macvlan_iface_conn': [],
                                                  'node_leaf_sriov_iface_conn': [],
                                                  'node_pod_br_iface_conn': [],
                                                  'node_pod_macvlan_iface_conn': [],
                                                  'node_pod_sriov_iface_conn': [],
                                                  'pods': {'dateformat': {'annotations': {},
                                                                          'ip': '192.158.1.3',
                                                                          'labels': {'guest': 'frontend'},
                                                                          'ns': 'dockerimage',
                                                                          'other_ifaces': {},
                                                                          'primary_iface': ''}},
                                                  'vmis': {'cp-1': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.35',
                                                                                    'ipAddresses': ['192.168.2.35'],
                                                                                    'mac': '02:a0:e8:00:00:0a',
                                                                                    'name': 'nic-gray-guineafowl-45',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'},
                                                           'cp-2': {'interfaces': [{'infoSource': 'domain, '
                                                                                    'guest-agent, '
                                                                                    'multus-status',
                                                                                    'interfaceName': 'enp1s0',
                                                                                    'ipAddress': '192.168.2.36',
                                                                                    'ipAddresses': ['192.168.2.36'],
                                                                                    'mac': '02:a0:e8:00:00:0c',
                                                                                    'name': 'node',
                                                                                    'queueCount': 1}],
                                                                    'ns': 'ocp-cilium-c1'}}}},
                            'services': {'appx': [{'cluster_ip': '192.168.25.5',
                                                   'external_i_ps': ['192.168.5.1'],
                                                   'labels': {'app': 'guestbook'},
                                                   'load_balancer_ip': '192.168.5.2',
                                                   'name': 'example service',
                                                   'ns': 'appx'}]}}

                build = VkaciBuilTopology(
                    VkaciEnvVariables(self.vars), ApicMethodsMock())
                # Act
                result = build.update()
                # Assert
                self.assertDictEqual(result, expected)
                self.assertEqual(build.aci_vrf, "uni/tn-Ciscolive/ctx-vrf-01")


if __name__ == '__main__':
    unittest.main()
