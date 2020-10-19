#!/usr/bin/env python3

import time

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib import Path

from asynciojobs import Job, Scheduler, PrintJob

from apssh import SshNode, SshJob, Run
from apssh import RunString, RunScript, TimeColonFormatter

# make sure to pip install r2lab
from r2lab import ListOfChoices, ListOfChoicesNullReset, find_local_embedded_script

# include the set of utility scripts that are included by the r2lab kit
INCLUDES = [find_local_embedded_script(x) for x in (
    "r2labutils.sh", "nodes.sh", "mosaic-common.sh",
)]

##########
default_gateway  = 'faraday.inria.fr'
gateway_username  = 'inria_mosaic'
master_image = "kube5g-master" # this image is a k8base with mosaic5G snap installed
worker_image = "k8base"
verbose_mode = True
dry_run = False
disag_cn = False
node_master = 1
node_enb = 23
node_ids = [1,2,3,23]
phones = [1,]

##########

def fitname(node_id):
    """                                                                      
    Return a valid hostname from a node number - either str or int           
    """
    int_id = int(node_id)
    return "fit{:02d}".format(int_id)

def run(slicename=gateway_username, phones=phones, 
        node_ids=node_ids, node_master=node_master, node_enb=node_enb, 
        disag_cn=disag_cn, verbose_mode=verbose_mode, dry_run=dry_run):
    """
    Install K8 on R2lab

    Arguments:
        slicename: the Unix login name (slice name) to enter the gateway
        phones: list of indices of phones to use
        node_ids: a list of node ids to run the scenario on; strings or ints 
                  are OK;
        node_master: the master node id, must be part of selected nodes
        node_enb: the node id for the enb, whcih is connected to usrp
        disag_cn: Boolean; True for the disaggregated CN scenario. False for all-in-one CN.
    """

    if node_master not in node_ids:
        print(f"master node {node_master} must be part of selected fit nodes {node_ids}")
        exit(1)
    if node_enb not in node_ids:
        print(f"eNB worker node {node_enb} must be part of selected fit nodes {node_ids}")
        exit(1)

    worker_ids = node_ids[:]
    worker_ids.remove(node_master)

    faraday = SshNode(hostname=default_gateway, username=slicename,
                      verbose=verbose_mode,
                      formatter=TimeColonFormatter())

    master = SshNode(gateway=faraday, hostname=fitname(node_master), 
                     username="root",
                     verbose=verbose_mode,
                     formatter=TimeColonFormatter())

    node_index = {
        id: SshNode(gateway=faraday, hostname=fitname(id), 
                    username="root",formatter=TimeColonFormatter(), 
                    verbose=verbose_mode)
        for id in node_ids
    }

    worker_index = dict(node_index)
    del worker_index[node_master]
    fit_master = fitname(node_master)
    fit_enb = fitname(node_enb)
    
    # the global scheduler                                                   
    scheduler = Scheduler(verbose=verbose_mode)


    ##########
    check_lease = SshJob(
        scheduler=scheduler,
        node = faraday,
        critical = True,
        verbose=verbose_mode,
        command = Run("rhubarbe leases --check"),
    )

    green_light = [
        SshJob(
            scheduler=scheduler,
            required=check_lease,
            node=faraday,
            critical=True,
            verbose=verbose_mode,
            label = f"Load image {master_image} on master {fit_master}",
            commands=[
                Run(f"rhubarbe load -i {master_image} {node_master}"),
                Run(f"rhubarbe wait {node_master}"),
            ]
        ),
        SshJob(
            scheduler=scheduler,
            required=check_lease,
            node=faraday,
            critical=True,
            verbose=verbose_mode,
            label = f"Load image {worker_image} on worker nodes",
            commands=[
                Run(f"rhubarbe usrpoff {node_enb}"), # if usrp is on, load could be problematic...
                Run("rhubarbe", "load", "-i", worker_image, *worker_ids),
                Run("rhubarbe", "wait", *worker_ids),
                Run(f"rhubarbe usrpon {node_enb}"), # ensure a reset of the USRP on the enB node
            ],
        ),
    ]
            

    ##########
    # Initialize k8 on the master node
    init_master = SshJob(
        scheduler=scheduler,
        required=green_light,
        node=master,
        critical=True,
        verbose=verbose_mode,
        label = f"Install and launch k8 on the master {node_master}", 
        commands = [
            Run("sudo swapoff -a"),
            Run("hostnamectl set-hostname master-node"),
            Run("kubeadm init --pod-network-cidr=10.244.0.0/16 > /tmp/join_msg.txt"),
            Run("tail -2 /tmp/join_msg.txt > /tmp/join_msg"),
            Run("mkdir -p $HOME/.kube"),
            Run("cp -i /etc/kubernetes/admin.conf $HOME/.kube/config"),
            Run("chown $(id -u):$(id -g) $HOME/.kube/config"),
            Run("kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml"),
            Run("kubectl get pods --all-namespaces"),
        ],
    )
    init_workers = [
        SshJob(
            scheduler=scheduler,
            required=init_master,
            node=node,
            critical=True,
            verbose=verbose_mode,
            label=f"Init k8 on fit node {id} and join the cluster",
            commands = [
                Run("sudo swapoff -a"),
                Run(f"scp -o 'StrictHostKeyChecking no' {fit_master}:/tmp/join_msg /tmp/join_msg"),
                Run("chmod a+x /tmp/join_msg"),
                Run("/tmp/join_msg"),
            ],
        ) for id, node in worker_index.items()
    ]
    
    # wait 1mn for K8 nodes setup
    wait_k8nodes_ready = PrintJob(
        "Let k8 set up",
        scheduler=scheduler,
        required=init_master,
        sleep=60,
        label="settling k8 nodes"
    )


    init_kube5g = SshJob(
        scheduler=scheduler,
        required = wait_k8nodes_ready,
        node = master,
        verbose=verbose_mode,
        label = f"Add oai:ran label to oai-ran pod on {node_enb} and start 5GOperator pod",
        commands = [
            Run("kubectl get nodes"),
            # add label to the eNB node to help k8s scheduler selects the right fit node
            Run(f"kubectl label nodes fit{node_enb} oai=ran"), 
            Run("kubectl get nodes -Loai"),
            # apply the Mosaic5g CRD
            Run("cd /root/mosaic5g/kube5g/openshift/m5g-operator; ./m5goperator.sh -n"),
            # start the 5GOperator pod
            Run("cd /root/mosaic5g/kube5g/openshift/m5g-operator; ./m5goperator.sh container start"), 
            Run("kubectl get pods"),
        ],
    )

    # wait 20s for K8 5G Operator setup
    wait_k8_5GOp_ready = PrintJob(
        "Let 5G Operator set up",
        scheduler=scheduler,
        required=init_kube5g,
        sleep=20,
        label="settling 5G Operator pod"
    )

    if disag_cn:
        cn_type="disaggregated-cn"
        setup_time = 120
    else:
        cn_type="all-in-one"
        setup_time = 60
        
    run_kube5g = SshJob(
        scheduler=scheduler,
        required = wait_k8_5GOp_ready,
        node = master,
        verbose=verbose_mode,
        label = f"deploy CN {cn_type} then eNB pods",
        commands = [
            Run("kubectl get nodes -Loai"),
            Run(f"cd /root/mosaic5g/kube5g/openshift/m5g-operator; ./m5goperator.sh deploy {cn_type}"),
            Run("kubectl get pods"),
        ],
    )
    
    # Coffee Break -- wait 1 or 2mn for K8 5G pods setup
    wait_k8_5Gpods_ready = PrintJob(
        "Let all 5G pods set up",
        scheduler=scheduler,
        required=run_kube5g,
        sleep=setup_time,
        label="settling all 5G pods"
    )

    check_kube5g = SshJob(
        scheduler=scheduler,
        required = wait_k8_5Gpods_ready,
        node = master,
        verbose=verbose_mode,
        label = "Check which pods are deployed", 
        commands = [
            Run("kubectl get nodes -Loai"),
            Run("kubectl get pods"),
        ],
    )

    ########## Test phone(s) connectivity

    sleeps = [40, 60]
    phone_msgs = [f"wait for {sleep}s for eNB to start up before waking up phone{id}"
                  for sleep, id in zip(sleeps, phones)]
    wait_commands = [f"echo {msg}; sleep {sleep}"
                     for msg, sleep in zip(phone_msgs, sleeps)]

    job_start_phones = [
        SshJob(
            node=faraday,
            commands=[
                Run(wait_command),
                RunScript(find_local_embedded_script("faraday.sh"), f"macphone{id}",
                          "r2lab-embedded/shell/macphone.sh", "phone-on",
                          includes=INCLUDES),
                RunScript(find_local_embedded_script("faraday.sh"), f"macphone{id}",
                          "r2lab-embedded/shell/macphone.sh", "phone-start-app",
                          includes=INCLUDES),
            ],
            label=f"turn off airplane mode on phone {id}",
            required=check_kube5g,
            scheduler=scheduler)
        for id, wait_command in zip(phones, wait_commands)]
    

    ##########
    # Update the .dot and .png file for illustration purposes
    scheduler.check_cycles()
    name = "deploy-k8"
    print(10*'*', 'See main scheduler in',
          scheduler.export_as_pngfile(name))
    
    # orchestration scheduler jobs
    if verbose_mode:
        scheduler.list()

    if dry_run:
        return True

    if verbose_mode:
        input('OK ? - press control C to abort ? ')

    if not scheduler.orchestrate():
        print(f"RUN KO : {scheduler.why()}")
        scheduler.debrief()
        return False
    print("RUN OK")
    print(80*'*')  

##########                                                    

def main():
    """    
    Command-line frontend - offers primarily all options to kube5g scenario

    """

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("-s", "--slicename", default=gateway_username,
                        help="specify an alternate slicename, default={}".format(gateway_username))
    parser.add_argument("-v", "--verbose-mode", default=False, 
                        action='store_true', dest='verbose_mode',
                        help="run script in verbose mode")
    parser.add_argument("-D", "--disag-cn", default=False, 
                        action='store_true',
                        help="if set, Deploy the Disaggragated CN scenario, else deploy the all-in-one CN")
    parser.add_argument("-N", "--node-id", dest='node_ids',
                        default=node_ids, 
                        choices=[str(x+1) for x in range(37)],
                        action=ListOfChoices,
                        help="specify as many node ids as you want, including master and eNB nodes")
    parser.add_argument("-M", "--node-master", dest='node_master',
                        default=node_master, 
                        help="specify master id node")
    parser.add_argument(
	"-R", "--ran", default=node_enb, dest='node_enb',
        help="""specify the id of the node that runs the eNodeB,
which requires a USRP b210 and 'duplexer for eNodeB""")
    parser.add_argument(
        "-p", "--phones", dest='phones',
        action=ListOfChoicesNullReset, type=int, choices=(1, 2, 0),
        default=[1],
        help='Commercial phones to use; use -p 0 to choose no phone')

    parser.add_argument(
        "-n", "--dry-run", action='store_true', default=False, dest='dry_run',
        help="run script in dry mode")


    args = parser.parse_args()

    # we pass to run exactly the set of arguments known to parser
    # build a dictionary with all the values in the args
    kwds = args.__dict__.copy()

    # actually run it
    if(args.disag_cn):
        print("*** Run the Disaggragated CN Scenario *** ")
    else:
        print("*** Run the all-in-one CN Scenario *** ")
    print("With the following fit nodes:")
    for i in args.node_ids:
        if i == args.node_master:
            role = "Master node"
        elif i == args.node_enb:
            role = "Worker eNB node"
        else:
            role = "Worker node"
        nodename = fitname(i)
        print(f"\t{nodename}: {role}")
    if args.phones:
        for phone in args.phones:
            print(f"Using phone{phone}")
    else:
        print("No phone involved")
        
    now = time.strftime("%H:%M:%S")
    print(f"Experiment STARTING at {now}")
    if not run(**kwds):
        print("exiting")
        return    
    


##########
if __name__ == '__main__':
    # return something useful to your OS
    exit(0 if main() else 1)
