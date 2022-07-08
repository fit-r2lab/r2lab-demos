

# OAI5G demo on SophiaNode

This script aims to demonstrate how to automate a OAI5G deployment on the SophiaNode cluster
using both fit nodes on R2lab and classical k8s workers.

In this demo, the **oai-demo.py** nepi-ng script is used to prepare 4 fit nodes that will be used to run the following OAI5G functions developed at Eurecom:

* oai-amf (fit01 by default)
* oai-spgwu (fit02 by default)
* oai-gnb (fit03 by default)
* oai-nr-ue (fit04 by default)

This demo does not involve radio transmission as the OAI5G RfSimulator will be used instead.


_Acknowledgments: Support regarding configuration of the OAI5G functions has been provided by
Sagar Arora at Eurecom <sagar.arora@eurecom.fr>._

## References

* [OAI 5G Core Network Deployment using Helm Charts](https://gitlab.eurecom.fr/oai/cn5g/oai-cn5g-fed/-/blob/master/docs/DEPLOY_SA5G_HC.md)
* [R2lab welcome page](https://r2lab.inria.fr/)
* [R2lab run page (requires login)](https://r2lab.inria.fr/run.md)
* [github repo for this page](https://github.com/fit-r2lab/r2lab-demos)


## The different steps...

### Metal provisioning

By default, the nepi-ng **oai-demo.py** script will deploy a specific Kubernetes (k8s) image on
the following R2lab fit nodes: 

* fit01 for oai-amf 
* fit02 for oai-spgwu 
* fit03 for oai-gnb 
* fit09 for oai-nr-ue 

Then the script will configure the nodes to use the data interface used by [k8s Multus](https://github.com/k8snetworkplumbingwg/multus-cni) and it will make all the nodes join the k8s master (sopnode-l1.inria.fr by default).

After that, you can log on the master (ssh oai@sopnode-l1.inria.fr) and deploy the OAI5G pods using the **demo-oai** script (under /home/oai/bin) or by running manually the following commands:

```bash
echo "Wait until all fit nodes are in READY state"
kubectl wait no --for=condition=Ready kubectl wait no --for=condition=Ready fit01 fit02 fit03 fit09

echo "Run the OAI 5G Core pods"
cd /home/oai/oai-cn5g-fed/charts/oai-5g-core/oai-5g-basic

helm --namespace=oai5g spray .

echo "Wait until all 5G Core pods are READY"
kubectl wait pod -noai5g --for=condition=Ready --all

echo "Run the oai-gnb pod on fit03"
echo "cd /home/oai/oai-cn5g-fed/charts/oai-5g-ran"
cd /home/oai/oai-cn5g-fed/charts/oai-5g-ran

helm --namespace=oai5g install oai-gnb oai-gnb/

echo "Wait until the gNB pod is READY"
kubectl wait pod -noai5g --for=condition=Ready --all

echo "Run the oai-nr-ue pod on fit09"

# Retrieve the IP address of the gnb pod and set it in chart /home/oai/oai-cn5g-fed/charts/oai-5g-ran/oai-nr-ue/values.yaml

GNB_POD_NAME=$(kubectl -noai5g get pods -l app.kubernetes.io/name=oai-gnb -o jsonpath="{.items[0].metadata.name}")

GNB_POD_IP=$(kubectl -noai5g get pod $GNB_POD_NAME --template '{{.status.podIP}}')

echo "gNB pod IP is $GNB_POD_IP"

conf_ue_dir="/home/oai/oai-cn5g-fed/charts/oai-5g-ran/oai-nr-ue"
    cat > /tmp/gnb-values.sed <<EOF
s|  rfSimulator:.*|  rfSimulator: "${GNB_POD_IP}"|
EOF

echo "(Over)writing oai-nr-ue chart $conf_ue_dir/values.yaml"
cp $conf_ue_dir/values.yaml /tmp/values-orig.yaml
sed -f /tmp/gnb-values.sed < /tmp/values-orig.yaml > /tmp/values.yaml
cp /tmp/values.yaml $conf_ue_dir/

helm --namespace=oai5g install oai-nr-ue oai-nr-ue/

echo "Wait until the NR-UE pod is READY"
kubectl wait pod -noai5g --for=condition=Ready --all

UE_POD_NAME=$(kubectl -noai5g get pods -l app.kubernetes.io/name=oai-nr-ue -o jsonpath="{.items[0].metadata.name}")

echo "Check UE logs"
kubectl -noai5g logs $UE_POD_NAME -c nr-ue


```
To clean up all pods, you can run the **demo-oai-clean** script (under /home/oai/) or run the following:
```bash 
helm --namespace oai5g ls --short --all | xargs -L1 helm --namespace oai5g delete
```

### Software dependencies

Before you can run the script in this directory, make user to install its dependencies

    pip install -r requirements.txt

