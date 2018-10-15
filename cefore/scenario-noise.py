#!/usr/bin/env python3

# pylint: disable=c0103

from collections import defaultdict

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from asynciojobs import Scheduler, PrintJob

from apssh import SshNode, LocalNode, SshJob, Service
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
# use the -s option to change
gateway_username  = 'inria_cefore'

# Default fit id for the node that runs ns-3/dce
def_simulator = 1
# Default fit id for the node that runs the publisher
def_publisher = 37
# Default fit id for the node that runs the noise generator
def_generator = 12

# Waiting time for producer to settle
settle_delay = 15

# Images names for server and client
image_simulator = "dce-ap"
image_publisher = "cefore"
image_generator = "gnuradio"

parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
parser.add_argument("-s", "--slice", default=gateway_username,
                    help="specify an alternate slicename")
parser.add_argument("-S", "--simulator", default=def_simulator,
                    help="id of the node that runs ns-3/dce")
parser.add_argument("-P", "--publisher", default=def_publisher,
                    help="id of the node that runs the publisher")
parser.add_argument("-G", "--generator", default=def_generator,
                    help="id of the node that runs the noise generator")
parser.add_argument("-v", "--verbose-ssh", default=False, action='store_true',
                    help="run ssh in verbose mode")
parser.add_argument("-n", "--dry-run", action='store_true', default=False)
parser.add_argument("-l", "--load-images", default=False, action='store_true',
                    help="load default image nodes before running the exp")
args = parser.parse_args()

gateway_username = args.slice
verbose_ssh = args.verbose_ssh
dry_run = args.dry_run
node_sim = args.simulator
node_pub = args.publisher
node_generator = args.generator


waf_script = "cd NS3/source/ns-3-dce; ./waf --run dce-test-twoRealNodes-wifiSimConsumers-onlyTap-v1"

#waf_script = """ cd ns-3-dev; ./waf --run "scratch/olsr --remote={} --local={} --dstnNode={} --stopTime={} --multicast=true" """.format(args.server,args.client,target_node,duration)


simulator, publisher, generator = fitname(args.simulator), fitname(args.publisher), fitname(args.generator)


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

generator = SshNode(gateway=faraday, hostname=generator, username="root",
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

if args.load_images:
    # replace green_light in this case
    load_sim = SshJob(
        node=faraday,
        required=check_lease,
        critical=True,
        scheduler=scheduler,
        commands=[
            Run("rhubarbe", "load", "-i", image_simulator, node_sim),
            Run("rhubarbe", "wait", node_sim),
        ],
    )
    load_pub = SshJob(
        node=faraday,
        required=check_lease,
        critical=True,
        scheduler=scheduler,
        commands=[
            Run("rhubarbe", "load", "-i", image_publisher, node_pub),
            Run("rhubarbe", "wait", node_pub),
        ],
    )
    load_generator = SshJob(
        node=faraday,
        required=check_lease,
        critical=True,
        scheduler=scheduler,
        commands=[
            Run("rhubarbe", "usrpoff", node_generator),
            Run("rhubarbe", "load", "-i", image_generator, node_generator),
            Run("rhubarbe", "usrpon", node_generator),
            Run("rhubarbe", "wait", node_generator),
        ],
    )
    turn_off_others = SshJob(
        node=faraday,
        scheduler=scheduler,
        required=check_lease,
        command=Run("rhubarbe off --all ~{} ~{} ~{}"
                    .format(node_pub, node_sim, node_generator)
                    ),
    )
    green_light = (load_pub, load_sim, load_generator, turn_off_others)

# turns out that the daemons - at least csmgr -
# somehow rely on the USER environment variable
# but this is not implicitly defined when using systemd
# so for now we define it explicitly here
# this *might* become a feature of the Service class in the future
environ = {
    'USER': 'root'
}

# in this order, as cefnet requires csmgr
csmgr_service = Service("csmgrd", service_id="csmgr",
                        environ=environ)
cefnet_service = Service("cefnetd", service_id="cefnet",
                        environ=environ)

#siggen_service = Service("uhd_siggen --gaussian -f 2425M -g 10", 
#                         service_id="uhd_siggen", verbose=True)


# Run Cefore on both Producer and Simulator nodes
com_pub="echo ccn:/realRemote udp 10.0.0.{} > /usr/local/cefore/cefnetd.fib".format(node_pub)
run_simulator_daemons = SshJob(
    node=simulator,
    scheduler=scheduler,
    required=green_light,
    critical=True,
    commands=[
        Run(com_pub, verbose=True, label="Add to FIB ccn:/realRemote udp 10.0.0.{}".format(node_pub)),
        RunScript("cefore.sh", "configure-ip-ap", node_sim),
        csmgr_service.start_command(),
        cefnet_service.start_command(),
    ],
)

run_publisher_daemons = SshJob(
    node=publisher,
    scheduler=scheduler,
    required=green_light,
    critical=True,
    commands=[
        RunScript("cefore.sh", "connect-to-ap", node_pub),
        csmgr_service.start_command(),
        Run("sleep 2"),
        cefnet_service.start_command(),
        Run("sleep 2"),
    ],
)

switch_on_usrp = SshJob(
    # switch on usrp
    node=faraday,
    scheduler=scheduler,
    required=green_light,
    commands=[
        Run("rhubarbe", "usrpon", node_generator),
        Run("sleep 5"),
    ],
)


xterm_script= "(xterm -fn -*-fixed-medium-*-*-*-20-*-*-*-*-*-*-* -bg wheat -geometry 90x10; ret=$?; if [ $ret -eq '140' ]; then echo 'return 140'; exit 0; fi; exit $ret)"
prepare_generator_job = [
    SshJob(
        node=generator,
        forever=True,
        commands=[
            RunScript("cefore.sh", "enable-usrp-ethernet", verbose=True),
#            Run("xterm -fn -*-fixed-medium-*-*-*-20-*-*-*-*-*-*-*"
#                " -bg {} -geometry 90x10".format("wheat"),
#                x11=True),
            Run(xterm_script, x11=True),
        ],
    )
]
prepare_generator = Scheduler(*prepare_generator_job,
                               scheduler=scheduler,
                               required=sitch_on_usrp,
                               label="Set up USRP and display X11 window for uhd_siggen on fit node {}".format(node_generator))


all_nodes_ready = (run_simulator_daemons, run_publisher_daemons)

put_media_on_publisher = SshJob(
    node=publisher,
    scheduler=scheduler,
    required=all_nodes_ready,
    critical=True,
    commands=[
        RunScript("cefore.sh", "put-media-on-publisher",)
    ],
)


# wait before starting the simulation (cefputfile takes some time...)
##settle_producer = PrintJob(
#    "Wait {} seconds before starting the simulation".format(settle_delay),
#    sleep=settle_delay,
#    scheduler=scheduler,
#    required=green_light,
#    label="settling for {} seconds".format(settle_delay)
#)

run_ns3 = SshJob(
    node=simulator,
    scheduler=scheduler,
    required=put_media_on_publisher,
    critical=True,
    commands=[
        RunString(waf_script, label='waf_script'),
        Pull(
            remotepaths="/root/NS3/source/ns-3-dce/files-2/tmp/OutFile",
            localpath="."),
    ],
)

# epilogue
for node in simulator, publisher:
    SshJob(
        # shutdown services
        node=node,
        scheduler=scheduler,
        required=run_ns3,
        commands=[
            cefnet_service.stop_command(),
            csmgr_service.stop_command(),
            ]
)

kill_generator_script="pkill --signal SIGUSR2 xterm; echo 'pkill xterm'"

SshJob(
    # shutdown uhd_siggen service
    node=generator,
    scheduler=scheduler,
    required=run_ns3,
    command = RunString(kill_generator_script, label="Exit noise generator window"),
)

SshJob(
    # switch off usrp
    node=faraday,
    scheduler=scheduler,
    required=run_ns3,
    command=Run("rhubarbe", "usrpoff", node_generator),
)



##########
scheduler.export_as_pngfile("cefore-scenario")
if args.dry_run:
    exit(0)

# run the scheduler
scheduler.verbose = True
scheduler.list()

try:
    success = scheduler.run()
except KeyboardInterrupt:
    print("OOPS ! ")
    scheduler.debrief()
    exit(1)

# give details if it failed
success or scheduler.debrief()

exit(0 if success else 1)
