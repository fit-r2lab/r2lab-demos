#!/usr/bin/env python3

from argparse import ArgumentParser

from asynciojobs import Scheduler

from apssh import SshNode, SshJob, Run
from apssh import RunString, RunScript, TimeColonFormatter

##########
gateway_hostname  = 'faraday.inria.fr'
gateway_username  = 'inria_l2bm'
verbose_ssh = True
#verbose_ssh = False

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

node1 = SshNode(gateway = faraday, hostname = "fit01", username = "root",
                verbose = verbose_ssh,
                formatter = TimeColonFormatter())

node2 = SshNode(gateway = faraday, hostname = "fit02", username = "root",
                verbose = verbose_ssh,
                formatter = TimeColonFormatter())

##########
check_lease = SshJob(
    # checking the lease is done on the gateway
    node = faraday,
    # this means that a failure in any of the commands
    # will cause the scheduler to bail out immediately
    critical = True,
    command = Run("rhubarbe leases --check"),
)

####################

##########
# setting up the wireless interface on both fit01 and fit02
init_node_01 = SshJob(
    node = node1,
    required = check_lease,
    command = RunScript(
        "l2bm-setup.sh", "init-ad-hoc-network",
        wireless_driver, "L2BM", 2412,
#        verbose=True,
    ))

init_node_02 = SshJob(
    node = node2,
    required = check_lease,
    command = RunScript(
        "l2bm-setup.sh", "init-ad-hoc-network",
        wireless_driver, "L2BM", 2412))

# test Wi-Fi ad hoc connectivity between the two nodes 
ping = SshJob(
    node = node1,
    required = (init_node_01, init_node_02),
    command = RunScript(
        "l2bm-setup.sh", "my-ping", '10.0.0.2', 20,
#        verbose=True,
    ))

# Let fit02 node be the OVS switch node

ovs_setup = SshJob(
    node = node2,
    required = ping,
    command = RunScript(
        "l2bm-setup.sh", "ovs-setup",
#        verbose=True,                                                          
    ))

# we need to wait for fit01 OVS and libfluid controller setup
duration = 60
msg = "wait for OVS and libfluid setup in fit01".format(duration)
job_wait = Job(
    verbose_delay(duration, msg),
    label = msg,
    required = ping
)

iperf_sender = SshJob(
    node = node2,
    required = job_wait,
    command = RunScript(
        "l2bm-setup.sh", "iperf_sender",)
    )

# Run an iperf receiver at node 01
iperf_receiver = SshJob(
    node = node1,
    required = iperf_sender,
    command = RunScript(
        "l2bm-setup.sh", "iperf_receiver",
#        verbose=True,                                                          
    ))


##########
# our orchestration scheduler has 4 jobs to run this time
sched = Scheduler(check_lease, init_node_01, init_node_02, ping, ovs_setup, iperf_sender, iperf_receiver)

# run the scheduler
ok = sched.orchestrate()
# give details if it failed
ok or sched.debrief()

success = ok and ping.result() == 0

# return something useful to your OS
exit(0 if success else 1)
