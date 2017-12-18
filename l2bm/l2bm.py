#!/usr/bin/env python3

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib import Path

from asynciojobs import Job, Scheduler, PrintJob

from apssh import SshNode, SshJob, Run
from apssh import RunString, RunScript, TimeColonFormatter

from listofchoices import ListOfChoices

##########
default_gateway  = 'faraday.inria.fr'
gateway_username  = 'inria_l2bm'
fit_image = "u16.04-ovs-hostapd"
wireless_driver = 'ath9k'
verbose_mode = True
load_images = False
node_sender = 2
node_ids = [1,2,3]
frequency = 2412
ssid = "L2BM"

##########

def fitname(node_id):
    """                                                                      
    Return a valid hostname from a node number - either str or int           
    """
    int_id = int(node_id)
    return "fit{:02d}".format(int_id)

def run_scenario(slicename=gateway_username, load_images=load_images,
                 node_ids=node_ids, verbose_mode=verbose_mode,
                 node_sender=node_sender):
    """
    Performs L2BM experimentation

    Arguments:
        slicename: the Unix login name (slice name) to enter the gateway
        load_images: a boolean specifying whether nodes should be re-imaged 
                     first, else nodes will be reset to allow reconfiguration
        node_ids: a list of node ids to run the scenario on; strings or ints 
                  are OK;
        node_sender: the sender node id, must be part of selected nodes
    """

    if node_sender not in node_ids:
        print("sender node {} must be part of selected fit nodes {}".format(node_sender, node_ids))
        exit(1)

    faraday = SshNode(hostname=default_gateway, username=slicename,
                      verbose=verbose_mode,
                      formatter=TimeColonFormatter())

    node_ovs = SshNode(gateway=faraday, hostname=fitname(node_sender), 
                       username="root",
                       verbose=verbose_mode,
                       formatter=TimeColonFormatter())

    node_index = {
        id: SshNode(gateway=faraday, hostname=fitname(id), 
                    username="root",formatter=TimeColonFormatter(), 
                    verbose=verbose_mode)
        for id in node_ids
        }

    receiver_index = dict(node_index)
    del receiver_index[node_sender]
    fit_sender = fitname(node_sender)
    ip_sender = "10.0.0.{}".format(node_sender)
    
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

    init_nodes = [
        SshJob(
            scheduler=scheduler,
            required=green_light,
            node=node,
            critical=True,
            verbose=verbose_mode,
            label="init fit node {}".format(id),
            command=RunScript(
                "l2bm-setup.sh", "init-ad-hoc-network",
                wireless_driver, ssid, frequency)
            ) for id, node in node_index.items()
        ]

    # test Wi-Fi ad hoc connectivity between receivers and the sender
    ping = [
        SshJob(
            scheduler=scheduler,
            required=init_nodes,
            node=node,
            verbose=verbose_mode,
            label="ping sender from receiver {}".format(id),
            command=RunScript(
                "l2bm-setup.sh", "my-ping", ip_sender, 20)
            ) for id, node in receiver_index.items()
        ]

    # Setting up OVS and libfluid on the sender node
    ovs_setup = SshJob(
        scheduler=scheduler,
        required=ping,
        node=node_ovs,
        critical=True,
        verbose=verbose_mode,
        command=RunScript("l2bm-setup.sh", "ovs-setup")
        )

    # we need to wait for OVS and libfluid controller setup
    wait_ovs_job = PrintJob(
        "Let the OVS and Libfluid settle",
        scheduler=scheduler,
        required=ping,
        sleep=60,
        label="settling ovs and libfluid"
        )


    iperf_sender = SshJob(
        scheduler=scheduler,
        required = wait_ovs_job,
        node = node_ovs,
        verbose=verbose_mode,
        command = RunScript("l2bm-setup.sh", "iperf_sender")
        )

    # Run an iperf receiver at each receiving nodes
    iperf_receivers = [
        SshJob(
            scheduler=scheduler,
            required=wait_ovs_job,
            node=node,
            verbose=verbose_mode,
            label="run iperf on receiver {}".format(id),
            command = RunScript("l2bm-setup.sh", "iperf_receiver")
            ) for id, node in receiver_index.items()
        ]

    ##########
    # orchestration scheduler jobs
    ok = scheduler.orchestrate()
    # give details if it failed                                              
    if not ok:
        scheduler.debrief()

##########                                                    

def main():
    """    
    Command-line frontend - offers primarily all options to l2bm_scenario

    """

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("-s", "--slice", default=gateway_username,
                        help="specify an alternate slicename, default={}".format(gateway_username))
    parser.add_argument("-v", "--verbose-mode", default=False, 
                        action='store_true',
                        help="run script in verbose mode")
    parser.add_argument("-l", "--load-images", default=False, 
                        action='store_true', help="if set, load image on nodes before running the exp")
    parser.add_argument("-N", "--node-id", dest='node_ids',
                        default=node_ids, 
                        choices=[str(x+1) for x in range(37)],
                        action=ListOfChoices,
                        help="specify as many node ids as you want to run the scenario against")
    parser.add_argument("-S", "--node-sender", dest='node_sender',
                        default=node_sender, 
                        help="specify sender id node")
    args = parser.parse_args()

    # run the experiment on all specified input values 
    return run_scenario(slicename=args.slice, 
                        load_images=args.load_images,
                        node_ids=args.node_ids, verbose_mode=args.verbose_mode,
                        node_sender=args.node_sender)
                       


##########
if __name__ == '__main__':
    # return something useful to your OS
    exit(0 if main() else 1)
