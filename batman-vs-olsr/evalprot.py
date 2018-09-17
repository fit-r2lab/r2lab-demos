#!/usr/bin/env python3

"""
Script to run batman or OLSR routing protocol on R2lab
"""

# pylint: disable=c0103, r0912, r0913, r0914, r0915

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib import Path
import shutil

from asynciojobs import Scheduler, Sequence, PrintJob

from apssh import SshNode, SshJob, LocalNode
from apssh import Run, RunScript, Pull, Push
from apssh import TimeColonFormatter

# helpers
#from processmap import Aggregator
from processroute import ProcessRoutes
from channels import channel_frequency

##########
default_gateway = 'faraday.inria.fr'
default_slicename = 'inria_batman'
default_run_name = 'exp-data'


choices_protocols = ['olsr', 'batman']
default_protocol = ['batman']
# a fixed amount of time that we wait for,
# once all the nodes have their wireless interface configured
settle_delay = 60
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
# USRP-2 and n210 emmits noise at 14dB, choose gain well!
choices_interference = ["-13", "-12", "-11", "-10", "-9",
                        "-8", "-7", "1", "2", "3", "4", "5", "6", "7", "None"]
default_interference = ["None"]

choices_scrambler_id = [5, 12, 13, 15, 30, 36]
scrambler_id = 5
default_netname = 'foobar'
netname = default_netname
# run on all nodes by default
#default_node_ids = list(range(1, 38))
# The 10 nodes selected by Farzaneh adapted
default_node_ids = [1, 3, 12, 14, 19, 22, 27, 31, 33, 37]
default_exp = [1]

# ping parameters
ping_timeout = 6
ping_size = 64
ping_interval = 0.001
default_ping_messages = 500

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
    return "fit{:02d}".format(int_id)


def naming_scheme(protocol, run_name, tx_power, phy_rate, antenna_mask,
                  channel, interference, autocreate=False):
    """
    Returns a pathlib Path instance that points at the directory
    where all tmp files and results are stored for those settings

    if autocreate is set to True, the directory is created if needed,
    and a message is printed in that case
    """
    root = Path(run_name)
    run_root = root / "t{t}-r{r}-a{a}-ch{ch}-I{inte}-{pro}"\
        .format(t=tx_power, r=phy_rate, a=antenna_mask,
                ch=channel, inte=interference, pro=protocol)
    if autocreate:
        if not run_root.is_dir():
            print("Creating result directory: {}".format(run_root))
            run_root.mkdir(parents=True, exist_ok=True)
    return run_root


def purgedir(path):
    """
    Delete everything in the given directory
    """
    shutil.rmtree(path)


def one_run(tx_power, phy_rate, antenna_mask, channel, interference,
            protocol, *, run_name=default_run_name, slicename=default_slicename,
            load_images=False, node_ids=None,
            verbose_ssh=False, verbose_jobs=False, dry_run=False,
            tshark=False, map=False, warmup=False,
            exp=default_exp, dest=default_node_ids,
            ping_messages=default_ping_messages, route_sampling=False,
            iperf=False):
    """
    Performs data acquisition on all nodes with the following settings

    Arguments:
        tx_power: in dBm, a string like 5, 10 or 14. Correspond to the transmission power.
        phy_rate: a string among 1, 54. Correspond to the wifi rate.
        antenna_mask: a string among 1, 3, 7.
        channel: a string like e.g. 1 or 40. Correspond to the channel.
        protocol: a string among batman , olsr. Correspond to the protocol
        interference : in dBm, a string like 60 or 50.
          Correspond to the power of the noise generated in the root.
        run_name: the name for a subdirectory where all data will be kept
          successive runs should use the same name for further visualization
        slicename: the Unix login name (slice name) to enter the gateway
        load_images: a boolean specifying whether nodes should be re-imaged first
        node_ids: a list of node ids to run the scenario against; strings or ints are OK;
          defaults to the nodes [1, 4, 5, 12, 19, 22,27 ,31, 33, 37]
        tshark: a boolean specifying wether we should format/parse the .pcap.
        map: a boolean specifying wether we should fetch/parse the route tables of the nodes.
        warmup: a boolean specifying whether we should run a ping before
          the experiment to be certain of the stabilisation on the network.
        exp: a list of nodes from which we will launch the ping from. strings or ints are OK.
          defaults to the node [1]
        ping_messages : The number of pings that will be generated

    """
    # set default for the nodes parameter
    node_ids = ([int(id) for id in node_ids]
                if node_ids is not None else default_node_ids)
    exp_ids = ([int(id) for id in exp]
               if exp is not None else default_exp)
    dest_ids = ([int(id) for id in dest]
                if dest is not None else default_node_ids)
    node_ids = list(set(node_ids).union(set(exp_ids).union(set(dest_ids))))

    #
    # dry-run mode
    # just display a one-liner with parameters
    #
    if dry_run:
        print("************************************")
        print("\n")
        run_root = naming_scheme(protocol, run_name, tx_power, phy_rate,
                                 antenna_mask, channel, interference, autocreate=False)
        load_msg = "" if not load_images else " LOAD"
        nodes = " ".join(str(n) for n in node_ids)
        exps = " ".join(str(n) for n in exp)
        pingst = ["PING{}-->{}".format(e, j)

                  for e in exp_ids
                  # and on the destination
                  for j in dest_ids
                  if e != j  # and not
                  #(j in exp_ids and j < e)

                 ]

        print("dry-run:{protocol} {run_name}{load_msg} -"
              " t{tx_power} r{phy_rate} a{antenna_mask} ch{channel} I{interference}-"
              "nodes {nodes}"
              " exp {exps}"
              .format(**locals()))
        print("\nNodes from which the experiment will be launched : \n"
              "{}\nList of pings generated:\n".format(exps))
        print(pingst)
        print("\n")
        if warmup:
            print("Will do warmup pings\n")
        if tshark:
            print("Will format data using tshark "
                  "and will agregate the RSSI into one RSSI.txt file")
        if map:
            print("Will fetch the routing tables of the node "
                  "(when stabilized) and will agregate the results\n")
        if route_sampling:
            print("Will launch route sampling services on nodes")
        #print("Test creation of ROUTES files")
        #post_processor= ProcessRoutes(run_root, exp_ids, node_ids)
        # post_processor.run()
        #print("\nList of tracepaths generated:\n{}".format(tracepathst))
        # in dry-run mode we are done

    ###
    # create the logs directory based on input parameters
    run_root = naming_scheme(protocol, run_name, tx_power, phy_rate,
                             antenna_mask, channel, interference, autocreate=False)
    if(run_root.is_dir() and not dry_run):
        purgedir(run_root)
    run_root = naming_scheme(protocol, run_name, tx_power, phy_rate,
                             antenna_mask, channel, interference, autocreate=True)
    exp_info_file_name = run_root / "info.txt"
    with exp_info_file_name.open("w") as info_file:
        info_file.write("Selected nodes : \n")
        for node in node_ids[:-1]:
            info_file.write(f"{node} ")
        info_file.write(f"{node_ids[-1]}")
        info_file.write("\nSources : \n")
        for src in exp_ids[:-1]:
            info_file.write(f"{src} ")
        info_file.write(f"{exp_ids[-1]}")
        info_file.write("\nDestinations : \n")
        for dest in dest_ids[:-1]:
            info_file.write(f"{dest} ")
        info_file.write(f"{dest_ids[-1]}" + "\n")

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
    if interference != "None":
        node_scrambler = SshNode(
            gateway=faraday, hostname=fitname(scrambler_id), username="root",
            formatter=TimeColonFormatter(), verbose=verbose_ssh)
    # the global scheduler
    scheduler = Scheduler(verbose=verbose_jobs)
    # if tshark:
    #scheduler_monitoring = Scheduler(verbose=verbose_jobs)
    # if interference != "None":
    #scheduler_interferences = Scheduler(verbose=verbose_jobs)

    ##########
    check_lease = SshJob(
        scheduler=scheduler,
        node=faraday,
        verbose=verbose_jobs,
        label="rhubarbe check lease",
        command=Run("rhubarbe leases --check", label="rlease"),
        #keep_connection = True
    )

    # load images if requested

    green_light = check_lease

    if load_images:
        # the nodes that we **do not** use should be turned off
        # so if we have selected e.g. nodes 10 12 and 15, we will do
        # rhubarbe off -a ~10 ~12 ~15, meaning all nodes except 10, 12 and 15
        negated_node_ids = ["~{}".format(id) for id in node_ids]
        # Add the id of the scrambler in the list and load the gnuradio image
        negated_node_ids.append("~{}".format(scrambler_id))
        load_ids = ([int(id) for id in node_ids]
                    if node_ids is not None else default_node_ids)
        load_ids.append(scrambler_id)
        # we can do these three things in parallel
        ready_jobs = [
            SshJob(node=faraday, required=check_lease,
                   scheduler=scheduler, verbose=verbose_jobs,
                   label="turn off unused nodes",
                   command=Run("rhubarbe", "off", "-a", *negated_node_ids,
                               label="rhubarbe off")),
            SshJob(node=faraday, required=check_lease,
                   scheduler=scheduler, verbose=verbose_jobs,
                   label="load batman image",
                   command=Run("rhubarbe", "load", "-i",
                               "/home/inria_batman/bat_nodes.ndz",
                               *node_ids,
                               label="rload {}".format(node_ids))),
            SshJob(node=faraday, required=check_lease,
                   scheduler=scheduler, verbose=verbose_jobs,
                   label="load gnuradio image",
                   command=Run("rhubarbe", "load", "-i",
                               "/home/inria_batman/gnuradio_batman.ndz",
                               scrambler_id,
                               label=f"load gnuradio on {scrambler_id}"))
        ]
        # replace green_light in this case
        green_light = SshJob(
            node=faraday, required=ready_jobs,
            scheduler=scheduler, verbose=verbose_jobs,
            label="wait for nodes to come up",
            command=Run("rhubarbe", "wait", scrambler_id, *load_ids,
                        label="rwait"))

    ##########
    # setting up the wireless interface on all nodes
    #
    # this is a python feature known as a list comprehension
    # we just create as many SshJob instances as we have
    # (id, SshNode) couples in node_index
    # and gather them all in init_wireless_jobs
    # they all depend on green_light
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
                            label="reset-failed services")
        )
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
            # scheduler=scheduler,
            # required=green_light,
            node=node,
            verbose=verbose_jobs,
            label="init {}".format(id),
            command=RunScript(
                "node-utilities.sh",
                "init-ad-hoc-network-{}".format(wireless_driver),
                wireless_driver, "foobar", frequency, phy_rate,
                antenna_mask, tx_power_driver,
                label="init add-hoc network"),
            #keep_connection = True
        )
        for id, node in node_index.items()]
    init_wireless_jobs = Scheduler(
        *init_wireless_sshjobs,
        scheduler=scheduler,
        required=green_light,
        verbose=verbose_jobs,
        label="Initialisation of wireless chips")

    green_light_prot = [init_wireless_jobs, reset_failed_services]
    if interference != "None":
        # Run uhd_siggen with the chosen power
        frequency_str = frequency/1000
        frequency_str = str(frequency_str) + "G"
        init_scrambler_job = [SshJob(
            forever=True,
            node=node_scrambler,
            verbose=verbose_jobs,
            label="init scrambler on node {}".format(scrambler_id),
            #TODO : If exit-signal patch is done add exit-signal=["TERM"]
            #       to this run object and call uhd_siggen directly
            commands=[RunScript("node-utilities.sh",
                                "init-scrambler",
                                label="init scambler"),
                      Run("systemd-run --unit=uhd_siggen -t ",
                          "uhd_siggen -a usrp -g {}".format(interference),
                          "-f {} --gaussian".format(frequency_str)),
                      ]
            #keep_connection = True
        )]
        init_scrambler = Scheduler(*init_scrambler_job,
                                   scheduler=scheduler,
                                   required=green_light,
                                   #forever = True,
                                   verbose=verbose_jobs,
                                   label="Running interference")
    # then install and run batman on fit nodes
    run_protocol_job = [
        SshJob(
            # scheduler=scheduler,
            node=node,
            # required=green_light_prot,
            label="init and run {} on fit node {}".format(protocol, i),
            verbose=verbose_jobs,
            # CAREFUL : These ones use sytemd-run
            #            with the ----service-type=forking option!
            command=RunScript("node-utilities.sh", "run-{}".format(protocol),
                              label="run {}".format(protocol)),
            #keep_connection = True
        )
        for i, node in node_index.items()]

    run_protocol = Scheduler(* run_protocol_job,
                             scheduler=scheduler,
                             required=green_light_prot,
                             verbose=verbose_jobs,
                             label="init and run routing protocols")

    # after that, run tcpdump on fit nodes, this job never ends...
    if tshark:

        run_tcpdump_job = [
            SshJob(
                # scheduler=scheduler_monitoring,
                node=node,
                forever=True,
                label="run tcpdump on fit node".format(i),
                verbose=verbose_jobs,
                commands=[
                            Run("systemd-run -t  --unit=tcpdump",
                                "tcpdump -U -i moni-{}".format(wireless_driver),
                                "-y ieee802_11_radio -w /tmp/fit{}.pcap".format(i),
                                label="run tcpdump")
                         ]
                    #RunScript(
                    #    "node-utilities.sh", "run-tcpdump", wireless_driver, i,
                    #    label="run tcpdump")
                ,
                #keep_connection = True
            )
            for i, node in node_index.items()
            ]

        run_tcpdump = Scheduler(*run_tcpdump_job,
                                scheduler=scheduler,
                                required=run_protocol,
                                forever=True,
                                verbose=verbose_jobs,
                                label="Monitoring - tcpdumps")
    # let the wireless network settle
    settle_wireless_job = PrintJob(
        "Let the wireless network settle",
        sleep=settle_delay,
        scheduler=scheduler,
        required=run_protocol,
        label="settling for {} sec".format(settle_delay))

    green_light_experiment = settle_wireless_job

    if warmup:
        warmup_pings_job = [
            SshJob(
                node=nodei,
                # required=green_light_experiment,
                label="warmup ping {} -> {}".format(i, j),
                verbose=verbose_jobs,
                commands=[
                    Run("echo {} '->' {}".format(i, j),
                        label="ping {} '->' {}".format(i, j)),
                    RunScript("node-utilities.sh", "my-ping",
                              "10.0.0.{}".format(
                                  j), ping_timeout, ping_interval,
                              ping_size, ping_messages, label="")
                ],
                #keep_connection = True
            )
            # for each selected experiment nodes
            for e in exp_ids
            # looping on the source (to get the correct sshnodes)
            for i, nodei in node_index.items()
            # and on the destination
            for j, nodej in node_index.items()
            # and keep only sources that are in the selected experiment nodes
            # and remove destination that are themselves
            # and remove the couples that have already be done
            #    print("i {index} exp {expe}".format(index = i, expe= exp))
            if (i == e) and e != j and not
            (j in exp_ids and j < e)


        ]
        warmup_pings = Scheduler(Sequence(*warmup_pings_job),
                  scheduler=scheduler,
                  required=green_light_experiment,
                  verbose=verbose_jobs,
                  label="Warmup ping")
        settle_wireless_job2 = PrintJob(
            "Let the wireless network settle",
            sleep=settle_delay/2,
            scheduler=scheduler,
            required=warmup_pings,
            label="settling-warmup for {} sec".format(settle_delay/2))

        green_light_experiment = settle_wireless_job2

    if iperf:
        iperf_serv = [
            SshJob(
                node=nodei,
                label="iperf serv on {}".format(i, j),
                verbose=verbose_jobs,
                forever=True,
                commands=[
                    Run("systemd-run -t  --unit=iperf",
                        "iperf -s -p 1234  -u",
                        label="iperf serv on {}".format(j)),
                ],
            )
            for i, nodei in node_index.items()
            for j in dest_ids
            if (i == j)


        ]
        iperf_serv_sched = Scheduler(*iperf_serv,
                                     verbose=verbose_jobs,
                                     label="Iperf Servers")

        iperf_cli =[SshJob(node=nodei,
                           verbose=verbose_jobs,
                           label="iperf {}->{}".format(i, j),
                           commands=[
                                     Run("sleep 7", label=""),
                                     Run("iperf",
                                         "-c 10.0.0.{} -p 1234".format(j),
                                         "-u -b {}M -t 60".format(phy_rate),
                                         "-l 1024 > IPERF-{:02d}-{:02d}"
                                         .format(e, j),
                                         label="iperf {}->{}".format(i, j))
                            ]
                            )

                      # for each selected experiment nodes
                      for e in exp_ids
                      # looping on the source (to get the correct sshnodes)
                      for i, nodei in node_index.items()
                      # and on the destination
                      for j in dest_ids
                      # and keep only sources that are in the selected experiment nodes
                      # and remove destination that are themselves
                      # and remove the couples that have already be done
                      if (i == e) and (e != j)

                    ]
        iperf_cli_sched = Scheduler(Sequence(*iperf_cli),
                                     verbose=verbose_jobs,
                                     label="Iperf Clients")
        iperf_stop = [
                        SshJob(node=nodei,
                               verbose=verbose_jobs,
                               label="Stop iperf server",
                               commands=[
                                            Run("systemctl stop iperf")
                               ]
                               )
                        for i, nodei in node_index.items()
                        for j in dest_ids
                        if i == j
                    ]
        iperf_stop_sched = Scheduler(*iperf_stop,
                                     required=iperf_cli_sched,
                                     verbose=verbose_jobs,
                                     label="Iperf server stop")
        iperf_fetch = [
                        SshJob(node=nodei,
                               verbose=verbose_jobs,
                               label="fetch iperf report",
                               commands=[
                                            Pull(remotepaths=
                                                    ["IPERF-{:02d}-{:02d}"
                                                     .format(i, j)],
                                                 localpath=str(run_root),
                                                 label="fetch iperf report")
                                          ]
                               )
                        for e in exp_ids
                        for i, nodei in node_index.items()
                        for j in dest_ids
                        if e == i and e != j

                      ]
        iperf_fetch_sched = Scheduler(*iperf_fetch,
                                      required=iperf_stop_sched,
                                      verbose=verbose_jobs,
                                      label="Iperf fetch report")
        iperf_jobs = [iperf_serv_sched, iperf_cli_sched,
                      iperf_stop_sched, iperf_fetch_sched]
        iperf_sched = Scheduler(*iperf_jobs,
                  scheduler=scheduler,
                  required=green_light_experiment,
                  verbose=verbose_jobs,
                  label="Iperf Module")
        settle_wireless_job_iperf = PrintJob(
            "Let the wireless network settle",
            sleep=settle_delay,
            scheduler=scheduler,
            required=iperf_sched,
            label="settling-iperf for {} sec".format(settle_delay))

        green_light_experiment = settle_wireless_job_iperf
    ##########
    # create all the tracepath jobs from the first node in the list
    #
    if map:
        routes_job = [
            SshJob(
                node=nodei,
                # scheduler=scheduler,
                # required=green_light_experiment,
                label="Generating ROUTE file for prot {} on node {}"
                      .format(protocol, i),
                verbose=verbose_jobs,
                commands=[
                    RunScript("node-utilities.sh", "route-{}".format(protocol),
                              ">", "ROUTE-TABLE-{:02d}".format(i),
                              label="get route table"),
                    Pull(remotepaths="ROUTE-TABLE-{:02d}".format(i),
                         localpath=str(run_root),
                         label="")
                ],
                #keep_connection = True
            )
            for i, nodei in node_index.items()
        ]
        routes = Scheduler(*routes_job,
                           scheduler=scheduler,
                           required=green_light_experiment,
                           verbose=verbose_jobs,
                           label="Snapshoting route files")
        green_light_experiment = routes

    if route_sampling:
        routes_sampling_job = [
            SshJob(
                node=nodei,
                label="Route sampling service for prot {} on node {}"
                      .format(protocol, i),
                verbose=False,
                forever=True,
                #required = green_light_experiment,
                #scheduler = scheduler,
                commands=[
                    Push(localpaths=["route_sample_service.sh"],
                         remotepath=".", label=""),
                    Run("chmod +x route_sample_service.sh"),
                    Run("systemd-run -t  --unit=route_sample",
                        "/root/route_sample_service.sh", "route-sample",
                        "ROUTE-TABLE-{:02d}-SAMPLED".format(i),
                        "{}".format(protocol),
                        label="run route sampling service"),
                ],
                #keep_connection = True
            )
            for i, nodei in node_index.items()
        ]
        routes_sampling = Scheduler(*routes_sampling_job,
                                    scheduler=scheduler,
                                    verbose=False,
                                    forever=True,
                                    label="Route Sampling services launch",
                                    required=green_light_experiment)
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
            node=nodei,
            # required=green_light_experiment,
            label="ping {} -> {}".format(i, j),
            verbose=verbose_jobs,
            commands=[
                Run("echo {} '->' {}".format(i, j),
                    label="ping {}'->' {}".format(i, j)),
                RunScript("node-utilities.sh", "my-ping",
                          "10.0.0.{}".format(j), ping_timeout, ping_interval,
                          ping_size, ping_messages,
                          ">", "PING-{:02d}-{:02d}".format(i, j), label=""),
                Pull(remotepaths="PING-{:02d}-{:02d}".format(i, j),
                     localpath=str(run_root), label=""),
            ],
            #keep_connection = True
        )
        # for each selected experiment nodes
        for e in exp_ids
        # looping on the source (to get the correct sshnodes)
        for i, nodei in node_index.items()
        # and on the destination
        for j in dest_ids
        # and keep only sources that are in the selected experiment nodes
        # and remove destination that are themselves
        # and remove the couples that have already be done
        if (i == e) and e != j and not
        (j in exp_ids and j < e)


    ]
    pings = Scheduler(scheduler=scheduler,
                      label="PINGS",
                      verbose=verbose_jobs,
                      required=green_light_experiment)

    # retrieve all pcap files from fit nodes
    stop_protocol_job = [
        SshJob(
            # scheduler=scheduler,
            node=nodei,
            # required=pings,
            label="kill routing protocol on fit{:02d}".format(i),
            verbose=verbose_jobs,
            commands=[
                RunScript("node-utilities.sh", "kill-{}".format(protocol),
                          label="kill-{}".format(protocol)),
            ],
            #keep_connection = False
        )
        for i, nodei in node_index.items()
    ]
    stop_protocol = Scheduler(*stop_protocol_job,
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
                label="retrieve pcap trace from fit{:02d}".format(i),
                verbose=verbose_jobs,
                commands=[

                    Run("systemctl stop tcpdump"),
                    #Run("systemctl reset-failed tcpdump"),
                    #RunScript("node-utilities.sh", "kill-tcpdump",
                    #          label="kill-tcpdump"),
                    Run(
                        "echo retrieving pcap trace and result-{i}.txt from fit{i:02d}".format(i=i),
                         label=""),
                    Pull(remotepaths=["/tmp/fit{}.pcap".format(i)],
                         localpath=str(run_root), label=""),
                ],
            )
            for i, nodei in node_index.items()
        ]
        retrieve_tcpdump = Scheduler(*retrieve_tcpdump_job,
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
                label="retrieve sampling trace from fit{:02d}".format(i),
                verbose=verbose_jobs,
                commands=[
                    # RunScript("node-utilities.sh", "kill-route-sample", protocol,
                    #          label = "kill route sample"),
                    #RunScript("route_sample_service.sh", "kill-route-sample",
                    #          label="kill route sample"),
                    Run("systemctl stop route_sample"),
                    Run(
                        "echo retrieving sampling trace from fit{i:02d}".format(
                            i=i),
                        label=""),
                    Pull(remotepaths=["ROUTE-TABLE-{:02d}-SAMPLED".format(i)],
                         localpath=str(run_root), label=""),
                ],
                #keep_connection = True
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
                label="parse pcap trace {path}/fit{node}.pcap".format(path=run_root, node=i),
                verbose=verbose_jobs,
                #commands = [RunScript("parsepcap.sh", run_root, i)]
                commands=[Run("tshark", "-2", "-r", "{path}/fit{node}.pcap"
                              .format(path=run_root, node=i),
                              "-R",
                              "'(ip.dst==10.0.0.{node} && icmp) && radiotap.dbm_antsignal'"
                              .format(node=i),
                              "-Tfields",
                              "-e", "'ip.src'",
                              "-e" "'ip.dst'",
                              "-e", "'radiotap.dbm_antsignal'",
                              "> {path}/result-{node}.txt"
                              .format(path=run_root, node=i),
                              label="parse pcap locally")],
                #keep_connection = True
            )
            for i in node_ids
        ]
        parse_pcaps = Scheduler(*parse_pcaps_job,
                                scheduler=scheduler,
                                required=retrieve_tcpdump,
                                label="Parse pcap",
                                )

    if interference != "None":
        kill_uhd_siggen = SshJob(
            scheduler=scheduler,
            node=node_scrambler,
            required=pings,
            label="killing uhd_siggen on the scrambler node {}"\
                  .format(scrambler_id),
            verbose=verbose_jobs,
            commands=[Run("systemctl", "stop", "uhd_siggen"),
                      #Run("systemctl reset-failed tcpdump"),
                      ],
            #keep_connection = True
        )
        kill_2_uhd_siggen = SshJob(
            scheduler=scheduler,
            node=faraday,
            required=kill_uhd_siggen,
            label="turning off usrp on the scrambler node {}"\
                  .format(scrambler_id),
            verbose=verbose_jobs,
            commands=[Run("rhubarbe", "usrpoff", "fit{}".format(scrambler_id))],
            #keep_connection = True
        )
# if map:
        #scheduler.add(Sequence(*tracepaths, scheduler=scheduler))
# if warmup:
#       scheduler.add(Sequence(*warmup_pings_job, scheduler=scheduler))
    pings.add(Sequence(*pings_job))
    # for running sequentially we impose no limit on the scheduler
    # that will be limitied anyways by the very structure
    # of the required graph
#jobs_window = None
    dot_file = run_root/"experiment_graph"
    if not dot_file.is_file():
        scheduler.export_as_pngfile(run_root/"experiment_graph")
    if dry_run:
        scheduler.list()
        return True
    # if not in dry-run mode, let's proceed to the actual experiment

    ok = scheduler.orchestrate()  # jobs_window=jobs_window)

    #TODO : Call ssh connection close :
    #util.close_ssh_from_sched(scheduler)


    # give details if it failed
    if not ok:
        scheduler.debrief()
        scheduler.export_as_pngfile("debug")
    if ok and map:
        print("Creation of ROUTES files")
        post_processor = ProcessRoutes(run_root, exp_ids, node_ids)
        post_processor.run()
    if ok and route_sampling:
        post_processor = ProcessRoutes(run_root, exp_ids, node_ids)
        post_processor.run_sampled()
    print("END of creation for ROUTES FILES")
    # data acquisition is done, let's aggregate results
    # i.e. compute averages
    #if ok and tshark:
        #post_processor = Aggregator(run_root, node_ids, antenna_mask)
        #post_processor.run()

    return ok


def all_runs(tx_powers, phy_rates, antenna_masks,
             channels, interferences, protocols, *args, **kwds):
    """
    calls one_run with the cartesian product of
    tx_powers, phy_rates, antenna_masks and channels, interferences that are expected to
    be lists of strings

    All other arguments to one_run may/must be specified as well

    Example:
        all_runs([5, 14], [1], [1], [1, 40], [60], ...)
        will call one_run exactly 4 times
    """
    # we don't use all() on a list comprehension because
    # (*) we want to run all configs regardless of a failure, and
    #     all() is lazy and would stop at the first failure
    # (*) we need to set load_images to false after the first run
    overall = True
    if interferences is None:
        interferences = ["None"]
    for protocol in protocols:
        for tx_power in tx_powers:
            for phy_rate in phy_rates:
                for antenna_mask in antenna_masks:
                    for channel in channels:
                        for interference in interferences:
                            # record any failure
                            if not one_run(tx_power, phy_rate, antenna_mask,
                                           channel, interference, protocol,
                                           *args, **kwds):
                                overall = False
                            # make sure images will get loaded only once
                            kwds['load_images'] = False
    return overall


def main():
    """
    Command-line frontend - offers primarily all options to all_runs
    All 4 options -t -r -a -c -e -I are cumulative
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
        "-P", "--protocol", dest='protocol', metavar='protocol',
        default=default_protocol, choices=choices_protocols,
        nargs='+',
        help="specify the WMN protocols you want to use,"
             " among {}".format(set(choices_protocols)))
    parser.add_argument(
        "-N", "--node-id", dest='node_ids', metavar='routing-node',
        default=default_node_ids, choices=[
            str(x) for x in default_node_ids],
        nargs='+',
        # action=ListOfChoices,
        help="specify as many node ids as you want to run the scenario against;"
             " these will be on and sending route info;"
             " among {}".format(set(default_node_ids)))
    parser.add_argument(
        "-e", "--experiment", dest='exp', metavar='source-node',
        default=default_exp, choices=[str(x) for x in default_node_ids],
        nargs='+',
        help="specify the ids of the node you want to run"
        " the experiment from (sources of the pings),"
        " among {}".format(set(default_node_ids))
        )
    parser.add_argument(
        "-D", "--destination", dest='dest', metavar='dest-node',
        default=default_node_ids, choices=[str(x) for x in default_node_ids],
        nargs='+',
        # action=ListOfChoices,
        help="specify as many node ids as you want to be the destination of the ping")
    parser.add_argument(
        "-t", "--tx-power", dest='tx_powers', metavar='tx-power',
        default=[default_tx_power], choices=choices_tx_power,
        nargs='+',
        type=int,
        help="specify Tx power(s) among {}".format(set(choices_tx_power)))
    parser.add_argument(
        "-r", "--phy-rate", dest='phy_rates', metavar='phy-rate',
        default=[default_phy_rate], choices=choices_phy_rate,
        nargs='+',
        type=int,
        help="specify PHY rate(s), among {}".format(set(choices_phy_rate)))
    parser.add_argument(
        "-a", "--antenna-mask", dest='antenna_masks', metavar='antenna-mask',
        default=[default_antenna_mask], choices=choices_antenna_mask,
        nargs='+',
        type=int,
        help="specify antenna mask(s), among {}"
             .format(set(choices_antenna_mask)))
    parser.add_argument(
        "-c", "--channel", dest='channels', metavar='channel',
        default=[default_channel], choices=choices_channel,
        nargs='+',
        type=int,
        help="channel(s), among {}".format(set(choices_channel)))
    parser.add_argument(
        "-I", "--interference", dest='interference', metavar='interference',
        default=default_interference, choices=choices_interference,
        nargs='+',
        type=str,
        help="specify the gain (dBm) for the white gaussian noise"
             " you want to generate in the room, among {}"
             .format(set(choices_interference)))

    # should either be none (sequencial command) or parallel > 2*nbnodes
    # (since at a point we run a tcpdump command (that never ends) on each node end we have the pings jobs)
    # No sense to do it considering the experiment
    # parser.add_argument("-p", "--parallel", default=None, type=int,
    #                    help="""run in parallel, with this value as the
    #                    limit to the number of simultaneous pings - default is sequential;
    #                    -p 0 means no limit""")
    # parser.add_argument("-T", "--ping-timeout", default=ping_timeout,
    #                    help="timeout for each individual ping")
    # parser.add_argument("-I", "--ping-interval", default=ping_interval,
    #                    help="specify time interval between pings")
    # parser.add_argument("-S", "--ping-size", default=ping_size,
    #                    help="specify packet size for each individual ping")
    parser.add_argument(
        "-m", "--ping-messages", default=default_ping_messages,
        help="specify number of ping packets to send")

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

    # POST PROCESSING OPTIONS
    parser.add_argument(
        "-W", "--tshark", default=False, action='store_true',
        help="parse pcap files to get RSSIs for each nodes"
             " (Warning: you need to have tshark installed on your machine)")
    parser.add_argument(
        "-M", "--map", default=False, action='store_true',
        help="add results of the trace-path command from the first selected node")
    parser.add_argument(
        "-w", "--warmup", default=False, action='store_true',
        help="do a ping as a warmup to try to stabilise routes and then "
             "settle again before getting routes and register results")
    parser.add_argument(
        "-p", "--iperf", default=False, action='store_true',
        help="[BONUS]do an iperf for the sources and destinations ")
    parser.add_argument(
        "-S", "--route-sampling", default=False, action='store_true',
        help="observe and recolt the routing table over time during the experiment")
    args = parser.parse_args()
    # if "None" in args.interferences:
    #     for item in args.interferences:
    #        if item == "None":
    #            print("NONE FOUND")
    #            args.interferences
    # run the experiment on all specified input values
    return all_runs(
        tx_powers=args.tx_powers, phy_rates=args.phy_rates,
        antenna_masks=args.antenna_masks, channels=args.channels,
        interferences=args.interference,
        protocols=args.protocol,
        run_name=args.run_name,
        slicename=args.slicename,
        load_images=args.load_images,
        node_ids=args.node_ids,
        verbose_ssh=args.verbose_ssh,
        verbose_jobs=args.debug,
        dry_run=args.dry_run,
        tshark=args.tshark,
        map=args.map,
        warmup=args.warmup,
        exp=args.exp,
        dest=args.dest,
        # ping_timeout = args.ping_timeout
        # ping_interval = args.ping_interval
        # ping_size = args.ping_size
        ping_messages=args.ping_messages,
        route_sampling=args.route_sampling,
        iperf=args.iperf,
        # wireless_driver   = args.wifi_driver,
    )


##########
if __name__ == '__main__':
    # return something useful to your OS
    exit(0 if main() else 1)
