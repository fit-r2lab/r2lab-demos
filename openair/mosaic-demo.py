#!/usr/bin/env python3

# pylint: disable=c0103, c0111, r0912, r0913, r0914

### standard library
import os
import time
from itertools import chain, cycle
from pathlib import Path
from collections import defaultdict
from argparse import (ArgumentParser, ArgumentDefaultsHelpFormatter,
                      RawTextHelpFormatter)


### nepi-ng
from asynciojobs import Scheduler, PrintJob

from apssh import SshNode, SshJob, Run, RunScript, Pull
from apssh import TimeColonFormatter
from apssh import Service

### r2lab - for illustration purposes
# testbed preparation
from r2lab import prepare_testbed_scheduler
# utils
from r2lab import r2lab_hostname, r2lab_parse_slice, find_local_embedded_script
# argument parsing
from r2lab import ListOfChoices, ListOfChoicesNullReset


# include the set of utility scripts that are included by the r2lab kit
INCLUDES = [find_local_embedded_script(x) for x in (
    "r2labutils.sh", "nodes.sh", "mosaic-common.sh",
)]


### harware map
# the python code for interacting with sidecar is too fragile for now
# to be invoked every time; plus, it takes time; so:
def hardwired_hardware_map():
    return {
        'E3372-UE': (2, 26),
        'OAI-UE':  (6, 19),
    }

# build our hardware map: we compute the ids of the nodes
# that have the characteristics that we want
def probe_hardware_map():
    # import here so depend on socketIO_client only if needed
    from r2lab import SidecarSyncClient
    import ssl
    ssl_context = ssl.SSLContext()
    ssl_context.verify_mode = ssl.CERT_NONE
    with SidecarSyncClient(ssl=ssl_context) as sidecar:
        nodes_hash = sidecar.nodes_status()

    if not nodes_hash:
        print("Could not probe testbed status - exiting")
        exit(1)

    # debug
    #for id in sorted(nodes_hash.keys()):
    #    print(f"node[{id}] = {nodes_hash[id]}")

    # we search for the nodes that have usrp_type == 'e3372'
    e3372_ids = [id for id, node in nodes_hash.items()
                 if node['usrp_type'] == 'e3372']
    # and here the ones that have a b210 with a 'for UE' duplexer
    oaiue_ids = [id for id, node in nodes_hash.items()
                 if node['usrp_type'] == 'b210'
                 and 'ue' in node['usrp_duplexer'].lower()]

    return {
        'E3372-UE' : e3372_ids,
        'OAI-UE' :  oaiue_ids,
    }

def show_hardware_map(hw_map):
    print("Nodes that can be used as E3372 UEs (suitable for -E/-e):",
          ', '.join([str(id) for id in sorted(hw_map['E3372-UE'])]))
    print("Nodes that can be used as OpenAirInterface UEs (suitable for -U/-u)",
          ', '.join([str(id) for id in sorted(hw_map['OAI-UE'])]))

# make sure to store data in $HOME on the remote box
tcpdump_cn_pcap = "data-network.pcap"
tcpdump_cn_service = Service(
    command=f"tcpdump -n -U -i data -w ~/{tcpdump_cn_pcap}",
    service_id="tcpdump-data",
    verbose=True,
)

############################## first stage
def run(*,                                # pylint: disable=r0912, r0914, r0915
        # the pieces to use
        slicename, cn, ran, phones,
        e3372_ues, oai_ues, gnuradios,
        e3372_ue_xterms, gnuradio_xterms,
        # boolean flags
        load_nodes, reset_usb, oscillo,
        # the images to load
        image_cn, image_ran, image_oai_ue, image_e3372_ue, image_gnuradio, image_T_tracer,
        # miscell
        n_rb, nodes_left_alone, T_tracer, verbose, dry_run):
    """
    ##########
    # 3 methods to get nodes ready
    # (*) load images
    # (*) reset nodes that are known to have the right image
    # (*) do nothing, proceed to experiment

    expects e.g.
    * slicename : s.t like inria_mosaic@faraday.inria.fr
    * cn : 7
    * ran : 23
    * phones: list of indices of phones to use

    * e3372_ues : list of nodes to use as a UE using e3372
    * oai_ues   : list of nodes to use as a UE using OAI
    * gnuradios : list of nodes to load with a gnuradio image
    * T_tracer  : list of nodes to load with a tracer image

    * image_* : the name of the images to load on the various nodes

    Plus
    * load_nodes: whether to load images or not - in which case
                  image_cn, image_ran and image_*
                  are used to tell the image names
    * reset_usb : the USRP board will be reset when this is set
    """

    # what argparse knows as a slice actually is about the gateway (user + host)
    gwuser, gwhost = r2lab_parse_slice(slicename)
    gwnode = SshNode(hostname=gwhost, username=gwuser,
                     formatter=TimeColonFormatter(verbose=verbose), debug=verbose)

    hostnames = [r2lab_hostname(x) for x in (cn, ran)]

    cnnode, rannode = [
        SshNode(gateway=gwnode, hostname=hostname, username='root',
                formatter=TimeColonFormatter(verbose=verbose), debug=verbose)
        for hostname in hostnames
    ]

    scheduler = Scheduler(verbose=verbose, label="CORE EXP")

    ########## prepare the image-loading phase
    # focus on the experiment, and use
    # prepare_testbed_scheduler later on to prepare testbed
    # all we need to do at this point is compute a mapping dict
    # image -> list-of-nodes

    images_to_load = defaultdict(list)
    images_to_load[image_cn] += [cn]
    images_to_load[image_ran] += [ran]
    if e3372_ues:
        images_to_load[image_e3372_ue] += e3372_ues
    if e3372_ue_xterms:
        images_to_load[image_e3372_ue] += e3372_ue_xterms
    if oai_ues:
        images_to_load[image_oai_ue] += oai_ues
    if gnuradios:
        images_to_load[image_gnuradio] += gnuradios
    if gnuradio_xterms:
        images_to_load[image_gnuradio] += gnuradio_xterms
    if T_tracer:
        images_to_load[image_T_tracer] += T_tracer

    # start core network
    job_start_cn = SshJob(
        node=cnnode,
        commands=[
            RunScript(find_local_embedded_script("nodes.sh"),
                      "git-pull-r2lab",
                      includes=INCLUDES),
            RunScript(find_local_embedded_script("mosaic-cn.sh"),
                      "journal --vacuum-time=1s",
                      includes=INCLUDES),
            RunScript(find_local_embedded_script("mosaic-cn.sh"), "configure",
                      includes=INCLUDES),
            RunScript(find_local_embedded_script("mosaic-cn.sh"), "start",
                      includes=INCLUDES),
            tcpdump_cn_service.start_command(),
        ],
        label="start CN service",
        scheduler=scheduler,
    )

    # prepare enodeb
    reset_option = "-u" if reset_usb else ""
    job_warm_ran = SshJob(
        node=rannode,
        commands=[
            RunScript(find_local_embedded_script("nodes.sh"),
                      "git-pull-r2lab",
                      includes=INCLUDES),
            RunScript(find_local_embedded_script("mosaic-ran.sh"),
                      "journal --vacuum-time=1s",
                      includes=INCLUDES),
            RunScript(find_local_embedded_script("mosaic-ran.sh"),
                      "warm-up", reset_option,
                      includes=INCLUDES),
            RunScript(find_local_embedded_script("mosaic-ran.sh"),
                      "configure -b", n_rb, cn,
                      includes=INCLUDES),
        ],
        label="Configure eNB",
        scheduler=scheduler,
    )

    ran_requirements = [job_start_cn, job_warm_ran]
###
    if oai_ues:
        # prepare OAI UEs
        for ue in oai_ues:
            ue_node = SshNode(gateway=gwnode, hostname=r2lab_hostname(ue), username='root',
                              formatter=TimeColonFormatter(verbose=verbose), debug=verbose)
            job_warm_ues = [
                SshJob(
                    node=ue_node,
                    commands=[
                        RunScript(find_local_embedded_script("nodes.sh"),
                                  "git-pull-r2lab",
                                  includes=INCLUDES),
                        RunScript(find_local_embedded_script("mosaic-oai-ue.sh"),
                                  "journal --vacuum-time=1s",
                                  includes=INCLUDES),
                        RunScript(find_local_embedded_script("mosaic-oai-ue.sh"),
                                  "warm-up", reset_option,
                                  includes=INCLUDES),
                        RunScript(find_local_embedded_script("mosaic-oai-ue.sh"),
                                  "configure -b", n_rb,
                                  includes=INCLUDES),
                        ],
                    label=f"Configure OAI UE on fit{ue}",
                    scheduler=scheduler)
                ]
            ran_requirements.append(job_warm_ues)

###
    if not load_nodes and phones:
        job_turn_off_phones = SshJob(
            node=gwnode,
            commands=[
                RunScript(find_local_embedded_script("faraday.sh"),
                          f"macphone{phone} phone-off")
                for phone in phones],
            scheduler=scheduler,
        )
        ran_requirements.append(job_turn_off_phones)

    # wait for everything to be ready, and add an extra grace delay

    grace = 5
    grace_delay = PrintJob(
        f"Allowing grace of {grace} seconds",
        sleep=grace,
        required=ran_requirements,
        scheduler=scheduler,
        label=f"settle for {grace}s",
    )

    # optionally start T_tracer
    if T_tracer:
        job_start_T_tracer = SshJob(                    # pylint: disable=w0612
            node=SshNode(
                gateway=gwnode, hostname=r2lab_hostname(T_tracer[0]), username='root',
                formatter=TimeColonFormatter(verbose=verbose), debug=verbose),
            commands=[
                Run(f"/root/trace {ran}",
                    x11=True),
            ],
            label="start T_tracer service",
            required=ran_requirements,
            scheduler=scheduler,
        )
#        ran_requirements.append(job_start_T_tracer)


# start services

    graphical_option = "-x" if oscillo else ""
    graphical_message = "graphical" if oscillo else "regular"
    tracer_option = " -T" if T_tracer else ""

    # we use a Python variable for consistency
    # although it not used down the road
    _job_service_ran = SshJob(
        node=rannode,
        commands=[
            RunScript(find_local_embedded_script("mosaic-ran.sh"),
                      "start", graphical_option, tracer_option,
                      includes=INCLUDES,
                      x11=oscillo,
                      ),
        ],
        label=f"start {graphical_message} softmodem on eNB",
        required=grace_delay,
        scheduler=scheduler,
    )

    ########## run experiment per se
    # Manage phone(s) and OAI UE(s)
    # this starts at the same time as the eNB, but some
    # headstart is needed so that eNB actually is ready to serve
    sleeps = [20, 30]
    phone_msgs = [f"wait for {sleep}s for eNB to start up before waking up phone{id}"
                  for sleep, id in zip(sleeps, phones)]
    wait_commands = [f"echo {msg}; sleep {sleep}"
                     for msg, sleep in zip(phone_msgs, sleeps)]

    job_start_phones = [
        SshJob(
            node=gwnode,
            commands=[
                Run(wait_command),
                RunScript(find_local_embedded_script("faraday.sh"), f"macphone{id}",
                          "r2lab-embedded/shell/macphone.sh", "phone-on",
                          includes=INCLUDES),
                RunScript(find_local_embedded_script("faraday.sh"), f"macphone{id}",
                          "r2lab-embedded/shell/macphone.sh", "phone-start-app",
                          includes=INCLUDES),
            ],
            label=f"turn off airplace mode on phone {id}",
            required=grace_delay,
            scheduler=scheduler)
        for id, wait_command in zip(phones, wait_commands)]

    if oai_ues:
        delay = 25
        for ue in oai_ues:
            msg = f"wait for {delay}s for eNB to start up before running UE on node fit{ue}"
            wait_command = f"echo {msg}; sleep {delay}"
            ue_node = SshNode(gateway=gwnode, hostname=r2lab_hostname(ue), username='root',
                              formatter=TimeColonFormatter(verbose=verbose), debug=verbose)
            job_start_ues = [
                SshJob(
                    node=ue_node,
                    commands=[
                        Run(wait_command),
                        RunScript(find_local_embedded_script("mosaic-oai-ue.sh"),
                                  "start",
                                  includes=INCLUDES),
                        ],
                    label=f"Start OAI UE on fit{ue}",
                    required=grace_delay,
                    scheduler=scheduler)
                ]
            delay += 20

        for ue in oai_ues:
            ue_node = SshNode(gateway=gwnode, hostname=r2lab_hostname(ue), username='root',
                              formatter=TimeColonFormatter(verbose=verbose), debug=verbose)
            msg = f"Wait 60s and then ping faraday gateway from UE on fit{ue}"
            _job_ping_gw_from_ue = [
                SshJob(
                    node=ue_node,
                    commands=[
                        Run(f"echo {msg}; sleep 60"),
                        Run(f"ping -c 5 -I oip1 faraday.inria.fr"),
                        ],
                    label=f"ping faraday gateway from UE on fit{ue}",
                    critical=False,
                    required=job_start_ues,
                    scheduler=scheduler)
                ]

    # ditto
    _job_ping_phones_from_cn = [
        SshJob(
            node=cnnode,
            commands=[
                Run("sleep 20"),
                Run(f"ping -c 100 -s 100 -i .05 172.16.0.{id+1} &> /root/ping-phone{id}"),
                ],
            label=f"ping phone {id} from core network",
            critical=False,
            required=job_start_phones,
            scheduler=scheduler)
        for id in phones]

    ########## xterm nodes

    colors = ("wheat", "gray", "white", "darkolivegreen")

    xterms = e3372_ue_xterms + gnuradio_xterms

    for xterm, color in zip(xterms, cycle(colors)):
        xterm_node = SshNode(
            gateway=gwnode, hostname=r2lab_hostname(xterm), username='root',
            formatter=TimeColonFormatter(verbose=verbose), debug=verbose)
        SshJob(
            node=xterm_node,
            command=Run(f"xterm -fn -*-fixed-medium-*-*-*-20-*-*-*-*-*-*-*",
                        f" -bg {color} -geometry 90x10",
                        x11=True),
            label=f"xterm on node {xterm_node.hostname}",
            scheduler=scheduler,
            # don't set forever; if we do, then these xterms get killed
            # when all other tasks have completed
            # forever = True,
            )

    # remove dangling requirements - if any
    # should not be needed but won't hurt either
    scheduler.sanitize()

    ##########
    print(10*"*", "nodes usage summary")
    if load_nodes:
        for image, nodes in images_to_load.items():
            for node in nodes:
                print(f"node {node} : {image}")
    else:
        print("NODES ARE USED AS IS (no image loaded, no reset)")
    print(10*"*", "phones usage summary")
    if phones:
        for phone in phones:
            print(f"Using phone{phone}")
    else:
        print("No phone involved")
    if nodes_left_alone:
        print(f"Ignore following fit nodes: {nodes_left_alone}")

    # wrap scheduler into global scheduler that prepares the testbed
    scheduler = prepare_testbed_scheduler(
        gwnode, load_nodes, scheduler, images_to_load, nodes_left_alone)

    scheduler.check_cycles()
    # Update the .dot and .png file for illustration purposes
    name = "mosaic-load" if load_nodes else "mosaic"
    print(10*'*', 'See main scheduler in',
          scheduler.export_as_pngfile(name))

    if verbose:
        scheduler.list()

    if dry_run:
        return True

    if verbose:
        input('OK ? - press control C to abort ? ')

    if not scheduler.orchestrate():
        print(f"RUN KO : {scheduler.why()}")
        scheduler.debrief()
        return False
    print("RUN OK")
    return True

# use the same signature in addition to run_name by convenience
def collect(run_name, slicename, cn, ran, oai_ues, verbose, dry_run):
    """
    retrieves all relevant logs under a common name
    otherwise, same signature as run() for convenience

    retrieved stuff will be 3 compressed tars named
    <run_name>-(cn|ran).tar.gz

    xxx - todo - it would make sense to also unwrap them all
    in a single place locally, like what "logs.sh unwrap" does
    """

    # the local dir to store incoming raw files. mostly tar files
    local_path = Path(f"{run_name}")
    if not local_path.exists():
        print(f"Creating directory {local_path}")
        local_path.mkdir()

    gwuser, gwhost = r2lab_parse_slice(slicename)
    gwnode = SshNode(hostname=gwhost, username=gwuser,
                     formatter=TimeColonFormatter(verbose=verbose),
                     debug=verbose)

    functions = ["cn", "ran"]
    hostnames = [r2lab_hostname(x) for x in (cn, ran)]
    node_cn, node_ran = nodes = [
        SshNode(gateway=gwnode, hostname=hostname, username='root',
                formatter=TimeColonFormatter(verbose=verbose), debug=verbose)
        for hostname in hostnames
    ]
    if oai_ues:
        hostnames_ue = [r2lab_hostname(x) for x in oai_ues]
        nodes_ue = [
            SshNode(gateway=gwnode, hostname=hostname, username='root',
                    formatter=TimeColonFormatter(verbose=verbose), debug=verbose)
            for hostname in hostnames_ue]


    # all nodes involved are  managed in the same way
    # node: a SshNode instance
    # id: the fit number
    # function, a string like 'cn' or 'ran' or 'oai-ue'

    local_nodedirs_tars = []

    scheduler = Scheduler(verbose=verbose)
    for (node, id, function) in zip(
            chain(nodes, nodes_ue),
            chain( [cn, ran], oai_ues),
            chain(functions, cycle(["oai-ue"]))):
        # nodes on 2 digits
        id0 = f"{id:02d}"
        # node-dep collect dir
        node_dir = local_path / id0
        node_dir.exists() or node_dir.mkdir()
        local_tar = f"{local_path}/{function}-{id0}.tgz"
        SshJob(
            node=node,
            commands=[
                # first run a 'capture-all' function remotely
                # to gather all the relevant files and commands remotely
                RunScript(
                    find_local_embedded_script(f"mosaic-{function}.sh"),
                    f"capture-all", f"{run_name}-{function}",
                    includes=INCLUDES),
                # and retrieve it locally
                Pull(
                    remotepaths=f"{run_name}-{function}.tgz",
                    localpath=local_tar),
                ],
            scheduler=scheduler)
        local_nodedirs_tars.append((node_dir, local_tar))

    
    # retrieve tcpdump on CN
    SshJob(
        node=node_cn,
        commands=[
            tcpdump_cn_service.stop_command(),
            Pull(remotepaths=[tcpdump_cn_pcap],
                 localpath=local_path),
            ],
        scheduler=scheduler
        )

    print(10*'*', 'See collect scheduler in',
          scheduler.export_as_pngfile("mosaic-collect"))

    if verbose:
        scheduler.list()

    if dry_run:
        return

    if not scheduler.run():
        print("KO")
        scheduler.debrief()
        return

    # unwrap
    for node_dir, tar in local_nodedirs_tars:
        print(f"Untaring {tar} in {node_dir}/")
        os.system(f"tar -C {node_dir} -xzf {tar}")


# raw formatting (for -x mostly) + show defaults
class RawAndDefaultsFormatter(ArgumentDefaultsHelpFormatter,
                              RawTextHelpFormatter):
    pass

def main():                                      # pylint: disable=r0914, r0915

    hardware_map = hardwired_hardware_map()

    def_slicename = "inria_mosaic@faraday.inria.fr"

    # WARNING: the core network box needs its data interface !
    # so boxes with a USRP N210 are not suitable for that job
    def_cn, def_ran = 7, 23

    def_image_cn = "mosaic-cn"
    # hopefully available in the near future
    def_image_ran = "mosaic-ran"
    def_image_ran = "/var/lib/rhubarbe-images/mosaic-ran-2019-02-25.ndz"

    def_image_gnuradio = "gnuradio"
    def_image_T_tracer = "oai-trace"
    # these 2 are mere intentions at this point
    def_image_oai_ue = "mosaic-ue"
    def_image_e3372_ue = "e3372-ue"

    parser = ArgumentParser(formatter_class=RawAndDefaultsFormatter)

    parser.add_argument(
        "-s", "--slice", dest='slicename', default=def_slicename,
        help="slice to use for entering")

    parser.add_argument(
        "--cn", default=def_cn,
        help="id of the node that runs the core network")
    parser.add_argument(
        "--ran", default=def_ran,
        help="""id of the node that runs the eNodeB,
requires a USRP b210 and 'duplexer for eNodeB""")

    parser.add_argument(
        "-p", "--phones", dest='phones',
        action=ListOfChoicesNullReset, type=int, choices=(1, 2, 0),
        default=[1],
        help='Commercial phones to use; use -p 0 to choose no phone')


    e3372_nodes = hardware_map['E3372-UE']
    parser.add_argument(
        "-E", "--e3372", dest='e3372_ues', default=[],
        action=ListOfChoices, type=int, choices=e3372_nodes,
        help=f"""id(s) of nodes to be used as a E3372-based UE
choose among {e3372_nodes}""")
    parser.add_argument(
        "-e", "--e3372-xterm", dest='e3372_ue_xterms', default=[],
        action=ListOfChoices, type=int, choices=e3372_nodes,
        help="""likewise, with an xterm on top""")

    oaiue_nodes = hardware_map['OAI-UE']
    parser.add_argument(
        "-U", "--oai-ue", dest='oai_ues', default=[],
        action=ListOfChoices, type=int, choices=oaiue_nodes,
        help=f"""id(s) of nodes to be used as a OAI-based UE
choose among {oaiue_nodes} - note that these notes are also
suitable for scrambling the 2.54 GHz uplink""")

    parser.add_argument(
        "-G", "--gnuradio", dest='gnuradios', default=[], action='append',
        help="""id(s) of nodes intended to run gnuradio;
prefer using fit10 and fit11 (B210 without duplexer)""")
    parser.add_argument(
        "-g", "--gnuradio-xterm", dest='gnuradio_xterms', default=[], action='append',
        help="""likewise, with an xterm on top""")

    parser.add_argument(
        "-l", "--load", dest='load_nodes', action='store_true', default=False,
        help='load images as well')
    parser.add_argument(
        "-r", "--reset", dest="reset_usb",
        default=True, action='store_false',
        help="""Reset the USB board if set (always done with --load)""")

    parser.add_argument(
        "-o", "--oscillo", dest='oscillo',
        action='store_true', default=False,
        help='run eNB with oscillo function; no oscillo by default')

    parser.add_argument(
        "-T", "--T_tracer", dest='T_tracer', default=[], action='append',
        help="id of the node to run the GUI eNB tracer")

    parser.add_argument(
        "--image-cn", default=def_image_cn,
        help="image to load in hss and epc nodes")
    parser.add_argument(
        "--image-ran", default=def_image_ran,
        help="image to load in ran node")
    parser.add_argument(
        "--image-e3372-ue", default=def_image_e3372_ue,
        help="image to load in e3372 UE nodes")
    parser.add_argument(
        "--image-oai-ue", default=def_image_oai_ue,
        help="image to load in OAI UE nodes")
    parser.add_argument(
        "--image-gnuradio", default=def_image_gnuradio,
        help="image to load in gnuradio nodes")
    parser.add_argument(
        "--image-T-tracer", default=def_image_T_tracer,
        help="image to load on the eNB tracer node")


    parser.add_argument(
        "-N", "--n-rb", dest='n_rb',
        default=25,
        type=int,
        choices=[25, 50],
        help="specify the Number of Resource Blocks (NRB) for the downlink")

    parser.add_argument(
        "-m", "--map", default=False, action='store_true',
        help="""Probe the testbed to get an updated hardware map
that shows the nodes that currently embed the
capabilities to run as either E3372- and
OpenAirInterface-based UE. Does nothing else.""")

    parser.add_argument(
        "-i", "--nodes-left-alone", dest='nodes_left_alone',
        default=[], action=ListOfChoices, type=int,
        help="ignore (do not switch off) those nodes")

    parser.add_argument(
        "-v", "--verbose", action='store_true', default=False)
    parser.add_argument(
        "-n", "--dry-run", action='store_true', default=False)

    args = parser.parse_args()

    if args.map:
        show_hardware_map(probe_hardware_map())
        exit(0)

    # map is not a recognized parameter in run()
    delattr(args, 'map')

    # we pass to run exactly the set of arguments known to parser
    # build a dictionary with all the values in the args
    kwds = args.__dict__.copy()

    # actually run it
    now = time.strftime("%H:%M:%S")
    print(f"Experiment STARTING at {now}")
    if not run(**kwds):
        print("exiting")
        return

    if args.dry_run:
        run_name = '<your-run-name>'
    else:
        run_name = None
        print(f"Experiment READY at {now}")
        # then prompt for when we're ready to collect
        try:
            run_name = input("type capture name when ready : ")
            if not run_name:
                raise KeyboardInterrupt
        except KeyboardInterrupt:
            print("OK, skipped collection, bye")

    if run_name:
        collect(run_name, args.slicename,
                args.cn, args.ran, args.oai_ues, args.verbose, args.dry_run)


main()
