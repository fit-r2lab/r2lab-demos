#!/usr/bin/env python3

import os

from argparse import ArgumentParser

from asynciojobs import Scheduler, Sequence, PrintJob

from apssh import SshNode, LocalNode, SshJob
from apssh import Run, RunScript, Pull
from apssh import TimeColonFormatter


##########
gateway_hostname  = 'faraday.inria.fr'
gateway_username  = 'inria_naoufal.mesh'
# a fixed amount of time that we wait for once all the nodes
# have their wireless interface configured
settle_delay      = 10
# antenna mask for each node, three values are authorized: 1, 3, 7
antenna_mask      = 7
# PHY rate used for each node, e.g. 1, 6, 54...
phy_rate          = 1
# Channel frequency used for each node
channel_frequency = 2412
# Tx Power for each node, for Atheros 5dBm (i.e. 500) to 14dBm (i.e. 1400)
tx_power          = 1400
#
# ping parameters
#
ping_timeout      = 1
ping_size         = 64
ping_interval     = 0.008
ping_number       = 100

parser = ArgumentParser()
parser.add_argument("-s", "--slice", default=gateway_username,
                    help="specify an alternate slicename, default={}"
                         .format(gateway_username))
parser.add_argument("-l", "--load-images", default=False, action='store_true',
                    help = "enable to load the default image on nodes before the exp")
parser.add_argument("-w", "--wifi-driver", default='ath9k',
                    choices = ['iwlwifi', 'ath9k'],
                    help="specify which driver to use")
parser.add_argument("-m", "--max", default=5, type=int,
                    help="will run on all nodes between 1 and this number")

parser.add_argument("-p", "--parallel", default=None,type=int,
                    help="""run in parallel, with this value as the
                    limit to the number of simultaneous pings - -p 0 means no limit""")
parser.add_argument("-a", "--antenna-mask", default=antenna_mask,choices = ['1','3','7'],
                    help="specify antenna mask for each node - default={}".format(antenna_mask))
parser.add_argument("-r", "--phy-rate", default=phy_rate,
                    help="specify PHY rate - default={}".format(phy_rate))
parser.add_argument("-f", "--channel-frequency", default=channel_frequency,
                    help="specify the channel frequency for each node - default={}".format(channel_frequency))
parser.add_argument("-T", "--tx-power", default=tx_power,
                    help="specify Tx power - default={}".format(tx_power))
parser.add_argument("-t", "--ping-timeout", default=ping_timeout,
                    help="specify timeout for each individual ping - default={}".format(ping_timeout))
parser.add_argument("-i", "--ping-interval", default=ping_interval,
                    help="specify time interval between ping - default={}".format(ping_interval))
parser.add_argument("-S", "--ping-size", default=ping_size,
                    help="specify packet size for each individual ping - default={}".format(ping_size))
parser.add_argument("-N", "--ping-number", default=ping_number,
                    help="specify number of ping to send - default={}".format(ping_number))

parser.add_argument("-n", "--dry-run", default=False, action='store_true',
                    help="do not run anything, just print out scheduler, and generate .dot file")
parser.add_argument("-v", "--verbose-ssh", default=False, action='store_true',
                    help="run ssh in verbose mode")
parser.add_argument("-d", "--debug", default=False, action='store_true',
                    help="run jobs and engine in verbose mode")
args = parser.parse_args()

max = args.max
gateway_username = args.slice
verbose_ssh = args.verbose_ssh
verbose_jobs = args.debug
ping_timeout = args.ping_timeout
ping_interval = args.ping_interval
ping_size = args.ping_size
ping_number = args.ping_number
wireless_driver   = args.wifi_driver
antenna_mask = args.antenna_mask
phy_rate = args.phy_rate
channel_frequency = args.channel_frequency
tx_power = args.tx_power

# convenience
def fitname(id):
    return "fit{:02d}".format(id)


###
# create the logs dirctory base don input parameters
dirlogs = "trace-T{}-r{}-a{}-t{}-i{}-S{}-N{}".format(tx_power,phy_rate,antenna_mask,ping_timeout,ping_interval,ping_size, ping_number)
print("Creating log directory: "+dirlogs)
os.makedirs(dirlogs, exist_ok=True)

### the list of (integers) that hold node numbers, starting at 1
# of course it would make sense to come up with a less rustic way of
# selecting target nodes
node_ids = range(1, max+1)


########## the nodes involved
faraday = SshNode(hostname = gateway_hostname, username = gateway_username,
formatter=TimeColonFormatter(), verbose = verbose_ssh)

# this is a python dictionary that allows to retrieve a node object
# from an id
node_index = {
    id: SshNode(gateway = faraday,
                hostname = fitname(id),
                username = "root",
                formatter=TimeColonFormatter(),
                verbose = verbose_ssh)
    for id in node_ids
}

########## the global scheduler
scheduler = Scheduler(verbose = verbose_jobs)

##########
check_lease = SshJob(
    scheduler = scheduler,
    node = faraday,
    verbose = verbose_jobs,
    critical = True,
    command = Run("rhubarbe leases --check"),
)

########## load images if requested

green_light = check_lease

if args.load_images:
    negated_node_ids = [ "~{}".format(id) for id in node_ids ]
    # replace green_light in this case
    green_light = SshJob(
        node = faraday,
        required = check_lease,
        critical = True,
        scheduler = scheduler,
        verbose = verbose_jobs,
        commands = [
            Run("rhubarbe", "off", "-a", *negated_node_ids),
            Run("rhubarbe", "load", "-i", "ubuntu", *node_ids),
            Run("rhubarbe", "wait", *node_ids)
        ]
    )

##########
# setting up the wireless interface on all nodes
#
# this is a python feature known as a list comprehension
# we just create as many SshJob instances as we have
# (id, SshNode) couples in node_index
# and gather them all in init_wireless_jobs
# they all depend on green_light
init_wireless_jobs = [
    SshJob(
        scheduler = scheduler,
        required = green_light,
        node = node,
        verbose = verbose_jobs,
        label = "init {}".format(id),
        command = RunScript(
            "node-utilities.sh", "init-ad-hoc-network",
            wireless_driver, "foobar", channel_frequency, phy_rate, antenna_mask, tx_power
        ))
    for id, node in node_index.items() ]


######### then run tcpdump on fit nodes, this job never ends...
run_tcpdump = [
    SshJob(
        scheduler = scheduler,
        node = node,
        required = init_wireless_jobs,
        label = "run tcpdump on fit nodes",
        verbose = verbose_jobs,
        commands = [
            Run("echo run tcpdump on fit{:02d}".format(i)),
#            Run("tcpdump -U -i moni0 -v icmp -y ieee802_11_radio -w /tmp/fit{}.pcap".format(i))
            Run("tcpdump -U -i moni0  -y ieee802_11_radio -w /tmp/fit{}.pcap".format(i))
        ]
    )
    for i, node in node_index.items()
]


########## let the wireless network settle
settle_wireless_job = PrintJob(
    "Let the wireless network settle",
    sleep = settle_delay,
    scheduler = scheduler,
    required = init_wireless_jobs,
    label = "settling")




##########
# create all the ping jobs, i.e. max*(max-1)/2
# this again is a python list comprehension
# see the 2 for instructions at the bottom
#
# notice that these SshJob instances are not yet added
# to the scheduler, we will add them later on
# depending on the sequential/parallel strategy

pings = [
    SshJob(
        node = nodei,
        required = settle_wireless_job,
        label = "ping {} -> {}".format(i, j),
        verbose = verbose_jobs,
        commands = [
            Run("echo {} '->' {}".format(i, j)),
            RunScript("node-utilities.sh", "my-ping",
                      "10.0.0.{}".format(j), ping_timeout, ping_interval,
                      ping_size, ping_number,
                      ">", "PING-{:02d}-{:02d}".format(i, j)),
            Pull(remotepaths = "PING-{:02d}-{:02d}".format(i, j), localpath="./"+dirlogs),
        ]
    )
    # looping on the source
    for i, nodei in node_index.items()
    # and on the destination
    for j, nodej in node_index.items()
    # and keep only half of the couples
    if j > i
]

# retrieve all pcap files from fit nodes
retrieve_tcpdump = [
    SshJob(
        scheduler = scheduler,
        node = nodei,
        required = pings,
        label = "retrieve pcap trace from fit{:02d}".format(i),
        verbose = verbose_jobs,
        commands = [
            Run("sleep 2;pkill tcpdump; sleep 1"),
            RunScript("node-utilities.sh", "process-pcap", i),
            Run("echo retrieve pcap trace from fit{:02d}".format(i)),
            Pull(remotepaths = "/tmp/fit{}.pcap".format(i), localpath="./"+dirlogs),
            Run("echo retrieve result{}.txt file".format(i)),
            Pull(remotepaths = "/tmp/result-{}.txt".format(i), localpath="./"+dirlogs),
        ]
    )
    for i, nodei in node_index.items()
]



if args.parallel is None:
    # with the sequential strategy, we just need to
    # create a Sequence out of the list of pings
    # Sequence will add the required relationships
    scheduler.add(Sequence(*pings, scheduler=scheduler))
    # for running sequentially we impose no limit on the scheduler
    # that will be limitied anyways by the very structure
    # of the required graph
    jobs_window = None
else:
    # with the parallel strategy
    # we just need to insert all the ping jobs
    # as each already has its required OK
    scheduler.update(pings)
    # this time the value in args.parallel is the one
    # to use as the jobs_limit; if 0 then inch'allah
    jobs_window = args.parallel


# Finally - i.e. when traces are retrieved from all nodes
# we can resume postprocessing of traces on the corresponding directory
SshJob(
    node = LocalNode(),
    scheduler = scheduler,
    required = retrieve_tcpdump,
    verbose = verbose_jobs,
    commands = [
        Run("echo Run post-process.py on {}".format(dirlogs)),
        Run("cd {};".format(dirlogs), "python3 ../post-process.py -m {} ".format(max), 
            " -a {}".format(antenna_mask)),
    ]
)

#
# dry-run mode
# show the scheduler using list(details=True)
# also generate a .dot file, and attempt to
# transform it into a .png - should work if graphviz is installed
# but don't run anything of course
#
if args.dry_run:
    print("==================== COMPLETE SCHEDULER")
    # -n + -v = max details
    scheduler.list(details=verbose_jobs)
    suffix = "par" if args.parallel else "seq"
    if args.load_images:
        suffix += "-load"
    filename = "heatmap-{}-{}".format(suffix, args.max)
    print("Creating dot file: {filename}.dot".format(filename=filename))
    scheduler.export_as_dotfile(filename+".dot")
    # try to run dot
    command = "dot -Tpng -o {filename}.png {filename}.dot".format(filename=filename)
    print("Trying to run dot to create {filename}.png".format(filename=filename))
    retcod = os.system(command)
    if retcod == 0:
        print("{filename}.png OK".format(filename=filename))
    else:
        print("Could not create {filename}.png - do you have graphviz installed ?"
              .format(filename=filename))
    # in dry-run mode we are done
    exit(0)

ok = scheduler.orchestrate(jobs_window=jobs_window)
# give details if it failed
ok or scheduler.debrief()

# return something useful to your OS
exit(0 if ok else 1)
