#!/usr/bin/env python3

import time

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib import Path

from asynciojobs import Job, Scheduler, PrintJob

from apssh import SshNode, SshJob, Run
from apssh import RunString, RunScript, TimeColonFormatter

# make sure to pip install r2lab
from r2lab import ListOfChoices

##########
default_gateway  = 'faraday.inria.fr'
gateway_username  = 'inria_mosaic'
fit_image = "k8base"
verbose_mode = True
dry_run = False
load_images = False
node_master = 1
node_ids = [1,2,3,23]


##########

def fitname(node_id):
    """                                                                      
    Return a valid hostname from a node number - either str or int           
    """
    int_id = int(node_id)
    return "fit{:02d}".format(int_id)

def run(slicename=gateway_username, load_images=load_images,
        node_ids=node_ids, verbose_mode=verbose_mode,
        node_master=node_master, dry_run=dry_run):
    """
    Install K8 on R2lab

    Arguments:
        slicename: the Unix login name (slice name) to enter the gateway
        load_images: a boolean specifying whether nodes should be re-imaged 
                     first, else nodes will be reset to allow reconfiguration
        node_ids: a list of node ids to run the scenario on; strings or ints 
                  are OK;
        node_master: the master node id, must be part of selected nodes
    """

    if node_master not in node_ids:
        print("master node {} must be part of selected fit nodes {}".format(node_master, node_ids))
        exit(1)

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

    if load_images:
        green_light = SshJob(
            scheduler=scheduler,
            required=check_lease,
            node=faraday,
            critical=True,
            verbose=verbose_mode,
            commands=[
                Run("rhubarbe", "load", "-i", fit_image, *node_ids),
                Run("rhubarbe", "wait", *node_ids)
            ]
        )
    else:
        # reset nodes if images are already loaded
        green_light = SshJob(
            scheduler=scheduler,
            required=check_lease,
            node=faraday,
            critical=True,
            verbose=verbose_mode,
            commands=[
                Run("rhubarbe", "reset", *node_ids),
                Run("rhubarbe", "wait", *node_ids)
            ]
        )

    ##########
    # setting up the wireless interface on all nodes


    # Initialize k8 on the master node
    init_master = SshJob(
        scheduler=scheduler,
        required=green_light,
        node=master,
        critical=True,
        verbose=verbose_mode,
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

    
    # wait a bit for setup
    wait_k8_job = PrintJob(
        "Let k8 settle",
        scheduler=scheduler,
        required=init_workers,
        sleep=10,
        label="settling k8"
        )


    check_workers = SshJob(
        scheduler=scheduler,
        required = wait_k8_job,
        node = master,
        verbose=verbose_mode,
        command = Run("kubectl get nodes"),
    )

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
    Command-line frontend - offers primarily all options to l2bm_scenario

    """

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("-s", "--slicename", default=gateway_username,
                        help="specify an alternate slicename, default={}".format(gateway_username))
    parser.add_argument("-v", "--verbose-mode", default=False, 
                        action='store_true', dest='verbose_mode',
                        help="run script in verbose mode")
    parser.add_argument("-l", "--load-images", default=False, 
                        action='store_true', help="if set, load image on nodes before running the exp")
    parser.add_argument("-W", "--node-id", dest='node_ids',
                        default=node_ids, 
                        choices=[str(x+1) for x in range(37)],
                        action=ListOfChoices,
                        help="specify as many worker node ids as you want")
    parser.add_argument("-M", "--node-master", dest='node_master',
                        default=node_master, 
                        help="specify master id node")
    parser.add_argument(
	"-m", "--map", default=False, action='store_true',
        help="""Probe the testbed to get an updated hardware map
that shows the nodes that currently embed the
capabilities to run as either E3372- and
OpenAirInterface-based UE. Does nothing else.""")
    parser.add_argument(
        "-n", "--dry-run", action='store_true', default=False, dest='dry_run',
        help="run script in dry mode")


    args = parser.parse_args()

    if args.map:
        show_hardware_map(probe_hardware_map())
        exit(0)

    # map is not a recognized parameter in run()
    delattr(args, 'map')

    # we pass to run exactly the set of arguments known to parser
    # build a dictionary with all the values in the args
    kwds = args.__dict__.copy()

    # actually run it
    now = time.strftime("%H:%M:%S")
    print(f"Experiment STARTING at {now}")
    if not run(**kwds):
        print("exiting")
        return    
    


##########
if __name__ == '__main__':
    # return something useful to your OS
    exit(0 if main() else 1)
