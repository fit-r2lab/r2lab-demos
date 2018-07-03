#!/usr/bin/env python3

from argparse import ArgumentParser

from asynciojobs import Scheduler

from apssh import SshNode, SshJob
from apssh import Run, RunString

##########
gateway_hostname  = 'faraday.inria.fr'
gateway_username  = 'inria_ns3'
verbose_ssh = False

parser = ArgumentParser()
parser.add_argument("-s", "--slice", default=gateway_username,
                    help="specify an alternate slicename, default={}"
                         .format(gateway_username))
parser.add_argument("-v", "--verbose-ssh", default=False, action='store_true',
                    help="run ssh in verbose mode")
args = parser.parse_args()

gateway_username = args.slice
verbose_ssh = args.verbose_ssh

##########
faraday = SshNode(hostname = gateway_hostname, username = gateway_username,
                  verbose = verbose_ssh)

node1 = SshNode(gateway = faraday, hostname = "fit01", username = "root",
                verbose = verbose_ssh)
node2 = SshNode(gateway = faraday, hostname = "fit02", username = "root",
                verbose = verbose_ssh)

##########
# create an orchestration scheduler
scheduler = Scheduler()

##########
check_lease = SshJob(
    # checking the lease is done on the gateway
    node = faraday,
    critical = True,
    command = Run("rhubarbe leases --check"),
    scheduler = scheduler,
)

########## 
# load images on the two nodes
load_script = """
rhubarbe load -i u16.04-ns-3-dev 1
rhubarbe load -i u16.04-ns-3-dev 2
rhubarbe wait 1-2
"""

load_images = SshJob(
        node = faraday,
        required = check_lease,
        critical = True,
        scheduler = scheduler,
        command =  RunString (load_script,),
)

##########
# setting up the data interface on both fit01 and fit02  
# setting up routing on fit01

server_script = """
ifconfig data promisc up
"""

client_script = """
ifconfig data promisc up
"""

init_node_01 = SshJob(
    node = node1,
    command = Run("turn-on-data"),
    required = load_images,
    scheduler = scheduler,
)
init_node_02 = SshJob(
    node = node2,
    command = Run("turn-on-data"),
    required = load_images,
    scheduler = scheduler,
)
final_node_01 = SshJob(
    node = node1,
    command = RunString(
        server_script,
    ),
    required = (init_node_01, init_node_02),
    scheduler = scheduler,
)

final_node_02 = SshJob(
    node = node2,
    command = RunString(
        client_script,
    ),
    required = final_node_01,
    scheduler = scheduler,
)

##########
# run the scheduler
ok = scheduler.orchestrate()

# give details if it failed
ok or scheduler.debrief()

success = ok 

# producing a dot file for illustration
scheduler.export_as_dotfile("ping.dot")

exit(0 if success else 1)
