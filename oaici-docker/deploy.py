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
default_slicename  = 'inria_oaici'

default_nodes = [17, 23]
default_node_epc = 17
default_node_enb = 23
default_quectel_nodes = []
default_phones = [1,]

default_verbose = False
default_dry_run = False

default_load_images = True
default_epc_image = "oai-ci-cd-u18-epc-latest"
default_enb_image = "oai-ci-u18-lowlatency-enb-ue-docker-latest"
default_quectel_image = "u20.04-quectel"

##########

def fitname(node_id):
    """
    Return a valid hostname from a node number - either str or int
    """
    int_id = int(node_id)
    return "fit{:02d}".format(int_id)

def run(*, gateway, slicename,
        nodes, node_epc, node_enb, quectel_nodes, phones,
        verbose, dry_run, load_images, epc_image, enb_image, quectel_image):
    """
    Launch latest OAICI EPC and eNB Docker images on R2lab

    Arguments:
        slicename: the Unix login name (slice name) to enter the gateway
        quectel_nodes: list of indices of quectel UE nodes to use
        phones: list of indices of phones to use
        nodes: a list of node ids to run the scenario on; strings or ints
                  are OK;
        node_epc: the node id on which to run the EPC
        node_enb: the node id for the enb, which is connected to B210/eNB-duplexer

    """

    quectel_ids = quectel_nodes[:]
    quectel = len(quectel_ids) > 0

    faraday = SshNode(hostname=default_gateway, username=slicename,
                      verbose=verbose,
                      formatter=TimeColonFormatter())

    epc = SshNode(gateway=faraday, hostname=fitname(node_epc),
                  username="root",
                  verbose=verbose,
                  formatter=TimeColonFormatter())

    node_index = {
        id: SshNode(gateway=faraday, hostname=fitname(id),
                    username="root",formatter=TimeColonFormatter(),
                    verbose=verbose)
        for id in nodes
    }
    
    nodes_quectel_index = {
        id: SshNode(gateway=faraday, hostname=fitname(id),
                    username="root",formatter=TimeColonFormatter(),
                    verbose=verbose)
        for id in quectel_nodes
    }
    allnodes = nodes + quectel_nodes
    
    fit_epc = fitname(node_epc)
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
                label = f"Load image {epc_image} on {fit_epc}",
                commands=[
                    Run(f"rhubarbe load {node_epc} -i {epc_image}"),
                    Run(f"rhubarbe wait {node_epc}"),
                    RunScript("oaici.sh", "init-epc", node_epc, node_enb),
                ]
            ),
            SshJob(
                scheduler=scheduler,
                required=check_lease,
                node=faraday,
                critical=True,
                verbose=verbose,
                label = f"Load image {enb_image} on {fit_enb}",
                commands=[
                    Run(f"rhubarbe usrpoff {node_enb}"), # if usrp is on, load could be problematic...
                    Run(f"rhubarbe load {node_enb} -i {enb_image}"),
                    Run(f"rhubarbe wait {node_enb}"),
                    Run(f"rhubarbe usrpon {node_enb}"), # ensure a reset of the USRP on the enB node
                    RunScript("oaici.sh", "init-enb", node_enb, node_epc),
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
                        + "".join(f"~{x} " for x in allnodes))
                ]
            )
        ]
        if quectel:
            prepare_quectel = SshJob(
                scheduler=scheduler,
                required=check_lease,
                node=faraday,
                critical=True,
                verbose=verbose,
                label = f"Load image {quectel_image} on quectel UE nodes",
                commands=[
                    Run("rhubarbe", "usrpoff", *quectel_ids),
                    Run("rhubarbe", "load", *quectel_ids, "-i", quectel_image),
                    Run("rhubarbe", "wait", *quectel_ids),
                    Run("rhubarbe", "usrpon", *quectel_ids),
                ],
            ),

        
    ##########
    # Prepare the Quectel UE nodes
    if quectel:
        # wait 30s for Quectel modules show up
        wait_quectel_ready = PrintJob(
            "Let Quectel modules show up",
            scheduler=scheduler,
            required=prepare_quectel,
            sleep=30,
            label="sleep 30s for the Quectel modules to show up"
        )
        # run the Quectel Connection Manager as a service on each Quectel UE node
        quectelCM_service = Service(
                command="quectel-CM -s oai.ipv4 -4",
                service_id="QuectelCM",
                verbose=verbose,
        )
        init_quectel_nodes = [
            SshJob(
                scheduler=scheduler,
                required=wait_quectel_ready,
                node=node,
                critical=True,
                verbose=verbose,
                label=f"Init Quectel UE on fit node {id}",
                commands = [
                    Run("lsusb -t"),
                    Run("ls /dev/ttyUSB*"),
                    quectelCM_service.start_command(),
                ],
            ) for id, node in nodes_quectel_index.items()
        ]
        # wait 20s for Quectel Connection Manager to start up
        wait_quectelCM_ready = PrintJob(
            "Let QuectelCM start up",
            scheduler=scheduler,
            required=init_quectel_nodes,
            sleep=20,
            label="sleep 20s for the Quectel Connection Manager to start up"
        )
        detach_quectel_nodes = [
            SshJob(
                scheduler=scheduler,
                required=wait_quectelCM_ready,
                node=node,
                critical=True,
                verbose=verbose,
                label=f"Detach Quectel UE on fit node {id}",
                commands = [
                    Run("python3 ci_ctl_qtel.py /dev/ttyUSB2 detach"),
                ],
            ) for id, node in nodes_quectel_index.items()
        ]


    ##########
    # Launch the EPC
    start_epc = SshJob(
        scheduler=scheduler,
        required=green_light,
        node=faraday,
        critical=True,
        verbose=verbose,
        label = f"Launch EPC on {fit_epc}",
        commands = [
            RunScript("oaici.sh", "start-epc", node_epc),
        ],
    )
    # Launch the eNB
    if quectel:
        req = (start_epc, detach_quectel_nodes)
    else:
        req = start_epc
    start_enb = SshJob(
        scheduler=scheduler,
        required=req,
        node=faraday,
        critical=True,
        verbose=verbose,
        label = f"Launch eNB on {fit_enb}",
        commands = [
            RunScript("oaici.sh", "start-enb", node_enb),
        ],
    )

    ########## Test phone(s) connectivity

    sleeps_ran = (50, 60)
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
            required=start_enb,
            scheduler=scheduler)
        for id, wait_command, wait2_command in zip(phones, wait_commands, wait2_commands)
    ]
    if quectel:
        job_start_quectel = [
            SshJob(
                scheduler=scheduler,
                required=(job_start_phones,detach_quectel_nodes),
                node=node,
                critical=True,
                verbose=verbose,
                label=f"Attach Quectel UE on fit node {id}",
                command = Run("python3 ci_ctl_qtel.py /dev/ttyUSB2 wup"),
            ) for id, node in nodes_quectel_index.items()
        ]
    

    ##########
    # Update the .dot and .png file for illustration purposes
    scheduler.check_cycles()
    name = "deploy-oaici"
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
    print(f"RUN OK, you can log now on the EPC node {fit_epc} and the eNB node {fit_enb} to check the logs")
    print(80*'*')

##########

def main():
    """
    Command-line frontend - offers primarily all options to oaici scenario

    """

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument("-g", "--gateway", default=default_gateway,
                        help="specify an alternate gateway")
    parser.add_argument("-s", "--slicename", default=default_slicename,
                        help="specify an alternate slicename")

    parser.add_argument("-N", "--node-id", dest='nodes', default=default_nodes,
                        choices=[str(x+1) for x in range(37)],
                        action=ListOfChoices,
                        help="specify as many node ids as you want,"
			" including master and eNB nodes")
    
    parser.add_argument("-R", "--ran", default=default_node_enb, dest='node_enb',
                        help="specify the id of the node that runs the eNodeB,"
                             " which requires a USRP b210 and 'duplexer for eNodeB")
    
    parser.add_argument("-E", "--epc", default=default_node_epc, dest='node_epc',
                        help="specify the id of the node that runs the EPC")

    parser.add_argument("-P", "--phones", dest='phones',
                        action=ListOfChoicesNullReset, type=int, choices=(1, 2, 0),
                        default=default_phones,
                        help='Commercial phones to use; use -p 0 to choose no phone')
    parser.add_argument("-Q", "--quectel-id", dest='quectel_nodes',
                        default=default_quectel_nodes,
                        choices=["32",],
                        action=ListOfChoices,
			help="specify as many node ids with Quectel UEs as you want")

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
    parser.add_argument("--epc-image", dest="epc_image",
                        default=default_epc_image)
    parser.add_argument("--enb-image", dest="enb_image",
                        default=default_enb_image)
    parser.add_argument("--quectel-image", dest="quectel_image",
                        default=default_quectel_image)


    args = parser.parse_args()

    # asyncssh info messages are turned on by default
    if not args.debug:
        asyncssh_set_log_level(logging.WARNING)
    del args.debug

    # we pass to run exactly the set of arguments known to parser
    # build a dictionary with all the values in the args
    kwds = args.__dict__.copy()

    # actually run it
    print(f"*** Deploy the latest OAICI docker images *** ")
    print("\tWith the following fit nodes:")
    for i in args.nodes:
        if i == args.node_epc:
            role = "EPC node"
        elif i == args.node_enb:
            role = "eNB node"
        else:
            role = "Undefined"
        nodename = fitname(i)
        print(f"\t{nodename}: {role}")
    if args.phones:
        for phone in args.phones:
            print(f"Using phone{phone}")
    else:
        print("No phone involved")
    if args.quectel_nodes:
        for quectel in args.quectel_nodes:
            print(f"Using Quectel UE on node {quectel}")
    else:
        print("No Quectel UE involved")

    now = time.strftime("%H:%M:%S")
    print(f"Experiment STARTING at {now}")
    if not run(**kwds):
        print("exiting")
        return


##########
if __name__ == '__main__':
    # return something useful to your OS
    exit(0 if main() else 1)
