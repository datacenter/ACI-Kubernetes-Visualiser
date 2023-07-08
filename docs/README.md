# Visualising Kubernetes ACI

## [CISCO VKACI](https://github.com/datacenter/ACI-Kubernetes-Visualiser)

## Introduction

Visualisation of Kubernetes using ACI (Vkaci) is an open-source tool that generates a cluster topology and provides a visual representation, using neo4j graph database by accessing ACI and K8s APIs. This tool lets you quickly build visualisations of K8s and ACI end to end topologies. The objective of this documentation is to outline the creation, design, and installation of Vkaci to help users view their topologies.

Cisco Application Centric Infrastructure (Cisco ACI) is a component of Cisco's purpose-based networking design, which enables data centre agility and resiliency. It creates a policy that captures higher-level business and user intent and turns it into the network constructs needed to dynamically supply network, security, and infrastructure services.

The Kubernetes API allows you to query and manipulate the state of Kubernetes API objects (For example: Pods, Namespaces, ConfigMaps, and Events).

## Licensing Requirements

### Please note

***Fundamental Requirement***

GPL 3 is a strong copyleft license, meaning that any copy or modification of the original code must also be released under the GPL v3. In other words, you can take the GPL 3’d code, add to it or make major changes, then distribute your version. However, your version is subject to the same license requirements, meaning that it must be under GPL v3 as well — anyone can see your modified code and install it for their own purposes.

***Developers Requirement***

Research indicates that open source software contributors are motivated more by a desire to learn and be part of the OSS community than by financial rewards. Hence consider distribution of this code ethically and not for any external companies production or commercial environment. 

## Installing

### Connectivity Requirements in Cluster

Vkaci needs to connect to the APIC (OOB or InBand) via certificate-based authentication. It is expected that your APIC is pre-configured for certificate-based authentication.

### Installation – Helm Chart

A Helm chart for Vkaci has been created to enable simple deployment of the Vkaci app and a dependent Neo4j database along with required services on a K8s cluster.

The helm chart can currently be found in the source code for VKACI and is also available in the following repo:

<https://datacenter.github.io/ACI-Kubernetes-Visualiser>

#### Required Variables:**

| **Name** | **Description** | **Example** |
| --- | --- | --- |
| apicIps | Comma separated list of your APIC Ips. | 10.67.185.102,10.67.185.41,10.67.185.42 |
| apicCertName | Name of the certificate configured in the APIC. | ansible.crt |
| apicKeyData | The base64 encoded string that represents the certificate data. | Steps to generate data below. |
| apicUsername | Name of the APIC certificate user. | ansible |
| vrfTenant | Tenant where the cluster VRF is deployed. | calico |
| vrfName | Name of the VRF used by the cluster. | vrf |

#### Web UI External Connectivity:

To access the webui you have the following options:

- Expose the service as Type `Node Port`: With this config the Client will access the UI service by connecting to any of the nodes on port `nodePort`. Remember to set the `externalTrafficPolicy` to Cluster to ensure regardless of where the vkaci pod runs it can be accessed.
**Reccomended for**: Kube-Router or Calico

```yaml
service:
  externalTrafficPolicy: Cluster
  nodePort: 30000
  type: NodePort
```

- Expose the service as Type `Node Port` and set an `externalIPs`. With this config the Client will access the webui service by using the defined `externalIPs` as entry point into your cluster on port `80`. For this config to work the CNI must advertise via BGP the `externalIPs` and the client needs to be able to route to the `externalIPs`
**Reccomended for**: Kube-Router or Calico

```yaml
service:
  externalTrafficPolicy: Local
  type: NodePort
  externalIPs:
  - 192.168.14.2
```

- Expose the service as Type `LoadBalancer`. With this config the Client will access the neo4j service by using the allocated IP as entry point into your cluster on port `80`. For this config to work the CNI must advertise via BGP the `loadBalancerIP` and the client needs to be able to route to the `loadBalancerIP`.
**Reccomended for**: Cilium

```yaml
service:
  type: LoadBalancer
```

#### neo4j External Connectivity:

Currently the Client (Web Browser) needs to be able to accees the neo4j database directly. This can be acheived by exposing the neo4j service as `NodePort` or `LoadBalancer` type. This is done by configuring the `neo4j-standalone.services.default`.
Based on this configuration the vkaci deployment will be configured to pass, to the browser, the neo4j service IP.

Depending on your network and CNI you might wish to expose the neo4j service in different ways, here are a few options:

- Expose the service as Type `Node Port` set a `port` and Configure the `nodeExternalIP` and to one of your K8s node IP addresses: With this config the Client will access the neo4j service by using the `nodeExternalIP` on port `port` as entry point into your cluster.

**Reccomended for**: Kube-Router or Calico

```yaml
neo4j-standalone:
  services:
    # This setting configure the default neo4j service to 
    default:
      externalTrafficPolicy: Cluster # Needs to be cluster so that if the POD is not running on the specified nodes K8s will still route the traffic to it 
      type: NodePort
      nodeExternalIP: 192.168.11.1
      port: 30002 #This is mandatory and must be specified by the user, ensure you are not picking an already used port!
```

- Expose the service as Type `Node Port` and Configure a single `externalIPs`. With this config the Client will access the neo4j service by using the defined `externalIPs` as entry point into your cluster on port `7687`. For this config to work the CNI must advertise via BGP the `externalIPs` and the client needs to be able to route to the `externalIPs`

**Reccomended for**: Kube-Router or Calico

```yaml
neo4j-standalone:
  services:
    # This setting configure the default neo4j service to 
    default:
      externalTrafficPolicy: Local  # Ensure the Service IP is advertised as a /32 where supported (Calico or Kube-Router)
      type: NodePort
      externalIPs:
        - 192.168.14.1
```

- Expose the service as Type `LoadBalancer` and Configure a `loadBalancerIP`. With this config the Client will access the neo4j service by using the defined `loadBalancerIP` as entry point into your cluster on port `7687`. For this config to work the CNI must advertise via BGP the `loadBalancerIP` and the client needs to be able to route to the `loadBalancerIP`. This config is reccomended for Cilium, you must manually select a `loadBalancerIP`.

**Reccomended for**: Cilium

```yaml
neo4j-standalone:
  services:
    # This setting configure the default neo4j service to 
    default:
      type: LoadBalancer
      loadBalancerIP: 192.168.14.0 #
```

**Example values.yml:**

```yaml
# VKACI APIC Variables
apicIps: "10.67.185.102,10.67.185.41,10.67.185.42"
apicCertName: "ansible.crt"
apicKeyData: "<base64 certificate data>"
apicUsername: "ansible"
vrfTenant: "calico"
vrfName: "vrf"
# Neo4j Variables
neo4j-standalone:
  services:
    default:
      type: NodePort
      externalIPs:
        - 192.168.14.0
```

[Here](values_examples) you can find more exmaples!

To generate the base64 data for apicKeyData from the apic key file use the base64 command. Eg.

```bash
base64 certificate.key
```

## Installation - In Cluster  

Pre Requisites: A working K8s or OpenShift cluster and the ability to expose (to the client web browser) the neo4j database directly

- Add the vkaci chart:

```sh
helm repo add vkaci https://datacenter.github.io/ACI-Kubernetes-Visualiser
```

- Create a value file for your cluster, for example if you have a cluster running Calico and you have defined an External Subnet (advertised via BGP) of 192.168.22.x

```yaml
# VKACI APIC Variables
# All of these will need to be set correctly
apicIps: "<comma separated list of your APIC IP>" # The POD IP needs to have connectivity to ACI
apicUsername: "<User Name>"
apicCertName: "<The name of the certificate for the user>"
vrfTenant: "<Name of the Tenant Where the cluster VRF is located>"
vrfName: "<Name of the Cluster VRF>"
apicKeyData: <base64 certificate data>

service:
  externalTrafficPolicy: Local
  type: NodePort
  externalIPs:
  - 192.168.22.1

# Neo4j Chart Settings
neo4j-standalone:
  services:
    # This setting configure the default neo4j service to
    default:
      externalTrafficPolicy: Local  # Ensure the Service IP is advertised as a /32 where supported (Calico or Kube-Router)
      type: NodePort
      externalIPs:
        - 192.168.22.2
  neo4j:
    password: "" # Set a very good password
```

- Install the helm chart:

```sh
helm install -n vkaci vkaci vkaci/vkaci -f values.yaml
```

- In a few seconds the application should be rechable on the `externalIPs` you have specified
