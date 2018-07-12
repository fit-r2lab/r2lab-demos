#!/usr/bin/env python3

from argparse import ArgumentParser

from asynciojobs import Scheduler

from apssh import SshNode, SshJob, LocalNode
from apssh import Run, RunString, Pull

def fitname(node_id):
    """
    Return a valid hostname from a node number - either str or int
    """
    int_id = int(node_id)
    return "fit{:02d}".format(int_id)

##########
gateway_hostname  = 'faraday.inria.fr'
gateway_username  = 'inria_ns3'
verbose_ssh = False

# Default fit ids for server and client
def_server, def_client = 1, 2

# Images names for server and client
image_server = "ubuntu"
image_client = "u16.04-ns-3-dev"

parser = ArgumentParser()
parser.add_argument("-s", "--slice", default=gateway_username,
                    help="specify an alternate slicename, default={}"
                         .format(gateway_username))
parser.add_argument("-S", "--server", default=def_server,
                    help="id of the node that runs the server")
parser.add_argument("-C", "--client", default=def_client,
                    help="id of the node that runs the server")
parser.add_argument("-v", "--verbose-ssh", default=False, action='store_true',
                    help="run ssh in verbose mode")
parser.add_argument("-l", "--load-images", default=False, action='store_true',
                    help="enable to load the default image on nodes before the exp")
args = parser.parse_args()

gateway_username = args.slice
verbose_ssh = args.verbose_ssh

server, client = fitname(args.server), fitname(args.client)
print("Running script with server {} and client {}".format(server,client))

##########
faraday = SshNode(hostname = gateway_hostname, username = gateway_username,
                  verbose = verbose_ssh)

server = SshNode(gateway = faraday, hostname = server, username = "root",
                 verbose = verbose_ssh)
client = SshNode(gateway = faraday, hostname = client, username = "root",
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

########## load images on the two nodes if requested

green_light = check_lease

if args.load_images:
    # replace green_light in this case
    green_light = SshJob(
        node = faraday,
        required = check_lease,
        critical = True,
        scheduler = scheduler,
        commands = [
            Run("rhubarbe", "load", "-i", image_server, args.server),
            Run("rhubarbe", "load", "-i", image_client, args.client),
            Run("rhubarbe", "wait", "-t",  120, args.server, args.client),
        ]
    )

##########
# setting up the data interface on both the server and the client
# setting up routing on the server node

server_script = """
route add -net 10.1.1.0 gw 192.168.2.2 netmask 255.255.255.0 dev data
apt-get install smcroute
"""

client_script = """
ifconfig data promisc up
"""

waf_script = """
cd ns-3-dev
./waf --run "scratch/multicast-csma"
"""


init_server = SshJob(
    node = server,
    scheduler = scheduler,
    required = green_light,
    commands = [
        Run("turn-on-data"),
        RunString(server_script, label="init server node"),
    ],
)

init_client = SshJob(
    node = client,
    scheduler = scheduler,
    required = green_light,
    commands = [
        Run("turn-on-data"),
        RunString(client_script, label="init client node"),
    ],
)

mc_sender_job = [
    SshJob(
        node=server,
        #scheduler=scheduler
        forever=True,
        critical=False,
        label = "Run mcsender on server",
        commands =  Run ("mcsender -t16 -idata 225.1.2.4:1234"),
        )
]
mc_sender = Scheduler(*mc_sender_job,
                       scheduler=scheduler,
                       required=(init_client, init_server),
                       label="Run mc sender on server")

run_ns3 = SshJob(
    node = client,
    scheduler = scheduler,
    required = (init_client, init_server),
    command = RunString(waf_script, label="Run ns-3 script on client"),
)

stop_mc_sender = SshJob(
    node = server,
    scheduler = scheduler,
    required = run_ns3,
    label = "kill mc sender at server",
    command = Run("pkill mcsender"),
)

pull_files = SshJob(
    node = client,
    scheduler = scheduler,
    required = stop_mc_sender,
    label = "Retrieve pcap file from client",
    command = Pull (remotepaths="ns-3-dev/csma-multicast-2-0.pcap",localpath="."),
)




##########
# run the scheduler
ok = scheduler.orchestrate()

# give details if it failed
ok or scheduler.debrief()

success = ok 

# producing a png file for illustration
scheduler.export_as_pngfile("multicast-csma")

exit(0 if success else 1)
