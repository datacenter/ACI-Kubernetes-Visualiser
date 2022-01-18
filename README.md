# Calico ACI Integration Visibility

This Utility container will help locate the end to end connectivity for a POD.
You pass the POD name and you get infos on:

- The K8s node where the pod is running on.
- To which interface profile is the Node IP learned on ACI
- The LLDP neighbors discovered from the Physical interfaces member of the interface profile

## Installation - In Cluster

vkaci needs to connect to the APIC via certificate based authetication. It is expected that your APIC are pre-configured for certificate based authentication.

- edit the vkaci.yaml file and set the environment variables to match your infrastructure.
  - MODE: Set the app to run in "CLUSTER" mode (deployed on the cluster that is monitoring) or in LOCAL mode, useful for development. 
  - APIC_IPS: Comma separated list of your APIC IPs 
  - CERT_USER: Name of the user
  - CERT_NAME: Name of the certificate configured in the APIC.
  - TENANT: Tenant where the cluster L3OUT is deployed
  - VRF: Name of the VRF where the cluster is deployed
  - aci-user-cert: Replace the user.key content with your certificate key.
- apply the `list-permission.yaml` this will allow the `ServiceAccount` `default` to list pod.
- apply the `vkaci.yaml` this spin up the container that will run our tasks

## Installation - Off Cluster/for development

The same environemntvariables can be set to run the application locally. In addition the following additiona environment variable needs to be set:

- `KEY_PATH`: to define the location of the key used for APIC authentication.
- `KUBE_CONFIG`: to define the location of the kubeconfig file.

For example tu run the application you can

```bash
export MODE=LOCAL APIC_IPS="10.67.185.102,10.67.185.42,10.67.185.41" CERT_NAME=ansible.crt CERT_USER=ansible TENANT=calico2 VRF=vrf KEY_PATH=/home/cisco/Coding/ansible.key KUBE_CONFIG=/home/cisco/Coding/vkaci/calico-2.config
python3 init.py

```


- Execute the init.py script to load the ACI metadata used by pyaci (this is needed only the 1st time)
- Execute the visibility_ui.py

## How to use

Once the pod is running you can just run this:

- `kubectl exec -it vkaci -- visibility.py <pod_name>`

## Example

```bash
  kubectl exec -it vkaci -- visibility.py vkaci
  Looking for pod vkaci with IP 10.1.203.0 on node 192.168.2.8
  The K8s Node is physically connected to: topology/pod-1/protpaths-203-204/pathep-[esxi4_vpc_vmnic2-3_PolGrp]
  LLDP Infos:
    topology/pod-1/node-203 eth1/1
      esxi4.cam.ciscolabs.com
    topology/pod-1/node-204 eth1/1
      esxi4.cam.ciscolabs.com
  BGP Peer:
    node-201
    node-202
```

## Tip

Make an alias, just use set the namespace to what you need.

```bash
 alias vkaci='kubectl -n default exec -it vkaci -- visibility.py'
 ```

 now you can simply do `vkaci <pod_name>`
