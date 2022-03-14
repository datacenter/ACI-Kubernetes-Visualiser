# Calico ACI Integration Visibility

This Utility container will help locate the end to end connectivity for a POD.
You pass the POD name and you get infos on:

- The K8s node where the pod is running on.
- To which interface profile is the Node IP learned on ACI
- The LLDP neighbors discovered from the Physical interfaces member of the interface profile

## Installation - In Cluster

vkaci needs to connect to the APIC via certificate based authetication. It is expected that your APIC are pre-configured for certificate based authentication.

- edit the vkaci.yaml file and set the environment variables to match your infrastructure.
  - MODE: Set the app to run in `CLUSTER` mode (deployed on the cluster that is monitoring) or in `LOCAL` mode, useful for development. 
  - APIC_IPS:      Comma separated list of your APIC IPs
  - CERT_USER:     Name of the user
  - CERT_NAME:     Name of the certificate configured in the APIC
  - TENANT:        Tenant where the cluster VRF is deployed
  - VRF:           Name of the VRF used by the cluster
  - NEO4J_URL:     URL to the neo4j database. eg. neo4j://my-neo4j-release-neo4j:7687, your vkaci pod needs to be able to resolve this name to the K8s Service IP
  - NEO4J_BROWSER_URL: URL to the neo4j database service. Eg. neo4j://my-neo4j-release-neo4j:7687, your browser needs to be able to resolve this name to the K8s Service IP
  - NEO4J_USER:    Add neo4j username
  - NEO4J_PASSWORD: Add neo4j password

- aci-user-cert: Replace the user.key content with your certificate key.
- apply the `list-permission.yaml` this will allow the `ServiceAccount` `default` to list pod.
- apply the `vkaci.yaml` this spin up the container that will run our tasks

## Installation - Off Cluster/for development

The same environemntvariables can be set to run the application locally. In addition the following environment variable needs to be set:

- `KEY_PATH`: to define the location of the key used for APIC authentication.
- `KUBE_CONFIG`: to define the location of the kubeconfig file.

For example to run the application you can

```bash
export MODE=LOCAL APIC_IPS="10.67.185.102,10.67.185.42,10.67.185.41" CERT_NAME=ansible.crt CERT_USER=ansible TENANT=calico2 VRF=vrf KEY_PATH=/home/cisco/Coding/ansible.key KUBE_CONFIG=/home/cisco/Coding/vkaci/calico-2.config NEO4J_URL=neo4j://my-neo4j-release-neo4j:7687 NEO4J_BROWSER_URL=neo4j://my-neo4j-release-neo4j:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=me-change
```

- Execute the init.py script to load the ACI metadata used by pyaci (this is needed only the 1st time)
- Execute the visibility_ui.py
