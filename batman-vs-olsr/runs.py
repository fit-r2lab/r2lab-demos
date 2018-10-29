#!/usr/bin/env python3 -u

# pylint: disable=C0302, W0703, w0612

"""
Script to run batman or OLSR routing protocol on R2lab
"""

# pylint: disable=c0103, r0912, r0913, r0914, r0915

import itertools

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import shutil

from asynciojobs import Scheduler, Sequence, PrintJob

from apssh import SshNode, SshJob, LocalNode
from apssh import Run, RunScript, Pull, Push
from apssh import TimeColonFormatter
from apssh import close_ssh_in_scheduler

# helpers
#from processmap import Aggregator
from processroute import ProcessRoutes
from channels import channel_frequency

from datastore import naming_scheme, apssh_time, time_line

# the constant wireless conditions are hard-wired in datastore
# see globals TX_POWER, PHY_RATE, CHANNEL, ANTENNA_MASK,

##########
default_gateway = 'faraday.inria.fr'
default_slicename = 'inria_batman'
default_run_name = 'default-output-dir'


choices_protocols = ['olsr', 'batman']
default_protocol = ['batman']
# a fixed amount of time that we wait for,
# once all the nodes have their wireless interface configured
settle_delay_long = 40
settle_delay_shorter = 10
# antenna mask for each node, three values are allowed: 1, 3, 7

choices_antenna_mask = [1, 3, 7]
default_antenna_mask = 1
# PHY rate used for each node, e.g. 1, 6, 54...
choices_phy_rate = [1, 54]
default_phy_rate = 54
# Tx Power for each node, for Atheros 1dBm (i.e. 100) to 14dBm (i.e. 1400)
#choices_tx_power     = range(5, 15)
choices_tx_power = [1, 2, 3, 4, 5, 14]
default_tx_power = 5

# we'd rather provide a channel number than a frequency
#choices_channel      = list(channel_frequency.keys())
choices_channel = [10, 40]
default_channel = 10
# usrp-2 and n210; we use uhd_siggen --sine with an amplitude
# e.g interference = 20 -> ushd_siggen --since --amplitude 0.20
choices_interference = ['10', '15', '20', '25', '30', '35', '40', "None"]
default_interference = ["None"]

# focusing on n210 and usrp2:
# n210 = 12 15 27 30 31 36 37
# usrp2 = 5 13
choices_scrambler_id = [5, 12, 13, 15, 27, 30, 31, 36, 37]
default_scrambler_id = 5

all_node_ids = [str(i) for i in range(1, 38)]
# The 10 nodes selected by Farzaneh adapted
default_node_ids = [1, 4, 12, 15, 19, 27, 31, 33, 37]
default_src_ids = [1]
default_dest_ids = [37]

# actual ping parameters
ping_timeout = 3
ping_size = 254
ping_interval = 0.1
default_ping_messages = 100

# warmup ping parameters
warmup_ping_timeout = 5
warmup_ping_size = 64
warmup_ping_interval = 0.5
warmup_ping_messages = 60


# wireless driver: by default set to ath9k
wireless_driver = 'ath9k'
# Intel driver does not support mesh mode
#wireless_driver = 'iwlwifi'


# convenience
def fitname(node_id):
    """
    Return a valid hostname from a node number - either str or int
    """
    int_id = int(node_id)
    return f"fit{int_id:02d}"


def purgedir(path):
    """
    Delete everything in the given directory
    """
    shutil.rmtree(path)


# using * as the first parameter forces the caller to name all arguments
# which is a way to avoid stupid mistakes
# the parameters that don't have a default value
# still need to be passed of course
def one_run(*, protocol, interference,
            run_name=default_run_name, slicename=default_slicename,
            tx_power, phy_rate, antenna_mask, channel,
            load_images=False,
            node_ids=default_node_ids,
            src_ids=default_src_ids, dest_ids=default_dest_ids,
            scrambler_id=default_scrambler_id,
            ping_messages=default_ping_messages,
            tshark=False, map=False, warmup=False,
            route_sampling=False, iperf=False,
            verbose_ssh=False, verbose_jobs=False, dry_run=False,
            run_number=None):
    """
    Performs data acquisition on all nodes with the following settings

    Arguments:
        tx_power: in dBm, a string like 5, 10 or 14.
          Corresponds to the transmission power.
        phy_rate: a string among 1, 54. Correspond to the wifi rate.
        antenna_mask: a string among 1, 3, 7.
        channel: a string like e.g. 1 or 40. Correspond to the channel.
        protocol: a string among batman , olsr. Correspond to the protocol
        interference : in amplitude percentage, a string like 15 or 20.
          Correspond to the power of the noise generated in the spectrum.
          Can be either None or "None" to mean no interference.
        run_name: the name for a subdirectory where all data will be kept
          successive runs should use the same name for further visualization
        slicename: the Unix login name (slice name) to enter the gateway
        load_images: a boolean specifying whether nodes should be re-imaged first
        node_ids: a list of node ids to run the scenario against;
          strings or ints are OK;
        tshark: a boolean specifying wether we should format/parse the .pcap.
        map: a boolean specifying wether we should fetch/parse
          the route tables of the nodes.
        warmup: a boolean specifying whether we should run a ping before
          the experiment to be certain of the stabilisation on the network.
        src_ids: a list of nodes from which we will launch the ping from.
          strings or ints are OK.
        ping_messages : the number of ping packets that will be generated

    """
    # set default for the nodes parameter
    node_ids = ([int(id) for id in node_ids]
                if node_ids is not None else default_node_ids)
    src_ids = ([int(id) for id in src_ids]
               if src_ids is not None else default_src_ids)
    dest_ids = ([int(id) for id in dest_ids]
                if dest_ids is not None else default_node_ids)

    # all nodes - i.e. including sources and destinations -
    # need to run the protocol
    node_ids = list(set(node_ids).union(set(src_ids).union(set(dest_ids))))

    if interference == "None":
        interference = None

    # open result dir no matter what
    run_root = naming_scheme(
        run_name=run_name, protocol=protocol,
        interference=interference, autocreate=True)

# fix me    trace = run_root / f"trace-{%m-%d-%H-%M}"
    ref_time = apssh_time()
    trace = run_root / f"trace-{ref_time}"

    try:
        with trace.open('w') as feed:
            def log_line(line):
                time_line(line, file=feed)
            load_msg = f"{'WITH' if load_images else 'NO'} image loading"
            interference_msg = (f"interference={interference} "
                                f"from scrambler={scrambler_id}")
            nodes = " ".join(str(n) for n in node_ids)
            srcs = " ".join(str(n) for n in src_ids)
            dests = " ".join(str(n) for n in dest_ids)
            ping_labels = [
                f"PING {s} ➡︎ {d}"
                for s in src_ids
                # and on the destination
                for d in dest_ids
                if d != s
            ]

            log_line(f"output in {run_root}")
            log_line(f"trace in {trace}")
            log_line(f"protocol={protocol}")
            log_line(f"{load_msg}")
            log_line(f"{interference_msg}")
            log_line("----")
            log_line(f"Selected nodes : {nodes}")
            log_line(f"Sources : {srcs}")
            log_line(f"Destinations : {dests}")
            for label in ping_labels:
                log_line(f"{label}")
            log_line("----")
            for feature in ('warmup', 'tshark', 'map',
                            'route_sampling', 'iperf'):
                log_line(f"Feature {feature}: {locals()[feature]}")

    except Exception as exc:
        print(f"Cannot write into {trace} - aborting this run")
        print(f"Found exception {type(exc)} - {exc}")
        return False
    #
    # dry-run mode
    # just display a one-liner with parameters
    #
    prelude = "" if not dry_run else "dry_run:"
    with trace.open() as feed:
        print(f"**************** {ref_time} one_run #{run_number}:")
        for line in feed:
            print(prelude, line, sep='', end='')
    if dry_run:
        return True

    # the nodes involved
    faraday = SshNode(hostname=default_gateway, username=slicename,
                      formatter=TimeColonFormatter(), verbose=verbose_ssh)

    # this is a python dictionary that allows to retrieve a node object
    # from an id
    node_index = {
        id: SshNode(gateway=faraday, hostname=fitname(id), username="root",
                    formatter=TimeColonFormatter(), verbose=verbose_ssh)
        for id in node_ids
    }
    # extracts for sources and destinations
    src_index = {id:node for (id, node) in node_index.items()
                 if id in src_ids}
    dest_index = {id:node for (id, node) in node_index.items()
                  if id in dest_ids}

    if interference:
        node_scrambler = SshNode(
            gateway=faraday, hostname=fitname(scrambler_id), username="root",
            formatter=TimeColonFormatter(), verbose=verbose_ssh)
    # the global scheduler
    scheduler = Scheduler(verbose=verbose_jobs)

    ##########
    check_lease = SshJob(
        scheduler=scheduler,
        node=faraday,
        verbose=verbose_jobs,
        label="rhubarbe check lease",
        command=Run("rhubarbe leases --check", label="rlease"),
    )

    # load images if requested

    green_light = check_lease

    if load_images:
        # the nodes that we **do not** use should be turned off
        # so if we have selected e.g. nodes 10 12 and 15, we will do
        # rhubarbe off -a ~10 ~12 ~15, meaning all nodes except 10, 12 and 15
        negated_node_ids = [f"~{id}" for id in node_ids]
        # if interferences are requested, add the
        # id of the scrambler in the list and load the gnuradio image
        if interference:
            negated_node_ids.append(f"~{scrambler_id}")
        # copy node_ids
        load_ids = node_ids[:]
        if interference:
            load_ids.append(scrambler_id)
        # we can do these three things in parallel
        ready_jobs = [
            SshJob(node=faraday, required=green_light,
                   scheduler=scheduler, verbose=verbose_jobs,
                   command=Run("rhubarbe", "off", "-a", *negated_node_ids,
                               label="turn off unused nodes")),
            SshJob(node=faraday, required=green_light,
                   scheduler=scheduler, verbose=verbose_jobs,
                   label="load batman image",
                   command=Run("rhubarbe", "load", "-i",
                               "batman-olsr",
                               *node_ids,
                               label=f"load ubuntu on {node_ids}")),
        ]
        if interference:
            ready_jobs.append(
                SshJob(
                    node=faraday, required=green_light,
                    scheduler=scheduler, verbose=verbose_jobs,
                    label="load gnuradio image",
                    command=Run("rhubarbe", "load", "-i",
                                "batman-olsr-gnuradio",
                                scrambler_id,
                                label=f"load gnuradio on {scrambler_id}")))
        # replace green_light in this case
        green_light = SshJob(
            node=faraday, required=ready_jobs,
            scheduler=scheduler, verbose=verbose_jobs,
            label="wait for nodes to come up",
            command=Run("rhubarbe", "wait", *load_ids))

    ##########
    # setting up the wireless interface on all nodes
    #
    # provide node-utilities with the ranges/units it expects
    frequency = channel_frequency[int(channel)]
    # tx_power_in_mBm not in dBm
    tx_power_driver = tx_power * 100

    #just in case somme services failed in the previous experiment
    reset_failed_services_job = [
        SshJob(
            node=node,
            verbose=verbose_jobs,
            label="reset failed services",
            command=Run("systemctl reset-failed",
                        label="reset-failed services"))
        for id, node in node_index.items()
    ]
    reset_failed_services = Scheduler(
        *reset_failed_services_job,
        scheduler=scheduler,
        required=green_light,
        verbose=verbose_jobs,
        label="Reset failed services")
    init_wireless_sshjobs = [
        SshJob(
            node=node,
            verbose=verbose_jobs,
            label=f"init {id}",
            command=RunScript(
                "node-utilities.sh",
                f"init-ad-hoc-network-{wireless_driver}",
                wireless_driver, "foobar", frequency, phy_rate,
                antenna_mask, tx_power_driver,
                label="init add-hoc network"),
        )
        for id, node in node_index.items()]
    init_wireless_jobs = Scheduler(
        *init_wireless_sshjobs,
        scheduler=scheduler,
        required=green_light,
        verbose=verbose_jobs,
        label="Initialisation of wireless chips")

    if interference:
        # Run uhd_siggen with the chosen power
        frequency_str = f"{frequency}M"
        init_scrambler_job = SshJob(
            scheduler=scheduler,
            required=green_light,
            forever=True,
            node=node_scrambler,
            verbose=verbose_jobs,
            #TODO : If exit-signal patch is done add exit-signal=["TERM"]
            #       to this run object and call uhd_siggen directly
            commands=[RunScript("node-utilities.sh",
                                "init-scrambler",
                                label="init scrambler"),
                      Run(f"systemd-run --unit=uhd_siggen -t ",
                          f"uhd_siggen -a usrp -f {frequency}",
                          f"--sine --amplitude 0.{interference}",
                          label="systemctl start uhd_siggen")
                      ]
        )

    green_light = [init_wireless_jobs, reset_failed_services]
    # then install and run batman on fit nodes
    run_protocol_job = [
        SshJob(
            # scheduler=scheduler,
            node=node,
            label=f"init and run {protocol} on fit node {id}",
            verbose=verbose_jobs,
            # CAREFUL : These ones use sytemd-run
            #            with the ----service-type=forking option!
            command=RunScript("node-utilities.sh",
                              f"run-{protocol}",
                              label=f"run {protocol}"),
        )
        for id, node in node_index.items()]

    run_protocol = Scheduler(
        *run_protocol_job,
        scheduler=scheduler,
        required=green_light,
        verbose=verbose_jobs,
        label="init and run routing protocols")

    green_light = run_protocol

    # after that, run tcpdump on fit nodes, this job never ends...
    if tshark:

        run_tcpdump_job = [
            SshJob(
                # scheduler=scheduler_monitoring,
                node=node,
                forever=True,
                label=f"run tcpdump on fit node {id}",
                verbose=verbose_jobs,
                command=[
                    Run("systemd-run -t  --unit=tcpdump",
                        f"tcpdump -U -i moni-{wireless_driver}",
                        f"-y ieee802_11_radio -w /tmp/fit{id}.pcap",
                        label=f"tcpdump {id}")
                    ]
            )
            for id, node in node_index.items()
        ]

        run_tcpdump = Scheduler(
            *run_tcpdump_job,
            scheduler=scheduler,
            required=green_light,
            forever=True,
            verbose=verbose_jobs,
            label="Monitoring - tcpdumps")

    # let the wireless network settle
    settle_scheduler = Scheduler(
        scheduler=scheduler,
        required=green_light,
    )

    if warmup:
        # warmup pings don't need to be sequential, so let's
        # do all the nodes at the same time
        # on a given node though, we'll ping the other ends sequentially
        # see the graph for more
        warmup_jobs = [
            SshJob(
                node=node_s,
                verbose=verbose_jobs,
                commands=[
                    RunScript("node-utilities.sh",
                              "my-ping", f"10.0.0.{d}",
                              warmup_ping_timeout,
                              warmup_ping_interval,
                              warmup_ping_size,
                              warmup_ping_messages,
                              f"warmup {s} ➡︎ {d}",
                              label=f"warmup {s} ➡︎ {d}")
                    for d in dest_index.keys()
                    if s != d
                ]
            )
            # for each selected experiment nodes
            for s, node_s in src_index.items()
        ]
        warmup_scheduler = Scheduler(
            *warmup_jobs,
            scheduler=settle_scheduler,
            verbose=verbose_jobs,
            label="Warmup pings")
        settle_wireless_job2 = PrintJob(
            "Let the wireless network settle after warmup",
            sleep=settle_delay_shorter,
            scheduler=settle_scheduler,
            required=warmup_scheduler,
            label=f"settling-warmup for {settle_delay_shorter} sec")

    # this is a little cheating; could have gone before the bloc above
    # but produces a nicer graphical output
    # we might want to help asynciojobs if it offered a means
    # to specify entry and exit jobs in a scheduler
    settle_wireless_job = PrintJob(
        "Let the wireless network settle",
        sleep=settle_delay_long,
        scheduler=settle_scheduler,
        label=f"settling for {settle_delay_long} sec")

    green_light = settle_scheduler

    if iperf:
        iperf_service_jobs = [
            SshJob(
                node=node_d,
                verbose=verbose_jobs,
                forever=True,
                commands=[
                    Run("systemd-run -t --unit=iperf",
                        "iperf -s -p 1234 -u",
                        label=f"iperf serv on {d}"),
                ],
            )
            for d, node_d in dest_index.items()
        ]
        iperf_serv_sched = Scheduler(
            *iperf_service_jobs,
            verbose=verbose_jobs,
            label="Iperf Servers",
            # for a nicer graphical output
            # otherwise the exit arrow
            # from scheduler 'iperf mode'
            # to job 'settling for 60s'
            # gets to start from this box
            forever=True,
            )

        iperf_cli = [
            SshJob(
                node=node_s,
                verbose=verbose_jobs,
                commands=[
                    Run("sleep 7", label=""),
                    Run(f"iperf",
                        f"-c 10.0.0.{d} -p 1234",
                        f"-u -b {phy_rate}M -t 60",
                        f"-l 1024 > IPERF-{s:02d}-{d:02d}",
                        label=f"run iperf {s} ➡︎ {d}")
                ]
            )

            for s, node_s in src_index.items()
            for d, node_d in dest_index.items()
            if s != d
        ]
        iperf_cli_sched = Scheduler(
            Sequence(*iperf_cli),
            verbose=verbose_jobs,
            label="Iperf Clients")

        iperf_stop = [
            SshJob(node=node_d,
                   verbose=verbose_jobs,
                   label=f"Stop iperf on {d}",
                   command=Run("systemctl stop iperf"))
            for d, node_d in dest_index.items()
        ]
        iperf_stop_sched = Scheduler(
            *iperf_stop,
            required=iperf_cli_sched,
            verbose=verbose_jobs,
            label="Iperf server stop")
        iperf_fetch = [
            SshJob(node=node_s,
                   verbose=verbose_jobs,
                   command=Pull(
                       remotepaths=[f"IPERF-{s:02d}-{d:02d}"],
                       localpath=str(run_root),
                       label="fetch iperf {s} ➡︎ {d}")
                   )
            for s, node_s in src_index.items()
            for d, node_d in dest_index.items()
            if s != d
        ]
        iperf_fetch_sched = Scheduler(
            *iperf_fetch,
            required=iperf_stop_sched,
            verbose=verbose_jobs,
            label="Iperf fetch report")
        iperf_jobs = [iperf_serv_sched, iperf_cli_sched,
                      iperf_stop_sched, iperf_fetch_sched]
        iperf_sched = Scheduler(
            *iperf_jobs,
            scheduler=scheduler,
            required=green_light,
            verbose=verbose_jobs,
            label="Iperf Module")
        settle_wireless_job_iperf = PrintJob(
            "Let the wireless network settle",
            sleep=settle_delay_shorter,
            scheduler=scheduler,
            required=iperf_sched,
            label=f"settling-iperf for {settle_delay_shorter} sec")

        green_light = settle_wireless_job_iperf


    # create all the tracepath jobs from the first node in the list
    if map:
        map_jobs = [
            SshJob(
                node=node,
                label=f"Generating ROUTE file for proto {protocol} on node {id}",
                verbose=verbose_jobs,
                commands=[
                    RunScript(f"node-utilities.sh",
                              f"route-{protocol}",
                              f"> ROUTE-TABLE-{id:02d}",
                              label="get route table"),
                    Pull(remotepaths=[f"ROUTE-TABLE-{id:02d}"],
                         localpath=str(run_root),
                         label="")
                ],
            )
            for id, node in node_index.items()
        ]
        map_scheduler = Scheduler(
            *map_jobs,
            scheduler=scheduler,
            required=green_light,
            verbose=verbose_jobs,
            label="Snapshoting route files")
        green_light = map_scheduler

    if route_sampling:
        route_sampling_jobs = [
            SshJob(
                node=node,
                label=f"Route sampling service for proto {protocol} on node {id}",
                verbose=False,
                forever=True,
                commands=[
                    Push(localpaths=["route-sample-service.sh"],
                         remotepath=".", label=""),
                    Run("chmod +x route-sample-service.sh", label=""),
                    Run("systemd-run -t --unit=route-sample",
                        "/root/route-sample-service.sh",
                        "route-sample",
                        f"ROUTE-TABLE-{id:02d}-SAMPLED",
                        protocol,
                        label="start route-sampling"),
                ],
            )
            for id, node in node_index.items()
        ]
        route_sampling_scheduler = Scheduler(
            *route_sampling_jobs,
            scheduler=scheduler,
            verbose=False,
            forever=True,
            label="Route Sampling services launch",
            required=green_light)

    ##########
    # create all the ping jobs, i.e. max*(max-1)/2
    # this again is a python list comprehension
    # see the 2 for instructions at the bottom
    #
    # notice that these SshJob instances are not yet added
    # to the scheduler, we will add them later on
    # depending on the sequential/parallel strategy

    pings_job = [
        SshJob(
            node=node_s,
            verbose=verbose_jobs,
            commands=[
                Run(f"echo actual ping {s} ➡︎ {d} using {protocol}",
                    label=f"ping {s} ➡︎ {d}"),
                RunScript("node-utilities.sh", "my-ping",
                          f"10.0.0.{d}",
                          ping_timeout, ping_interval,
                          ping_size, ping_messages,
                          f"actual {s} ➡︎ {d}",
                          ">", f"PING-{s:02d}-{d:02d}",
                          label=""),
                Pull(remotepaths=[f"PING-{s:02d}-{d:02d}"],
                     localpath=str(run_root),
                     label=""),
            ],
        )
        # for each selected experiment nodes
        for s, node_s in src_index.items()
        for d, node_d in dest_index.items()
        if s != d
    ]
    pings = Scheduler(
        scheduler=scheduler,
        label="PINGS",
        verbose=verbose_jobs,
        required=green_light)

    # retrieve all pcap files from fit nodes
    stop_protocol_job = [
        SshJob(
            # scheduler=scheduler,
            node=node,
            # required=pings,
            label=f"kill routing protocol on {id}",
            verbose=verbose_jobs,
            command=RunScript(f"node-utilities.sh",
                              f"kill-{protocol}",
                              label=f"kill-{protocol}"),
        )
        for id, node in node_index.items()
    ]
    stop_protocol = Scheduler(
        *stop_protocol_job,
        scheduler=scheduler,
        required=pings,
        label="Stop routing protocols",
    )

    if tshark:
        retrieve_tcpdump_job = [
            SshJob(
                # scheduler=scheduler,
                node=nodei,
                # required=pings,
                label=f"retrieve pcap trace from fit{i:02d}",
                verbose=verbose_jobs,
                commands=[
                    Run("systemctl stop tcpdump",
                        label="stop tcpdump"),
                    #Run("systemctl reset-failed tcpdump"),
                    #RunScript("node-utilities.sh", "kill-tcpdump",
                    #          label="kill-tcpdump"),
                    Run(
                        f"echo retrieving pcap trace and result-{i}.txt from fit{i:02d}",
                        label=""),
                    Pull(remotepaths=[f"/tmp/fit{i}.pcap"],
                         localpath=str(run_root), label=""),
                ],
            )
            for i, nodei in node_index.items()
        ]
        retrieve_tcpdump = Scheduler(
            *retrieve_tcpdump_job,
            scheduler=scheduler,
            required=pings,
            label="Retrieve tcpdump",
        )
    if route_sampling:
        retrieve_sampling_job = [
            SshJob(
                # scheduler=scheduler,
                node=nodei,
                # required=pings,
                label=f"retrieve sampling trace from fit{i:02d}",
                verbose=verbose_jobs,
                commands=[
                    # RunScript("node-utilities.sh", "kill-route-sample", protocol,
                    #          label = "kill route sample"),
                    #RunScript("route-sample-service.sh", "kill-route-sample",
                    #          label="kill route sample"),
                    Run("systemctl stop route-sample",
                        label="stop route-sample"),
                    Run(
                        f"echo retrieving sampling trace from fit{i:02d}",
                        label=""),
                    Pull(remotepaths=[f"ROUTE-TABLE-{i:02d}-SAMPLED"],
                         localpath=str(run_root), label=""),
                ],
            )
            for i, nodei in node_index.items()
        ]
        retrieve_sampling = Scheduler(
            *retrieve_sampling_job,
            scheduler=scheduler,
            required=pings,
            verbose=verbose_jobs,
            label="Stop & retrieve route sampling",
            )
    if tshark:
        parse_pcaps_job = [
            SshJob(
                # scheduler=scheduler,
                node=LocalNode(),
                # required=retrieve_tcpdump,
                label=f"parse pcap trace {run_root}/fit{i}.pcap",
                verbose=verbose_jobs,
                #commands = [RunScript("parsepcap.sh", run_root, i)]
                command=Run("tshark", "-2", "-r",
                            f"{run_root}/fit{i}.pcap",
                            "-R",
                            f"'(ip.dst==10.0.0.{i} && icmp) && radiotap.dbm_antsignal'",
                            "-Tfields",
                            "-e", "'ip.src'",
                            "-e" "'ip.dst'",
                            "-e", "'radiotap.dbm_antsignal'",
                            ">", f"{run_root}/result-{i}.txt",
                            label=f"parsing pcap from {i}"),
            )
            for i in node_ids
        ]
        parse_pcaps = Scheduler(
            *parse_pcaps_job,
            scheduler=scheduler,
            required=retrieve_tcpdump,
            label="Parse pcap",
        )

    if interference:
        kill_uhd_siggen = SshJob(
            scheduler=scheduler,
            node=node_scrambler,
            required=pings,
            label=f"killing uhd_siggen on the scrambler node {scrambler_id}",
            verbose=verbose_jobs,
            commands=[Run("systemctl", "stop", "uhd_siggen"),
                      #Run("systemctl reset-failed tcpdump"),
                      ],
        )
        kill_2_uhd_siggen = SshJob(
            scheduler=scheduler,
            node=faraday,
            required=kill_uhd_siggen,
            label=f"turning off usrp on the scrambler node {scrambler_id}",
            verbose=verbose_jobs,
            command=Run("rhubarbe", "usrpoff", scrambler_id),
        )

    pings.add(Sequence(*pings_job))
    # for running sequentially we impose no limit on the scheduler
    # that will be limitied anyways by the very structure
    # of the required graph

    # safety check

    scheduler.export_as_pngfile(run_root / "experiment-graph")
    if dry_run:
        scheduler.list()
        return True

    # if not in dry-run mode, let's proceed to the actual experiment
    ok = scheduler.run()  # jobs_window=jobs_window)

    # close all ssh connections
    close_ssh_in_scheduler(scheduler)


    # give details if it failed
    if not ok:
        scheduler.debrief()
        scheduler.export_as_pngfile("debug")
    if ok and map:
        time_line("Creation of MAP files")
        post_processor = ProcessRoutes(run_root, src_ids, node_ids)
        post_processor.run()
    if ok and route_sampling:
        time_line("Creation of ROUTE SAMPLING files")
        post_processor = ProcessRoutes(run_root, src_ids, node_ids)
        post_processor.run_sampled()
    # data acquisition is done, let's aggregate results
    # i.e. compute averages
    #if ok and tshark:
        #post_processor = Aggregator(run_root, node_ids, antenna_mask)
        #post_processor.run()

    time_line("one_run done")
    return ok


# same as for interference, we force all arguments to be named
def all_runs(*args, interferences, protocols,
             tx_powers, phy_rates, antenna_masks, channels,
             **kwds):
    """
    calls one_run with the cartesian product of
    protocols, interferences,
    tx_powers, phy_rates, antenna_masks and channels,
    that are expected to be lists of strings

    All other arguments to one_run may/must be specified as well

    Example:
        all_runs(protocols=['olsr'],
                 interferences=[None],
                 tx_powers=[5, 14],
                 phy_rates=[1],
                 antenna_masks=[1],
                 channels=[1, 40],
                 ...)
        will call one_run exactly 4 times
    """
    # we don't use all() on a list comprehension because
    # (*) we want to run all configs regardless of a failure, and
    #     all() is lazy and would stop at the first failure
    # (*) we need to set load_images to false after the first run
    overall = True
    if interferences is None:
        interferences = ["None"]
    iterator = itertools.product(protocols, interferences, tx_powers,
                                 phy_rates, antenna_masks, channels)
    for (run_number, (protocol, interference, tx_power,
                      phy_rate, antenna_mask, channel)) \
            in enumerate(iterator, 1):
        if not one_run(
                protocol=protocol,
                interference=interference,
                tx_power=tx_power,
                phy_rate=phy_rate,
                antenna_mask=antenna_mask,
                channel=channel,
                run_number=run_number,
                *args, **kwds):
            overall = False
        # make sure images will get loaded only once
        kwds['load_images'] = False
    return overall


def main():
    """
    Command-line frontend - offers primarily all options to all_runs

    Options that build the cartesian product that all_runs operate upon
      primarily are cumulative
    """
    # running with --help will show default values
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "-s", "--slice", dest='slicename', default=default_slicename,
        help="specify your slicename (reservation needed)")
    parser.add_argument(
        "-l", "--load-images", default=False, action='store_true',
        help="if set, load image on nodes before running the experiment")
    parser.add_argument(
        "-o", "--output-name", dest='run_name',
        default=default_run_name,
        help="the name of a subdirectory where to store results")

    parser.add_argument(
        "-p", "--protocol", dest='protocol', metavar='protocol',
        default=default_protocol, choices=choices_protocols,
        nargs='+',
        help=f"specify the WMN protocols you want to use,"
             f" among {set(choices_protocols)}")

    parser.add_argument(
        "-i", "--interference", dest='interference', metavar='interference',
        default=default_interference, choices=choices_interference,
        nargs='+', type=str,
        help=f"gain (dBm) for the white gaussian noise"
             f" generated from scrambler node,"
             f" among {' '.join(choices_interference)}")

    parser.add_argument(
        "-N", "--node", dest='node_ids', metavar='routing-node',
        default=default_node_ids, choices=all_node_ids,
        nargs='+',
        help=f"specify as many nodes as you want to be involved in the scenario;"
             f" these will be on and run the routing protocol;"
             f" source and destination nodes are automatically added.")
    parser.add_argument(
        "-S", "--source", dest='src_ids', metavar='source-node',
        default=default_src_ids, choices=all_node_ids,
        nargs='+',
        help=f"specify the nodes sources of the pings,"
             f" among {set(default_node_ids)}")
    parser.add_argument(
        "--all-sources", dest='all_src', default=False, action='store_true',
        help="if set, all nodes in the experiment are used as sources"
    )
    parser.add_argument(
        "-D", "--destination", dest='dest_ids', metavar='dest-node',
        default=default_dest_ids, choices=all_node_ids,
        nargs='+',
        help="specify as many node ids as you want to be the destination of the ping")
    parser.add_argument(
        "--all-destinations", dest='all_dest', default=False, action='store_true',
        help="if set, all nodes in the experiment are used as destinations"
    )
    parser.add_argument(
        "--scrambler", dest='scrambler_id', metavar='scrambler-node',
        default=default_scrambler_id, choices=all_node_ids,
        help="location of the scrambler - can't be used in the experiment though")

    parser.add_argument(
        "-t", "--tx-power", dest='tx_powers', metavar='tx-power',
        default=[default_tx_power], choices=choices_tx_power,
        nargs='+', type=int,
        help=f"specify Tx power(s) among {set(choices_tx_power)}")
    parser.add_argument(
        "-r", "--phy-rate", dest='phy_rates', metavar='phy-rate',
        default=[default_phy_rate], choices=choices_phy_rate,
        nargs='+', type=int,
        help=f"specify PHY rate(s), among {set(choices_phy_rate)}")
    parser.add_argument(
        "-a", "--antenna-mask", dest='antenna_masks', metavar='antenna-mask',
        default=[default_antenna_mask], choices=choices_antenna_mask,
        nargs='+', type=int,
        help=f"specify antenna mask(s), among {set(choices_antenna_mask)}")
    parser.add_argument(
        "-c", "--channel", dest='channels', metavar='channel',
        default=[default_channel], choices=choices_channel,
        nargs='+', type=int,
        help=f"channel(s), among {set(choices_channel)}")

    parser.add_argument(
        "-m", "--ping-messages", default=default_ping_messages,
        help="specify number of ping packets to send")

    # POST PROCESSING OPTIONS
    parser.add_argument(
        "--warmup", default=False, action='store_true',
        help="do a ping as a warmup to try to stabilise routes and then "
             "settle again before getting routes and register results")
    parser.add_argument(
        "--iperf", default=False, action='store_true',
        help="[BONUS] do an iperf for the sources and destinations ")
    parser.add_argument(
        "--map", default=False, action='store_true',
        help="add results of the trace-path command from the first selected node")
    parser.add_argument(
        "--route-sampling", default=False, action='store_true',
        help="observe and recolt the routing table over time during the experiment")
    parser.add_argument(
        "--tshark", default=False, action='store_true',
        help="parse pcap files to get RSSIs for each nodes"
             " (Warning: you need to have tshark installed on your machine)")
    parser.add_argument(
        "--all-extras", default=False, action='store_true',
        help="enable 4 extra features: warmup, iperf, "
             "map and route-sampling; tshark is not included "
             " because it involves a huge data volume, "
             " and thus performs MUCH more slowly."
    )

    parser.add_argument(
        "-n", "--dry-run", default=False, action='store_true',
        help="do not run anything, just print out scheduler,"
        " and generate .dot file")
    parser.add_argument(
        "-v", "--verbose-ssh", default=False, action='store_true',
        help="run ssh in verbose mode")
    parser.add_argument(
        "-d", "--debug", default=False, action='store_true',
        help="run jobs and engine in verbose mode")

    args = parser.parse_args()

    # special 'all' options
    if args.all_src:
        args.src_ids = args.node_ids
    if args.all_dest:
        args.dest_ids = args.node_ids
    if args.all_extras:
        for feature in ( #'tshark', # tshark really involves too big a volume
                'map', 'warmup', 'iperf', 'route_sampling'):
            setattr(args, feature, True)

    return all_runs(
        protocols=args.protocol,
        interferences=args.interference,
        tx_powers=args.tx_powers, phy_rates=args.phy_rates,
        antenna_masks=args.antenna_masks, channels=args.channels,
        run_name=args.run_name,
        slicename=args.slicename,
        load_images=args.load_images,
        node_ids=args.node_ids,
        src_ids=args.src_ids,
        dest_ids=args.dest_ids,
        scrambler_id=args.scrambler_id,
        ping_messages=args.ping_messages,

        tshark=args.tshark,
        map=args.map,
        warmup=args.warmup,
        route_sampling=args.route_sampling,
        iperf=args.iperf,

        verbose_ssh=args.verbose_ssh,
        verbose_jobs=args.debug,
        dry_run=args.dry_run,
    )


##########
if __name__ == '__main__':
    # return something useful to your OS
    exit(0 if main() else 1)
