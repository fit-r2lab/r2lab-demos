#!/usr/bin/env python3 -u

import time

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib import Path

# the default for asyncssh is to be rather verbose
import logging
from asyncssh.logging import set_log_level as asyncssh_set_log_level

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
default_slicename  = 'inria_kube5g'

default_disag_cn = False
default_version = 'v2'

default_nodes = [1, 2, 3, 23]
default_node_master = 1
default_node_enb = 23
default_phones = [1,]

default_verbose = False
default_dry_run = False

default_load_images = True
default_master_image = "kube5g-master-v2"
# v2 master image is a k8base with latest kube5g v2 installed (latest core version but not latest ran)
#default_master_image = "k8base" # now kube5g is installed in this script
default_worker_image = "k8base"


##########

def fitname(node_id):
    """
    Return a valid hostname from a node number - either str or int
    """
    int_id = int(node_id)
    return "fit{:02d}".format(int_id)

def run(*, gateway, slicename,
        disag_cn, version, nodes, node_master, node_enb, phones,
        verbose, dry_run,
        load_images, master_image, worker_image):
    """
    Install K8 on R2lab

    Arguments:
        slicename: the Unix login name (slice name) to enter the gateway
        phones: list of indices of phones to use
        nodes: a list of node ids to run the scenario on; strings or ints
                  are OK;
        node_master: the master node id, must be part of selected nodes
        node_enb: the node id for the enb, which is connected to usrp/duplexer
        disag_cn: Boolean; True for the disaggregated CN scenario. False for all-in-one CN.
        version: string "v1" or "v2".
    """

    if version=="none":
        only_kube5g=True
    else:
        only_kube5g=False
    
    if node_master not in nodes:
        print(f"master node {node_master} must be part of selected fit nodes {nodes}")
        exit(1)
    if node_enb not in nodes:
        print(f"eNB worker node {node_enb} must be part of selected fit nodes {nodes}")
        exit(1)

    worker_ids = nodes[:]
    worker_ids.remove(node_master)

    faraday = SshNode(hostname=default_gateway, username=slicename,
                      verbose=verbose,
                      formatter=TimeColonFormatter())

    master = SshNode(gateway=faraday, hostname=fitname(node_master),
                     username="root",
                     verbose=verbose,
                     formatter=TimeColonFormatter())

    node_index = {
        id: SshNode(gateway=faraday, hostname=fitname(id),
                    username="root",formatter=TimeColonFormatter(),
                    verbose=verbose)
        for id in nodes
    }

    worker_index = dict(node_index)
    del worker_index[node_master]
    fit_master = fitname(node_master)
    fit_enb = fitname(node_enb)

    # the global scheduler
    scheduler = Scheduler(verbose=verbose)


    ##########
    check_lease = SshJob(
        scheduler=scheduler,
        node = faraday,
        critical = True,
        verbose=verbose,
        command = Run("rhubarbe leases --check"),
    )

    green_light = check_lease

    if load_images:
        green_light = [
            SshJob(
                scheduler=scheduler,
                required=check_lease,
                node=faraday,
                critical=True,
                verbose=verbose,
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
                verbose=verbose,
                label = f"Load image {worker_image} on worker nodes",
                commands=[
                    Run(f"rhubarbe usrpoff {node_enb}"), # if usrp is on, load could be problematic...
                    Run("rhubarbe", "load", "-i", worker_image, *worker_ids),
                    Run("rhubarbe", "wait", *worker_ids),
                    Run(f"rhubarbe usrpon {node_enb}"), # ensure a reset of the USRP on the enB node
                ],
            ),
            SshJob(
                scheduler=scheduler,
                required=check_lease,
                node=faraday,
                critical=False,
                verbose=verbose,
                label="turning off unused nodes",
                command=[
                    Run("rhubarbe bye --all " 
                        + "".join(f"~{x} " for x in nodes))
                ]
            )
        ]

    ##########
    # Initialize k8 on the master node
    init_master = SshJob(
        scheduler=scheduler,
        required=green_light,
        node=master,
        critical=True,
        verbose=verbose,
        label = f"Install and launch k8 on the master {node_master}",
        commands = [
            Run("swapoff -a"),
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
            verbose=verbose,
            label=f"Init k8 on fit node {id} and join the cluster",
            commands = [
                Run("swapoff -a"),
                Run("increase-control-mtu"),
                Run(f"scp -o 'StrictHostKeyChecking no' {fit_master}:/tmp/join_msg /tmp/join_msg"),
                Run("chmod a+x /tmp/join_msg"),
                Run("/tmp/join_msg"),
            ],
        ) for id, node in worker_index.items()
    ]

    # wait 30s for K8 nodes setup
    wait_k8nodes_ready = PrintJob(
        "Let k8 set up",
        scheduler=scheduler,
        required=init_master,
        sleep=30,
        label="settling k8 nodes"
    )


    init_kube5g = SshJob(
        scheduler=scheduler,
        required = wait_k8nodes_ready,
        node = master,
        verbose=verbose,
        label = f"Add oai:ran label to oai-ran pod on {node_enb} and start 5GOperator pod",
        commands = [
            Run("kubectl get nodes"),
            # add label to the eNB node to help k8s scheduler selects the right fit node
            Run(f"kubectl label nodes fit{node_enb} oai=ran"),
            Run("kubectl get nodes -Loai"),
            ## retrieve the kube5g operator
            #Run("git clone -b develop git@gitlab.eurecom.fr:mosaic5g/kube5g.git"),
            # install a few dependencies
            Run("apt install -y python3-pip"),
            Run("pip3 install --upgrade pip"),
            Run("pip3 install ruamel.yaml==0.16.12 colorlog==4.6.2"),
            # specify the R2lab specific configuration
            Run("cd /root/kube5g/common/config-manager; ./conf-manager.py -s conf_short_r2lab.yaml"),
            # apply the R2lab CRD
            Run("cd /root/kube5g/openshift/kube5g-operator; ./k5goperator.sh -n"),
            # start the kube5g operator pod
            Run("cd /root/kube5g/openshift/kube5g-operator; ./k5goperator.sh container start"),
            Run("kubectl get pods"),
        ],
    )

    # wait 30s for K8 5G Operator setup
    wait_k8_5GOp_ready = PrintJob(
        "Let 5G Operator set up",
        scheduler=scheduler,
        required=init_kube5g,
        sleep=30,
        label="settling 5G Operator pod"
    )

    if only_kube5g:
        finish = SshJob(
            scheduler=scheduler,
            required = wait_k8_5GOp_ready,
            node = master,
            verbose=verbose,
            label = f"showing nodes and pods before leaving",
            commands = [
                Run("kubectl get nodes -Loai"),
                Run("kubectl get pods"),
            ],
        )
    else:
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
            verbose=verbose,
            label = f"deploy CN {cn_type} then eNB pods",
            commands = [
                Run("kubectl get nodes -Loai"),
                Run(f"cd /root/kube5g/openshift/kube5g-operator; ./k5goperator.sh deploy {version} {cn_type}"),
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
            verbose=verbose,
            label = "Check which pods are deployed",
            commands = [
                Run("kubectl get nodes -Loai"),
                Run("kubectl get pods"),
            ],
        )

        ########## Test phone(s) connectivity

        sleeps_ran = [80, 100]
        phone_msgs = [f"wait for {sleep}s for eNB to start up before waking up phone{id}"
                      for sleep, id in zip(sleeps_ran, phones)]
        wait_commands = [f"echo {msg}; sleep {sleep}"
                         for msg, sleep in zip(phone_msgs, sleeps_ran)]
        sleeps_phone = [10, 10]
        phone2_msgs = [f"wait for {sleep}s for phone{id} before starting tests"
                       for sleep, id in zip(sleeps_phone, phones)]
        wait2_commands = [f"echo {msg}; sleep {sleep}"
                          for msg, sleep in zip(phone2_msgs, sleeps_phone)]

        job_start_phones = [
            SshJob(
                node=faraday,
                commands=[
                    Run(wait_command),
                    RunScript(find_local_embedded_script("faraday.sh"), f"macphone{id}",
                              "r2lab-embedded/shell/macphone.sh", "phone-on",
                              includes=INCLUDES),
                    Run(wait2_command),
                    RunScript(find_local_embedded_script("faraday.sh"), f"macphone{id}",
                              "r2lab-embedded/shell/macphone.sh", "phone-check-cx",
                              includes=INCLUDES),
                    RunScript(find_local_embedded_script("faraday.sh"), f"macphone{id}",
                              "r2lab-embedded/shell/macphone.sh", "phone-start-app",
                              includes=INCLUDES),
                ],
                label=f"turn off airplane mode on phone {id}",
                required=check_kube5g,
                scheduler=scheduler)
            for id, wait_command, wait2_command in zip(phones, wait_commands, wait2_commands)]


    ##########
    # Update the .dot and .png file for illustration purposes
    scheduler.check_cycles()
    name = "deploy-kube5g"
    print(10*'*', 'See main scheduler in',
          scheduler.export_as_pngfile(name))

    # orchestration scheduler jobs
    if verbose:
        scheduler.list()

    if dry_run:
        return True

    if not scheduler.orchestrate():
        print(f"RUN KO : {scheduler.why()}")
        scheduler.debrief()
        return False
    print(f"RUN OK, you can log now on master node {fit_master} to manually change the scenario")
    print(80*'*')

##########

def main():
    """
    Command-line frontend - offers primarily all options to kube5g scenario

    """

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument("-g", "--gateway", default=default_gateway,
                        help="specify an alternate gateway")
    parser.add_argument("-s", "--slicename", default=default_slicename,
                        help="specify an alternate slicename")

    parser.add_argument("-D", "--disag-cn", default=default_disag_cn,
                        action='store_true',
                        help="if set, Deploy the Disaggragated CN scenario,"
                             " otherwise deploy the all-in-one CN")
    parser.add_argument("-N", "--node-id", dest='nodes', default=default_nodes,
                        choices=[str(x+1) for x in range(37)],
                        action=ListOfChoices,
                        help="specify as many node ids as you want,"
                             " including master and eNB nodes")
    parser.add_argument("-M", "--node-master", dest='node_master',
                        default=default_node_master,
                        help="specify master id node")
    parser.add_argument("-R", "--ran", default=default_node_enb, dest='node_enb',
                        help="specify the id of the node that runs the eNodeB,"
                             " which requires a USRP b210 and 'duplexer for eNodeB")
    parser.add_argument("-P", "--phones", dest='phones',
                        action=ListOfChoicesNullReset, type=int, choices=(1, 2, 0),
                        default=[1],
                        help='Commercial phones to use; use -p 0 to choose no phone')
    parser.add_argument("-K", "--version", default=default_version,
                        choices=("none","v1", "v2"),
                        help="specify a version for Core Network,"
                        ' if "none" is set, only run the kube5g operator'),

    parser.add_argument("-v", "--verbose", default=default_verbose,
                        action='store_true', dest='verbose',
                        help="run script in verbose mode")
    parser.add_argument("-d", "--debug", default=False,
                        action='store_true', dest='debug',
                        help="print out asyncssh INFO-level messages")
    parser.add_argument("-n", "--dry-runmode", default=default_dry_run,
                        action='store_true', dest='dry_run',
                        help="only pretend to run, don't do anything")

    parser.add_argument("-l", "--load-images", default=True, action='store_true',
                        help="use this for reloading images on used nodes;"
                             " unused nodes will be turned off")
    parser.add_argument("--master-image", dest="master_image",
                        default=default_master_image)
    parser.add_argument("--worker-image", dest="worker_image",
                        default=default_worker_image)


    args = parser.parse_args()

    # asyncssh info messages are turned on by default
    if not args.debug:
        asyncssh_set_log_level(logging.WARNING)
    del args.debug

    # we pass to run exactly the set of arguments known to parser
    # build a dictionary with all the values in the args
    kwds = args.__dict__.copy()

    # actually run it
    if args.version == "none":
        print(f"*** Deploy the k8s nodes and only run the kube5g operator, not the OAI VNFs  *** ")
    else:
        if(args.disag_cn):
            print(f"*** Run the Disaggragated CN Scenario with kube5g {args.version} *** ")
        else:
            print(f"*** Run the all-in-one CN Scenario with kube5g {args.version} *** ")
            print("With the following fit nodes:")
        for i in args.nodes:
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
