#!/usr/bin/env python3

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib import Path

from asynciojobs import Job, Scheduler, PrintJob

from apssh import SshNode, SshJob, Run
from apssh import RunString, RunScript, TimeColonFormatter

##########
gateway_hostname  = 'faraday.inria.fr'
gateway_username  = 'inria_l2bm'
verbose_ssh = True

# sender is node 02
node_sender = 2
node_ids = [1,2,3]
frequency = 2412

parser = ArgumentParser()
parser.add_argument("-s", "--slice", default=gateway_username,
                    help="specify an alternate slicename, default={}"
                         .format(gateway_username))
parser.add_argument("-v", "--verbose-ssh", default=False, action='store_true',
                    help="run ssh in verbose mode")
parser.add_argument("-d", "--driver", default='ath9k',
                    choices = ['iwlwifi', 'ath9k'],
                    help="specify which driver to use")

args = parser.parse_args()

gateway_username = args.slice
verbose_ssh = args.verbose_ssh
wireless_driver = args.driver

##########
faraday = SshNode(hostname = gateway_hostname, username = gateway_username,
                  verbose = verbose_ssh,
                  formatter = TimeColonFormatter())

def fitname(node_id):
    """                                                                      
    Return a valid hostname from a node number - either str or int           
    """
    int_id = int(node_id)
    return "fit{:02d}".format(int_id)

# this is a python dictionary that allows to retrieve a node object      
# from an id                                                             
node_index = {
    id: SshNode(gateway=faraday, hostname=fitname(id), username="root",
                formatter=TimeColonFormatter(), verbose=verbose_ssh)
    for id in node_ids
}
receiver_index = dict(node_index)
del receiver_index[2]

node_ovs = SshNode(gateway = faraday, hostname = "fit02", username = "root",
                verbose = verbose_ssh,
                formatter = TimeColonFormatter())

# the global scheduler                                                   
scheduler = Scheduler(verbose=verbose_ssh)


##########
check_lease = SshJob(
    scheduler=scheduler,
    node = faraday,
    critical = True,
    verbose=verbose_ssh,
    command = Run("rhubarbe leases --check"),
)

green_light = SshJob(
    scheduler=scheduler,
    required=check_lease,
    node=faraday,
    critical=True,
    verbose=verbose_ssh,
    commands=[
#        Run("rhubarbe", "load", "-i", "u16.04-ovs-hostapd", *node_ids),
        Run("rhubarbe", "wait", *node_ids)
    ]
)

####################


##########
# setting up the wireless interface on node_ovs and other receiver nodes

init_nodes = [
    SshJob(
        scheduler=scheduler,
        required=green_light,
        node=node,
        critical=True,
        verbose=verbose_ssh,
        label="init {}".format(id),
        command=RunScript(
            "l2bm-setup.sh", "init-ad-hoc-network",
            wireless_driver, "L2BM", frequency)
    ) for id, node in node_index.items()
]

# test Wi-Fi ad hoc connectivity between receivers and the sender
ping = [
    SshJob(
        scheduler=scheduler,
        required=init_nodes,
        node=node,
        verbose=verbose_ssh,
        label="init {}".format(id),
        command = RunScript(
            "l2bm-setup.sh", "my-ping", '10.0.0.2', 20)
    ) for id, node in receiver_index.items()
]

# Setting up OVS and libfluid on the sender node
ovs_setup = SshJob(
    scheduler=scheduler,
    required = ping,
    node = node_ovs,
    critical=True,
    verbose=verbose_ssh,
    command = RunScript("l2bm-setup.sh", "ovs-setup")
)

# we need to wait for OVS and libfluid controller setup
wait_ovs_job = PrintJob(
    "Let the OVS and Libfluid settle",
    scheduler=scheduler,
    required=ping,
    sleep=100,
    label="settling ovs and libfluid"
)


iperf_sender = SshJob(
    node = node_ovs,
    required = wait_ovs_job,
    verbose=verbose_ssh,
    command = RunScript(
        "l2bm-setup.sh", "iperf_sender",)
)

# Run an iperf receiver at each receiving nodes
iperf_receivers = [
    SshJob(
        scheduler=scheduler,
        required=wait_ovs_job,
        node=node,
        verbose=verbose_ssh,
        label="run iperf on receiver {}".format(id),
        command = RunScript(
            "l2bm-setup.sh", "iperf_receiver")
    ) for id, node in receiver_index.items()
]

##########
# orchestration scheduler jobs
ok = scheduler.orchestrate()
# give details if it failed                                              
if not ok:
    scheduler.debrief()

success = ok and ping.result() == 0

# return something useful to your OS
exit(0 if success else 1)
