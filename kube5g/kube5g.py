#!/usr/bin/env python3 -u

import time

from sys import platform

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib import Path

# the default for asyncssh is to be rather verbose
import logging
from asyncssh.logging import set_log_level as asyncssh_set_log_level

from asynciojobs import Job, Scheduler, PrintJob

from apssh import (LocalNode, SshNode, SshJob, Run, RunString, RunScript,
                   TimeColonFormatter, Service, Deferred, Capture, Variables)

# make sure to pip install r2lab
from r2lab import ListOfChoices, ListOfChoicesNullReset, find_local_embedded_script

# include the set of utility scripts that are included by the r2lab kit
INCLUDES = [find_local_embedded_script(x) for x in (
    "r2labutils.sh", "nodes.sh", "mosaic-common.sh",
)]

##########
default_gateway  = 'faraday.inria.fr'
default_slicename  = 'inria_kube5g'

default_disaggregated_cn = False
default_operator_version = 'v1'

default_nodes = [1, 2, 3, 5, 23]
default_node_master = 1
default_node_enb = 23
default_phones = [1,]

default_flexran = False
default_drone = False

default_verbose = False
default_dry_run = False

default_load_images = True
default_master_image = "kube5g-master-v2.2"
# v2 master image is a k8base with latest kube5g v2 installed (latest core version but not latest ran)
#default_master_image = "k8base" # now kube5g is installed in this script
# k8base-v2 now includes Osama's fix for drone app (git clone -b droneapp https://gitlab.eurecom.fr/mosaic5g/store.git)
default_worker_image = "k8base-v2"

##########

def fitname(node_id):
    """
    Return a valid hostname from a node number - either str or int
    """
    int_id = int(node_id)
    return "fit{:02d}".format(int_id)

def run(*, gateway, slicename,
        disaggregated_cn, operator_version, nodes, node_master, node_enb, phones, flexran,
        drone, verbose, dry_run,
        load_images, master_image, worker_image):
    """
    Install K8S on R2lab

    Arguments:
        slicename: the Unix login name (slice name) to enter the gateway
        phones: list of indices of phones to use
        nodes: a list of node ids to run the scenario on; strings or ints
                  are OK;
        node_master: the master node id, must be part of selected nodes
        node_enb: the node id for the enb, which is connected to usrp/duplexer
        disaggregated_cn: Boolean; True for the disaggregated CN scenario. False for all-in-one CN.
        operator_version: str, either "none" or "v1" or "v2".
    """

    if operator_version == "none":
        only_kube5g = True
    else:
        only_kube5g = False

    if node_master not in nodes:
        print(f"master node {node_master} must be part of selected fit nodes {nodes}")
        exit(1)
    if node_enb not in nodes:
        print(f"eNB worker node {node_enb} must be part of selected fit nodes {nodes}")
        exit(1)

    # Check if the browser can be automatically run to display the Drone app
    if drone:
        run_browser = True
        if platform == "linux":
            cmd_open = "xdg-open"
        elif platform == "darwin":
            cmd_open = "open"
        else:
            run_browser = False
        if run_browser:
            print(f"**** Will run the browser with command {cmd_open}")
        else:
            print(f"**** Will not be able to run the browser as platform is {platform}")


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
                    Run(f"rhubarbe load {node_master} -i {master_image}"),
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
                    Run("rhubarbe", "load", *worker_ids, "-i", worker_image),
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
    # Initialize k8s on the master node
    init_master = SshJob(
        scheduler=scheduler,
        required=green_light,
        node=master,
        critical=True,
        verbose=verbose,
        label = f"Install and launch k8s on the master {node_master}",
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
            label=f"Init k8s on fit node {id} and join the cluster",
            commands = [
                Run("swapoff -a"),
                Run("increase-control-mtu"),
                Run(f"scp -o 'StrictHostKeyChecking no' {fit_master}:/tmp/join_msg /tmp/join_msg"),
                Run("chmod a+x /tmp/join_msg"),
                Run("/tmp/join_msg"),
            ],
        ) for id, node in worker_index.items()
    ]

    # wait 10s for K8S nodes setup
    wait_k8nodes_ready = PrintJob(
        "Let k8s set up",
        scheduler=scheduler,
        required=init_workers,
        sleep=10,
        label="sleep 10s for the k8s nodes to settle"
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

    # wait 30s for K8S 5G Operator setup
    wait_k8_5GOp_ready = PrintJob(
        "Let 5G Operator set up",
        scheduler=scheduler,
        required=init_kube5g,
        sleep=30,
        label="wait 30s for the 5G Operator pod to settle"
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
        if disaggregated_cn:
            cn_type="disaggregated-cn"
#            setup_time = 120
            setup_time = 200
        else:
            cn_type="all-in-one"
#            setup_time = 60
            setup_time = 140
        if flexran:
            flexran_opt="flexran"
        else:
            flexran_opt=""

        run_kube5g = SshJob(
            scheduler=scheduler,
            required = wait_k8_5GOp_ready,
            node = master,
            verbose=verbose,
            label = f"deploy {operator_version} {cn_type} {flexran_opt} pods",
            commands = [
                Run("kubectl get nodes -Loai"),
                Run(f"cd /root/kube5g/openshift/kube5g-operator; ./k5goperator.sh deploy {operator_version} {cn_type} {flexran_opt}"),
                Run("kubectl get pods"),
            ],
        )

        # Coffee Break -- wait 1 or 2mn for K8S 5G pods setup
        wait_k8_5Gpods_ready = PrintJob(
            "Let all 5G pods set up",
            scheduler=scheduler,
            required=run_kube5g,
            sleep=setup_time,
            label=f"waiting {setup_time}s for all 5G pods to settle"
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

        if drone:
            # the place where runtime variables get stored
            env = Variables()
            #
            # Define and run all the services to launch the Drone app locally on a firefox browser
            #
            drone_service = Service(
                command=f"python /root/mosaic5g/store/sdk/frontend/drone/drone.py --port=8088 --tasks --address=192.168.3.{node_enb}",
                service_id="drone_app",
                verbose=verbose,
            )
            k8s_port9999_fwd_service = Service(
                command=Deferred("kubectl port-forward {{flexran_pod}} 9999:9999 --address 0.0.0.0", env),
                service_id="k8s-port9999-fwd",
                verbose=verbose,
                # somehow this is required for kubectl to run properly
                environ={'KUBECONFIG': '/etc/kubernetes/admin.conf'}
            )
            # can't use a Service instance on the local box if it's not a Linux
            # and we have macs...
            local_port_fwd = (f"ssh -f -N -4"
                             f" -L9999:192.168.3.{node_master}:9999"
                             f" -L8088:192.168.3.{node_enb}:8088"
                             f" -o ExitOnForwardFailure=yes"
                             f" {slicename}@faraday.inria.fr")
            browser_service = Service(
                command=f"sleep 10; {cmd_open} http://127.0.0.1:8088/",
                service_id="drone_browser",
                verbose=verbose,
            )

            run_drone=SshJob(
                scheduler=scheduler,
                required=check_kube5g,
                node=worker_index[node_enb],
                verbose=verbose,
                label=f"Run the drone app on worker node {node_enb} as a service",
                commands=[
                    drone_service.start_command(),
                ],
            )
            get_flexran_podname=SshJob(
                scheduler=scheduler,
                required=check_kube5g,
                node=master,
                verbose=verbose,
                label=f"Retrieve the name of the FlexRAN pod",
                commands=[
                    # xxx here
                    Run("kubectl get --no-headers=true pods -l app=flexran -o custom-columns=:metadata.name",
                        capture=Capture('flexran_pod', env)),
                ],
            )
            run_k8s_port9999_fwd=SshJob(
                scheduler=scheduler,
                required=get_flexran_podname,
                node=master,
                verbose=verbose,
                label=f"Run port forwarding on the master node as a service",
                commands=[
                    k8s_port9999_fwd_service.start_command(),
                ],
            )
            # On the local machine, impossible to use Services as the latter uses systemd-run, only available on Linux
            run_local_ports_fwd = SshJob(
                scheduler=scheduler,
                required = check_kube5g,
                node = LocalNode(),
                verbose=verbose,
                label = f"Forward local ports 8088 and 9999",
                command=Run(local_port_fwd + "&", ignore_outputs=True),
            )
            if run_browser:
                run_local_browser = SshJob(
                    scheduler=scheduler,
                    required = (run_drone, run_k8s_port9999_fwd, run_local_ports_fwd),
                    node = LocalNode(),
                    verbose=verbose,
                    label = f"Run the browser on the local node in background",
                    command=browser_service.command+"&",
                )
                phones_requirements=run_local_browser
            else:
                phones_requirements=run_k8s_port9999_fwd
        else:
            phones_requirements=check_kube5g


        
        ########## Test phone(s) connectivity

        sleeps_ran = (10, 20)
        phone_msgs = [f"wait for {sleep}s for eNB to start up before waking up phone{id}"
                      for sleep, id in zip(sleeps_ran, phones)]
        wait_commands = [f"echo {msg}; sleep {sleep}"
                         for msg, sleep in zip(phone_msgs, sleeps_ran)]
        sleeps_phone = (10, 10)
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
                required=phones_requirements,
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

    parser.add_argument("-D", "--disaggregated-cn", default=default_disaggregated_cn,
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
                        default=default_phones,
                        help='Commercial phones to use; use -p 0 to choose no phone')
    parser.add_argument("-O", "--operator-version", default=default_operator_version,
                        choices=("none", "v1", "v2"),
                        help="specify a version for Core Network,"
                        ' if "none" is set, only run the kube5g operator'),
    parser.add_argument("-F", "--flexran", default=default_flexran,
                        action='store_true', dest='flexran',
                        help="run FlexRAN")
    parser.add_argument("-X", "--drone", default=default_drone,
                        action='store_true', dest='drone',
                        help="run FlexRAN with Drone")

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

    # Enforce FlexRAN option in case the Drone app is selected
    if args.drone:
        args.flexran = True

    # we pass to run exactly the set of arguments known to parser
    # build a dictionary with all the values in the args
    kwds = args.__dict__.copy()

    # actually run it
    if args.operator_version == "none":
        print(f"*** Deploy the k8s nodes and only run the kube5g operator, not the OAI VNFs  *** ")
    else:
        if(args.disaggregated_cn):
            print(f"*** Run the {args.operator_version} Disaggregated CN Scenario with kube5g *** ")
        else:
            print(f"*** Run the {args.operator_version} all-in-one CN Scenario with kube5g *** ")
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
        if args.drone:
            print("Run also FlexRAN with the Drone app")
        else:
            if args.flexran:
                print("Run also FlexRAN without Drone")
            else:
                print("Do not run FlexRAN")
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
