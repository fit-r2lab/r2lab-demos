#!/usr/bin/env python3

import os

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib import Path

from asynciojobs import Scheduler, Sequence, PrintJob

from apssh import SshNode, LocalNode, SshJob
from apssh import Run, RunScript, Pull
from apssh import TimeColonFormatter

from processmap import Aggregator
from listofchoices import ListOfChoices

##########
default_gateway_hostname  = 'faraday.inria.fr'
default_gateway_username  = 'inria_radiomap'
default_run_name          = 'myradiomap'
# a fixed amount of time that we wait for,
# once all the nodes have their wireless interface configured
settle_delay              = 10
# antenna mask for each node, three values are allowed: 1, 3, 7
choices_antenna_mask      = [ '1', '3', '7']
default_antenna_mask      = 7
# PHY rate used for each node, e.g. 1, 6, 54...
choices_phy_rate          = ['1', '54']
default_phy_rate          = 1
# Tx Power for each node, for Atheros 5dBm (i.e. 500) to 14dBm (i.e. 1400)
choices_tx_power          = ['500', '1400']
default_tx_power          = 1400

# source
# http://www.radio-electronics.com/info/wireless/wi-fi/80211-channels-number-frequencies-bandwidth.php
from collections import OrderedDict
channel_frequencies = OrderedDict([
    (1,   2412), (2,   2417), (3,   2422), (4,   2427),
    (5,   2432), (6,   2437), (7,   2442), (8,   2447),
    (9,   2452), (10,  2457), (11,  2462), (12,  2467),
    (13,  2472), (14,  2484),
    (36,  5180), (40,  5200), (44,  5220), (48,  5240),
    (52,  5260), (56,  5280), (60,  5300), (64,  5320),
    (100, 5500), (104, 5520), (108, 5540), (112, 5560),
    (116, 5580), (120, 5600), (124, 5620), (128, 5640),
    (132, 5660), (136, 5680), (140, 5700), (149, 5745),
    (153, 5765), (157, 5785), (161, 5805), (165, 5825),
])
    
for k, v in channel_frequencies.items():
    channel_frequencies[k] = str(v)
choices_frequency         = list(channel_frequencies.values())
# this is channel 1
default_frequency         = 2412


# run on all nodes by default
default_node_ids = list(range(1, 38))

# ping parameters
ping_timeout      = 1
ping_size         = 64
ping_interval     = 0.015
ping_number       = 500

# wireless driver: can use only ath9k for now
wireless_driver = 'ath9k'

# convenience
def fitname(id):
    int_id = int(id)
    return "fit{:02d}".format(int_id)


def one_run(tx_power, phy_rate, antenna_mask, frequency,
            run_name=default_run_name, gateway_username=default_gateway_username,
            load_images=False, node_ids=None,
            parallel=None,
            verbose_ssh=False, verbose_jobs=False, dry_run=False,
):
    """
    Performs data acquisition on all nodes with the following settings
    
    Arguments:
        tx_power: a string among 500, 1400 
        phy_rate: a string among 1, 54
        antenna_mask: a string among 1, 3, 7
        frequency: a string like e.g. 2412
        run_name: the name for a subdirectory where all data will be kept
                  successive runs should use the same name for further visualization
        gateway_username: the Unix login name (slice name) to enter the gateway
        load_images: a boolean specifying whether nodes should be re-imaged first
        node_ids: a list of node ids to run the scenario on; strings or ints are OK;
                  defaults to the all 37 nodes i.e. the whole testbed
        parallel: a number of simulataneous jobs to run
                  1 means all data acquisition is sequential (default)
                  0 means maximum parallel
    """

    # set default for the nodes parameter
    node_ids = [int(id) for id in node_ids] if node_ids is not None else default_node_ids

    ###
    # create the logs directory based on input parameters
    root = Path(run_name)
    run_root = root / "trace-t{tx_power}-r{phy_rate}-a{antenna_mask}-f{frequency}"\
               .format(**locals())
    print("Creating log directory: {}".format(run_root))
    run_root.mkdir(parents=True, exist_ok=True)

    ########## the nodes involved
    faraday = SshNode(hostname = default_gateway_hostname, username = gateway_username,
                      formatter = TimeColonFormatter(), verbose = verbose_ssh)

    # this is a python dictionary that allows to retrieve a node object
    # from an id
    node_index = {
        id: SshNode(gateway = faraday, hostname = fitname(id), username = "root",
                    formatter = TimeColonFormatter(), verbose = verbose_ssh)
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
    
    if load_images:
        # the nodes that we **do not** use should be turned off
        # so if we have selected e.g. nodes 10 12 and 15, we will do
        # rhubarbe off -a ~10 ~12 ~15, meaning all nodes except 10, 12 and 15
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
                wireless_driver, "foobar", frequency, phy_rate, antenna_mask, tx_power
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
                Pull(remotepaths = "PING-{:02d}-{:02d}".format(i, j),
                     localpath=str(run_root)),
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
                Run("sleep 1;pkill tcpdump; sleep 1"),
                RunScript("node-utilities.sh", "process-pcap", i),
                Run("echo retrieving pcap trace and result-{i}.txt from fit{i:02d}".format(i=i)),
                Pull(remotepaths = ["/tmp/fit{}.pcap".format(i),
                                    "/tmp/result-{}.txt".format(i)],
                     localpath=str(run_root)),
            ]
        )
        for i, nodei in node_index.items()
       ]


    # xxx this is a little fishy
    # should we not just consider that the default is parallel=1 ?
    if parallel is None:
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
        # this time the value in parallel is the one
        # to use as the jobs_limit; if 0 then inch'allah
        jobs_window = parallel


    #
    # dry-run mode
    # show the scheduler using list(details=True)
    # also generate a .dot file, and attempt to
    # transform it into a .png - should work if graphviz is installed
    # but don't run anything of course
    #
    if dry_run:
        print("==================== COMPLETE SCHEDULER")
        # -n + -v = max details
        scheduler.list(details=verbose_jobs)
        suffix = "par" if parallel is not None else "seq"
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
    
    # if not in dry-run mode, let's proceed to the actual experiment
    ok = scheduler.orchestrate(jobs_window=jobs_window)
    # give details if it failed
    ok or scheduler.debrief()

    # data acquisition is done, let's aggregate results
    # i.e. compute averages
    if ok:
        post_processor = Aggregator(run_root, node_ids, antenna_mask)
        post_processor.run()

    return ok

def all_runs(tx_powers, phy_rates, antenna_masks, frequencies, *args, **kwds):
    return all(
        one_run(tx_power, phy_rate, antenna_mask, frequency, *args, **kwds)
        for tx_power in tx_powers
        for phy_rate in phy_rates
        for antenna_mask in antenna_masks
        for frequency in frequencies)

def main():
    # running with --help will show default values
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    
    parser.add_argument("-o", "--output-name", dest='run_name',
                        default=default_run_name,
                        help="the name of a subdirectory where to store results")
    parser.add_argument("-s", "--slice", default=default_gateway_username,
                        help="specify an alternate slicename")

    parser.add_argument("-t", "--tx-power", dest='tx_powers',
                        default=[default_tx_power], choices = choices_tx_power,
                        action=ListOfChoices,
                        help="specify Tx power(s)")
    parser.add_argument("-r", "--phy-rate", dest='phy_rates',
                        default=[default_phy_rate], choices = choices_phy_rate,
                        action=ListOfChoices,
                        help="specify PHY rate(s)")
    parser.add_argument("-a", "--antenna-mask", dest='antenna_masks',
                        default=[default_antenna_mask], choices = choices_antenna_mask,
                        action=ListOfChoices,
                        help="specify antenna mask(s)")
    parser.add_argument("-f", "--channel-frequency", dest='frequencies',
                        default=[default_frequency], choices=choices_frequency,
                        action=ListOfChoices,
                        help="channel frequency(ies)")
    
    parser.add_argument("-l", "--load-images", default=False, action='store_true',
                        help = "if set, load image on nodes before running the exp")
    # TP : I am turning this off, since we currently only support ath9k anyways
    #parser.add_argument("-w", "--wifi-driver", default='ath9k',
    #                    choices = ['iwlwifi', 'ath9k'],
    #                    help="specify which driver to use")
    parser.add_argument("-N", "--node-id", dest='node_ids',
                        default=default_node_ids, choices=[str(x) for x in default_node_ids],
                        action=ListOfChoices,
                        help="specify as many node ids as you want to run the scenario against")
    
    parser.add_argument("-p", "--parallel", default=None, type=int,
                        help="""run in parallel, with this value as the
                        limit to the number of simultaneous pings - default is sequential;
                        -p 0 means no limit""")
    #parser.add_argument("-T", "--ping-timeout", default=ping_timeout,
    #                    help="timeout for each individual ping")
    #parser.add_argument("-I", "--ping-interval", default=ping_interval,
    #                    help="specify time interval between pings")
    #parser.add_argument("-S", "--ping-size", default=ping_size,
    #                    help="specify packet size for each individual ping")
    #parser.add_argument("-N", "--ping-number", default=ping_number,
    #                    help="specify number of ping packets to send")
    
    parser.add_argument("-n", "--dry-run", default=False, action='store_true',
                        help="do not run anything, just print out scheduler,"
                        " and generate .dot file")
    parser.add_argument("-v", "--verbose-ssh", default=False, action='store_true',
                        help="run ssh in verbose mode")
    parser.add_argument("-d", "--debug", default=False, action='store_true',
                        help="run jobs and engine in verbose mode")
    args = parser.parse_args()
    
    print("node ids = ", args.node_ids)

    # run the experiment on all specified input values
    return all_runs(tx_powers=args.tx_powers, phy_rates=args.phy_rates,
                    antenna_masks=args.antenna_masks, frequencies=args.frequencies,
                    run_name = args.run_name,
                    gateway_username = args.slice,
                    load_images=args.load_images,
                    node_ids=args.node_ids,
                    verbose_ssh = args.verbose_ssh,
                    verbose_jobs = args.debug,
                    parallel = args.parallel,
                    dry_run = args.dry_run,
                    #ping_timeout = args.ping_timeout
                    #ping_interval = args.ping_interval
                    #ping_size = args.ping_size
                    #ping_number = args.ping_number
                    #wireless_driver   = args.wifi_driver
    )

    
##########
if __name__ == '__main__':
    overall = main()
    # return something useful to your OS
    exit(0 if overall else 1)
