#!/usr/bin/env python3

from argparse import ArgumentParser

from asynciojobs import Scheduler, PrintJob

from apssh import SshNode, LocalNode, SshJob
from apssh import Run, RunString, Pull

def fitname(node_id):
    """
    Return a valid hostname from a node number - either str or int
    """
    int_id = int(node_id)
    return "fit{:02d}".format(int_id)

##########
gateway_hostname  = 'faraday.inria.fr'
gateway_username  = 'inria_cefore'
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

parser = ArgumentParser()
parser.add_argument("-s", "--slice", default=gateway_username,
                    help="specify an alternate slicename, default={}"
                         .format(gateway_username))
parser.add_argument("-S", "--simulator", default=def_simulator,
                    help="id of the node that runs ns-3/dce, default={}".format(def_simulator))
parser.add_argument("-P", "--publisher", default=def_publisher,
                    help="id of the node that runs the publisher, default={}".format(def_publisher))
parser.add_argument("-v", "--verbose-ssh", default=False, action='store_true',
                    help="run ssh in verbose mode")
parser.add_argument("-l", "--load-images", default=False, action='store_true',
                    help = "enable to load the default image on nodes before the exp")
args = parser.parse_args()

gateway_username = args.slice
verbose_ssh = args.verbose_ssh


waf_script = "cd NS3/source/ns-3-dce; ./waf --run dce-test-twoRealNodes-wifiSimConsumers-onlyTap-v1"

#waf_script = """ cd ns-3-dev; ./waf --run "scratch/olsr --remote={} --local={} --dstnNode={} --stopTime={} --multicast=true" """.format(args.server,args.client,target_node,duration)


simulator, publisher = fitname(args.simulator), fitname(args.publisher)



print("Running scenario with ns-3/dce running at {} and publisher running at {}".format(simulator,publisher))
print("and following waf command: {}".format(waf_script))

###
#######
faraday = SshNode(hostname = gateway_hostname, username = gateway_username,
                  verbose = verbose_ssh)

simulator = SshNode(gateway = faraday, hostname = simulator, username = "root",
                    verbose = verbose_ssh)
publisher = SshNode(gateway = faraday, hostname = publisher, username = "root",
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
            Run("rhubarbe", "load", "-i", image_simulator, args.simulator),
            Run("rhubarbe", "load", "-i", image_publisher, args.publisher),
            Run("rhubarbe", "wait", "-t",  120, args.simulator, args.publisher),
        ]
    )

##########
# setting up the data interface on both server and client
# setting up routing on server only


simulator_init_script = """
cefnetdstop
cefnetdstart
"""

publisher_init_script = """
cefnetdstop
csmgrdstop
csmgrdstart
cefnetdstart
cefputfile ccn:/realRemote/test ./big_buck_bunny.mp4
"""


# following two inits should be done only when load_images is true
if args.load_images:
    init_simulator = SshJob(
        node = simulator,
        scheduler = scheduler,
        required = green_light,
        commands = [
            Run("turn-on-data"),
            RunString(simulator_init_script, label="start Cefore daemon at the simulator node"),
        ],
    )

    init_publisher = SshJob(
        node = publisher,
        scheduler = scheduler,
        required = green_light,
        commands = [
            Run("turn-on-data"),
            RunString(publisher_init_script, label="initializations at the publisher node"),
        ],
    )

if args.load_images:
    init_done = (init_simulator,init_publisher)
else:
    init_done = green_light

# wait before starting the simulation (cefputfile takes some time...)
settle_producer = PrintJob(
    "Wait {} seconds before starting the simulation".format(settle_delay),
    sleep=settle_delay,
    scheduler=scheduler,
    required=init_done,
    label="settling for {} seconds".format(settle_delay)
)

run_ns3 = SshJob(
    node = simulator,
    scheduler = scheduler,
    command = RunString(waf_script, label="Run the ns-3/DCE script"),
    required = settle_producer,
)


pull_files = SshJob(
    node = simulator,
    scheduler = scheduler,
    commands = [
        Pull (remotepaths="/root/NS3/source/ns-3-dce/files-2/tmp/OutFile",localpath="."),
    ],
    required = run_ns3,
    label="Retrieve the output file from simulated node 2",
)

##########
# run the scheduler
ok = scheduler.orchestrate()

# give details if it failed
ok or scheduler.debrief()

success = ok 

# producing a png file for illustration
scheduler.export_as_pngfile("cefore-scenario")

exit(0 if success else 1)

