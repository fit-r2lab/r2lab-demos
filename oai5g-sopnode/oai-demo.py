#!/usr/bin/env python3 -u

"""
a demo script that prepares 4 fit R2lab nodes to join a sopnode k8s cluster for the oai5g demo.

This relies on
* the 'kubernetes' image, that comes with k8s installed
* the 'kube-install.sh' script, that is installed as well on that image in /usr/bin

although not illustrated in this simple script,
the latter can be upgraded with "git -C /root/kube-install pull"
"""

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib import Path

# the default for asyncssh is to be rather verbose
import logging
from asyncssh.logging import set_log_level as asyncssh_set_log_level

from asynciojobs import Job, Scheduler, PrintJob

from apssh import (LocalNode, SshNode, SshJob, Run, RunString, RunScript,
                   TimeColonFormatter, Service, Deferred, Capture, Variables)

# make sure to pip install r2lab
from r2lab import r2lab_hostname, ListOfChoices, ListOfChoicesNullReset, find_local_embedded_script


# where to join; as of this writing:
# sopnode-l1.inria.fr runs a production cluster, and
# sopnode-w2.inria.fr runs an experimental/devel cluster

default_master = 'sopnode-l1.inria.fr'
default_image = 'kubernetes'

default_amf = 1
default_spgwu = 2
default_gnb = 3
default_ue = 9

default_gateway  = 'faraday.inria.fr'
default_slicename  = 'inria_sopnode'

def run(*, gateway, slicename,
        master,
        amf, spgwu, gnb, ue,
        image, load_images,
        verbose, dry_run ):
    """
    add R2lab nodes as workers in a k8s cluster

    Arguments:
        slicename: the Unix login name (slice name) to enter the gateway
        quectel_nodes: list of indices of quectel UE nodes to use
        phones: list of indices of phones to use
        nodes: a list of node ids to run the scenario on; strings or ints
                  are OK;
        node_master: the master node id, must be part of selected nodes
        node_enb: the node id for the enb, which is connected to usrp/duplexer
        disaggregated_cn: Boolean; True for the disaggregated CN scenario. False for all-in-one CN.
        operator_version: str, either "none" or "v1" or "v2".
    """

    faraday = SshNode(hostname=gateway, username=slicename,
                      verbose=verbose,
                      formatter=TimeColonFormatter())
    
    hostnames = [r2lab_hostname(x) for x in (amf, spgwu, gnb, ue)]


    node_index = {
        id: SshNode(gateway=faraday, hostname=r2lab_hostname(id),
                    username="root",formatter=TimeColonFormatter(),
                    verbose=verbose)
        for id in (amf, spgwu, gnb, ue)
    }
    worker_ids = [amf, spgwu, gnb, ue]

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
                label = f"Load image {image} on worker nodes",
                commands=[
                    Run("rhubarbe", "load", *worker_ids, "-i", image),
                    Run("rhubarbe", "wait", *worker_ids),
                ],
            ),
# for now, useless to switch off other nodes as we use RfSimulator            
#            SshJob(
#                scheduler=scheduler,
#                required=check_lease,
#                node=faraday,
#                critical=False,
#                verbose=verbose,
#                label="turning off unused nodes",
#                command=[
#                    Run("rhubarbe bye --all "
#                        + "".join(f"~{x} " for x in nodes))
#                    Run("sleep 1") 
#                ]
#            )
        ]

    prepares = [
        SshJob(
            scheduler=scheduler,
            required=green_light,
            node=node,
            critical=False,
            verbose=verbose,
            label=f"Reset data interface, ipip tunnels of worker node {r2lab_hostname(id)} and possibly leave {master} k8s cluster",
            command=[
                Run("nmcli con down data; nmcli dev status; leave-tunnel"),
                Run(f"kube-install.sh leave-cluster r2lab@{master}"),
            ]
        ) for id, node in node_index.items()
    ]

    joins = [
        SshJob(
            scheduler=scheduler,
            required=prepares,
            node=node,
            critical=True,
            verbose=verbose,
            label=f"Set data interface and ipip tunnels of worker node {r2lab_hostname(id)} and add it to {master} k8s cluster",
            command=[
                Run("nmcli con up data; nmcli dev status; join-tunnel"),
                Run(f"kube-install.sh join-cluster r2lab@{master}")
            ]
        ) for id, node in node_index.items()
    ]

    scheduler.check_cycles()
    print(10*'*', 'See main scheduler in',
          scheduler.export_as_pngfile("oai-demo"))

    # orchestration scheduler jobs
    if verbose:
        scheduler.list()

    if dry_run:
        return True

    if not scheduler.orchestrate():
        print(f"RUN KO : {scheduler.why()}")
        scheduler.debrief()
        return False
    print(f"Worker FIT nodes ready. You can now log on oai@{master} cluster and launch the k8s demo-oai script")
    print(80*'*')

        
def main():
    """
    CLI frontend
    """
        
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument("--amf", default=default_amf,
                        help="id of the node that runs oai-amf")

    parser.add_argument("--spgwu", default=default_spgwu,
                        help="id of the node that runs oai-spgwu")

    parser.add_argument("--gnb", default=default_gnb,
                        help="id of the node that runs oai-gnb")

    parser.add_argument("--ue", default=default_ue,
                        help="id of the node that runs oai-ue")

    parser.add_argument(
        "-i", "--image", default=default_image,
        help="kubernetes image to load on nodes")
    
    parser.add_argument(
        "-m", "--master", default=default_master,
        help=f"kubernetes master node, default is {default_master}")
    
    parser.add_argument(
        "-s", "--slicename", default=default_slicename,
        help="slicename used to book FIT nodes, default is {default_slicename}")

    parser.add_argument("-l", "--load", dest='load_images',
                        action='store_true', default=False,
                        help='load images as well'),
    parser.add_argument("-v", "--verbose", default=False,
                        action='store_true', dest='verbose',
                        help="run script in verbose mode")
    parser.add_argument("-n", "--dry-runmode", default=False,
                        action='store_true', dest='dry_run',
                        help="only pretend to run, don't do anything")


    args = parser.parse_args()

    print(f"**** Running oai5g demo on k8s master {args.master} with {args.slicename} slicename")
    print(f"Following FIT nodes will be used:")
    print(f"\t{r2lab_hostname(args.amf)} for oai-amf")
    print(f"\t{r2lab_hostname(args.spgwu)} for oai-spgwu-tiny")
    print(f"\t{r2lab_hostname(args.gnb)} for oai-gnb")
    print(f"\t{r2lab_hostname(args.ue)} for oai-nr-ue")
    if args.load_images:
        print(f"with k8s image {args.image} loaded")
    
    
    run(gateway=default_gateway, slicename=args.slicename,
        master=args.master, amf=args.amf, spgwu=args.spgwu,
        gnb=args.gnb, ue=args.ue, dry_run=args.dry_run,
        verbose=args.verbose, load_images=args.load_images,
        image=args.image
    )


if __name__ == '__main__':
    # return something useful to your OS
    exit(0 if main() else 1)
