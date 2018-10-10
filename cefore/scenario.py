#!/usr/bin/env python3

# pylint: disable=c0103

from collections import defaultdict

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from asynciojobs import Scheduler, PrintJob

from apssh import SshNode, LocalNode, SshJob
from apssh import Run, RunString, RunScript, Pull


## illustrating the r2lab library
# utils
from r2lab import r2lab_hostname, r2lab_parse_slice, find_local_embedded_script

# argument parsing
from r2lab import ListOfChoices, ListOfChoicesNullReset
# include the set of utility scripts that are included by the r2lab kit
includes = [ find_local_embedded_script(x) for x in [
    "r2labutils.sh",
] ]

def fitname(node_id):
    """
    Return a valid hostname from a node number - either str or int
    """
    int_id = int(node_id)
    return "fit{:02d}".format(int_id)

##########
gateway_hostname  = 'faraday.inria.fr'
#gateway_username  = 'inria_cefore'
gateway_username  = 'inria_electrosmart'
verbose_ssh = False

# Default fit id for the node that runs ns-3/dce
def_simulator = 2
# Default fit id for the node that runs the publisher
def_publisher = 1

# Waiting time for producer to settle
settle_delay = 15

# Images names for server and client
image_simulator = "dce"
image_publisher = "cefore"

parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
parser.add_argument("-s", "--slice", default=gateway_username,
                    help="specify an alternate slicename")
parser.add_argument("-S", "--simulator", default=def_simulator,
                    help="id of the node that runs ns-3/dce")
parser.add_argument("-P", "--publisher", default=def_publisher,
                    help="id of the node that runs the publisher")
parser.add_argument("-v", "--verbose-ssh", default=False, action='store_true',
                    help="run ssh in verbose mode")
parser.add_argument("-n", "--dry-run", action='store_true', default=False)
parser.add_argument("-l", "--load-images", default=False, action='store_true',
                    help="load default image nodes before running the exp")
args = parser.parse_args()

gateway_username = args.slice
verbose_ssh = args.verbose_ssh
dry_run = args.dry_run

waf_script = "cd NS3/source/ns-3-dce; ./waf --run dce-test-twoRealNodes-wifiSimConsumers-onlyTap-v1"

#waf_script = """ cd ns-3-dev; ./waf --run "scratch/olsr --remote={} --local={} --dstnNode={} --stopTime={} --multicast=true" """.format(args.server,args.client,target_node,duration)


simulator, publisher = fitname(args.simulator), fitname(args.publisher)



print("Running scenario with ns-3/dce running at {}"
      " and publisher running at {}"
      .format(simulator, publisher))
print("and following waf command: {}".format(waf_script))

###
#######
faraday = SshNode(hostname=gateway_hostname, username=gateway_username,
                  verbose=verbose_ssh)

simulator = SshNode(gateway=faraday, hostname=simulator, username="root",
                    verbose=verbose_ssh)
publisher = SshNode(gateway=faraday, hostname=publisher, username="root",
                    verbose=verbose_ssh)


##########
# create an orchestration scheduler
scheduler = Scheduler()

##########
check_lease = SshJob(
    # checking the lease is done on the gateway
    node=faraday,
    critical=True,
    command=Run("rhubarbe leases --check"),
    scheduler=scheduler,
)

########## load images on the two nodes if requested

green_light = check_lease

#if args.load_images:
#    # replace green_light in this case
#    to_load = defaultdict(list)
#    to_load[image_simulator] += [args.simulator]
#    to_load[image_publisher] += [args.publisher]
#    commands = []
#    # ThierryP: this code is suboptimal as it loads images sequentially
#    for image, nodes in to_load.items():
#        commands.append(Run("rhubarbe", "load", "-i", image, *nodes))
#    commands.append(Run("rhubarbe", "wait", "-t", 120, *nodes))
#    green_light = SshJob(
#        node=faraday,
#        required=check_lease,
#        critical=True,
#        scheduler=scheduler,
#        commands=commands,
#        label="Prepare node(s) {}".format(nodes),
#    )

if args.load_images:
    # replace green_light in this case
    node_sim=args.simulator
    node_pub=args.publisher
    load_sim = SshJob(
        node=faraday,
        required=check_lease,
        critical=True,
        scheduler=scheduler,
        command=Run("rhubarbe", "load", "-i", image_simulator, node_sim),
    )
    load_pub = SshJob(
        node=faraday,
        required=check_lease,
        critical=True,
        scheduler=scheduler,
        command=Run("rhubarbe", "load", "-i", image_publisher, node_pub),
    )
    green_light = SshJob(
        node=faraday,
        required=check_lease,
        critical=True,
        scheduler=scheduler,
        command=Run("rhubarbe", "wait", "-t", 180, node_sim),
    )

##########
# setting up the data interface on both server and client
# setting up routing on server only


# following two inits should be done only when load_images is true
if args.load_images:
    init_simulator = SshJob(
        node=simulator,
        scheduler=scheduler,
        required=green_light,
        critical=True,
        commands=[
            Run("turn-on-data"),
        ],
    )

    init_publisher = SshJob(
        node=publisher,
        scheduler=scheduler,
        required=green_light,
        critical=True,
        commands=[
            Run("turn-on-data"),
        ],
    )

    init_done = (init_simulator, init_publisher)
else:
    init_done = green_light

# Run Cefore on both Producer and Simulator nodes
run_cefore_simulator = SshJob(
    node=simulator,
    scheduler=scheduler,
    required=init_done,
    critical=True,
    commands=[
        RunScript("cefore.sh", "run-cefore-sim",)
    ],
)

run_cefore_publisher = SshJob(
    node=publisher,
    scheduler=scheduler,
    required=init_done,
    critical=True,
    commands=[
        RunScript("cefore.sh", "run-cefore-publisher",)
    ],
)

cefore_ready = (run_cefore_simulator, run_cefore_publisher)

# wait before starting the simulation (cefputfile takes some time...)
settle_producer = PrintJob(
    "Wait {} seconds before starting the simulation".format(settle_delay),
    sleep=settle_delay,
    scheduler=scheduler,
    required=init_done,
    label="settling for {} seconds".format(settle_delay)
)

run_ns3 = SshJob(
    node=simulator,
    scheduler=scheduler,
    required=settle_producer,
    critical=True,
    command=RunString(waf_script),
)


pull_files = SshJob(
    node=simulator,
    scheduler=scheduler,
    critical=True,
    commands=[
        Pull (remotepaths="/root/NS3/source/ns-3-dce/files-2/tmp/OutFile",localpath="."),
    ],
    required=run_ns3,
)

##########
if dry_run:
    scheduler.export_as_pngfile("cefore-scenario")

# run the scheduler
ok = scheduler.orchestrate()

# give details if it failed
ok or scheduler.debrief()

success = ok

# producing a png file for illustration
scheduler.export_as_pngfile("cefore-scenario")

exit(0 if success else 1)
