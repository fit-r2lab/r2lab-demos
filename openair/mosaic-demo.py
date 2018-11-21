#!/usr/bin/env python3

# pylint: disable=c0103, c0111,

### standard library
import os.path
import time
import asyncio
import itertools
from collections import defaultdict
from argparse import (ArgumentParser, ArgumentDefaultsHelpFormatter,
                      RawTextHelpFormatter)


### nepi-ng
from asynciojobs import Scheduler, PrintJob

from apssh import SshNode, SshJob, Run, RunScript, Pull
from apssh.formatters import TimeColonFormatter


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
    from r2lab import R2labSidecar
    with R2labSidecar() as sidecar:
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

############################## first stage
def run(*,                                # pylint: disable=r0912, r0914, r0915
        # the pieces to use
        slicename, cn, enb, phones,
        e3372_ues, oai_ues, gnuradios,
        e3372_ue_xterms, oai_ue_xterms, gnuradio_xterms,
        # boolean flags
        load_nodes, skip_reset_usb, oscillo,
        # the images to load
        image_cn, image_enb, image_oai_ue, image_e3372_ue, image_gnuradio,
        # miscell
        n_rb, verbose, dry_run):
    """
    ##########
    # 3 methods to get nodes ready
    # (*) load images
    # (*) reset nodes that are known to have the right image
    # (*) do nothing, proceed to experiment

    expects e.g.
    * slicename : s.t like inria_mosaic@faraday.inria.fr
    * cn : 7
    * enb : 23
    * phones: list of indices of phones to use

    * e3372_ues : list of nodes to use as a UE using e3372
    * oai_ues   : list of nodes to use as a UE using OAI
    * gnuradios : list of nodes to load with a gnuradio image

    * image_* : the name of the images to load on the various nodes

    Plus
    * load_nodes: whether to load images or not - in which case
                  image_cn, image_enb and image_*
                  are used to tell the image names
    * skip_reset_usb : the USRP board will be reset as well unless this is set
    """

    # what argparse knows as a slice actually is about the gateway (user + host)
    gwuser, gwhost = r2lab_parse_slice(slicename)
    gwnode = SshNode(hostname=gwhost, username=gwuser,
                     formatter=TimeColonFormatter(verbose=verbose), debug=verbose)

    hostnames = [r2lab_hostname(x) for x in (cn, enb)]

    cnnode, enbnode = [
        SshNode(gateway=gwnode, hostname=hostname, username='root',
                formatter=TimeColonFormatter(verbose=verbose), debug=verbose)
        for hostname in hostnames
    ]

    sched = Scheduler(verbose=verbose, label="CORE EXP")

    ########## prepare the image-loading phase
    # focus on the experiment, and use
    # prepare_testbed_scheduler later on to prepare testbed
    # all we need to do at this point is compute an
    # image -> list-of-nodes mapping

    images_to_load = defaultdict(list)
    images_to_load[image_cn] += [cn]
    images_to_load[image_enb] += [enb]
    if e3372_ues:
        images_to_load[image_e3372_ue] += e3372_ues
    if e3372_ue_xterms:
        images_to_load[image_e3372_ue] += e3372_ue_xterms
    if oai_ues:
        images_to_load[image_oai_ue] += oai_ues
    if oai_ue_xterms:
        images_to_load[image_oai_ue] += oai_ue_xterms
    if gnuradios:
        images_to_load[image_gnuradio] += gnuradios
    if gnuradio_xterms:
        images_to_load[image_gnuradio] += gnuradio_xterms


    # start core network
    job_service_cn = SshJob(
        node=cnnode,
        commands=[
            RunScript(find_local_embedded_script("mosaic-cn.sh"), "configure",
                      includes=INCLUDES),
            RunScript(find_local_embedded_script("mosaic-cn.sh"), "start",
                      includes=INCLUDES)],
        label="start HSS service",
        scheduler=sched,
    )

    # start enodeb
    job_warm_enb = SshJob(
        node=enbnode,
        commands=[
            RunScript(find_local_embedded_script("mosaic-ran.sh"),
                      "configure", cn,
                      includes=INCLUDES),
        ],
        label="Warm eNB",
        scheduler=sched,
    )

    enb_requirements = (job_service_cn, job_warm_enb)

    # wait for everything to be ready, and add an extra grace delay

    grace = 30 if load_nodes else 10
    grace_delay = PrintJob(
        f"Allowing grace of {grace} seconds",
        sleep=grace,
        required=enb_requirements,
        scheduler=sched,
        label=f"settle for {grace}s",
    )

    # start services

    graphical_option = "-x" if oscillo else ""
    graphical_message = "graphical" if oscillo else "regular"

    job_service_enb = SshJob(
        node=enbnode,
        # run-enb expects the id of the epc as a parameter
        # n_rb means number of resource blocks for DL, set to either 25 or 50.
        commands=[
            RunScript(find_local_embedded_script("mosaic-ran.sh"),
                      "start", graphical_option,
                      includes=INCLUDES,
                      x11=oscillo,
                      ),
        ],
        label=f"start {graphical_message} softmodem on eNB",
        required=grace_delay,
        scheduler=sched,
    )

    ########## run experiment per se
    # Manage phone(s)
    # this starts at the same time as the eNB, but some
    # headstart is needed so that eNB actually is ready to serve
    delay = 12
    msg = f"wait for {delay}s for eNB to start up"
    wait_command = f"echo {msg}; sleep {delay}"

    job_start_phones = [
        SshJob(
            node=gwnode,
            commands=[
                Run(wait_command),
                RunScript(find_local_embedded_script("faraday.sh"),
                          f"macphone{id}", "r2lab-embedded/shell/macphone.sh", "phone-on",
                          includes=INCLUDES),
                RunScript(find_local_embedded_script("faraday.sh"),
                          "macphone{id}",
                          "r2lab-embedded/shell/macphone.sh", "phone-start-app",
                          includes=INCLUDES),
            ],
            label=f"turn off airplace mode on phone {id}",
            required=grace_delay,
            scheduler=sched)
        for id in phones]

    job_ping_phones_from_cn = [
        SshJob(
            node=cnnode,
            commands=[
                Run("sleep 10"),
                Run(f"ping -c 100 -s 100 -i .05 172.16.0.{id+1} &> /root/ping-phone"),
                ],
            label=f"ping phone {id} from core network",
            critical=False,
            required=job_start_phones)
        for id in phones]

    ########## xterm nodes

    colors = ("wheat", "gray", "white", "darkolivegreen")

    xterms = e3372_ue_xterms + oai_ue_xterms + gnuradio_xterms

    for xterm, color in zip(xterms, itertools.cycle(colors)):
        xterm_node = SshNode(
            gateway=gwnode, hostname=r2lab_hostname(xterm), username='root',
            formatter=TimeColonFormatter(verbose=verbose), debug=verbose)
        SshJob(
            node=xterm_node,
            command=Run(f"xterm -fn -*-fixed-medium-*-*-*-20-*-*-*-*-*-*-*"
                        " -bg {color} -geometry 90x10",
                        x11=True),
            label=f"xterm on node {xterm_node.hostname}",
            # don't set forever; if we do, then these xterms get killed
            # when all other tasks have completed
            # forever = True,
            )

    # remove dangling requirements - if any
    # should not be needed but won't hurt either
    sched.sanitize()

    ##########
    print(20*"*", "nodes usage summary")
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

    # wrap sched into global scheduler that prepares the testbed
    sched = prepare_testbed_scheduler(gwnode, load_nodes, sched, images_to_load)

    sched.check_cycles()
    # Update the .dot and .png file for illustration purposes
    name = "mosaic-load" if load_nodes else "mosaic"
    sched.export_as_dotfile(f"{name}.dot")
    os.system(f"dot -Tpng {name}.dot -o {name}.png")
    print(f"(Over)wrote {name}.png")

    if verbose or dry_run:
        sched.list()

    if dry_run:
        return False

    if verbose:
        input('OK ? - press control C to abort ? ')

    if not sched.orchestrate():
        print(f"RUN KO : {sched.why()}")
        sched.debrief()
        return False
    print("RUN OK")
    return True

# use the same signature in addition to run_name by convenience
def collect(run_name, slicename, hss, epc, enb, verbose):
    """
    retrieves all relevant logs under a common name
    otherwise, same signature as run() for convenience

    retrieved stuff will be 3 compressed tars named
    <run_name>-(hss|epc|enb).tar.gz

    xxx - todo - it would make sense to also unwrap them all
    in a single place locally, like what "logs.sh unwrap" does
    """

    gwuser, gwhost = r2lab_parse_slice(slicename)
    gwnode = SshNode(hostname=gwhost, username=gwuser,
                     formatter=TimeColonFormatter(verbose=verbose), debug=verbose)

    functions = "hss", "epc", "enb"

    hostnames = hssname, epcname, enbname = [ r2lab_hostname(x) for x in (hss, epc, enb) ]

    nodes = hssnode, epcnode, enbnode = [
        SshNode(gateway=gwnode, hostname=hostname, username='root',
                formatter=TimeColonFormatter(verbose=verbose), debug=verbose)
        for hostname in hostnames
    ]

    # first run a 'capture' function remotely to gather all the relevant
    # info into a single tar named <run_name>.tgz

    capturers = [
        SshJob(
            node=node,
            command=RunScript(
                find_local_embedded_script("oai-common.sh"),
                f"capture-{function}", run_name,
                includes=[find_local_embedded_script(f"mosaic-{function}.sh")]),
            label="capturer on {function}",
        )
        for (node, function) in zip(nodes, functions) ]

    collectors = [
        SshJob(
            node=node,
            command=Pull(
                remotepaths=[f"{run_name}-{function}.tgz"],
                localpath="."),
            label=f"collector on {function}",
            required=capturers,
        )
        for (node, function, capturer) in zip(nodes, functions, capturers) ]

    sched = Scheduler(verbose=verbose)
    sched.update(capturers)
    sched.update(collectors)

    if verbose:
        sched.list()

    if not sched.orchestrate():
        print("KO")
        sched.debrief()
        return
    print("OK")
    if os.path.exists(run_name):
        print(f"local directory {run_name} already exists = NOT UNWRAPPED !")
        return
    os.mkdir(run_name)
    local_tars = [f"{run_name}-{ext}.tgz" for ext in ['hss', 'epc', 'enb']]
    for tar in local_tars:
        print(f"Untaring {tar} in {run_name}")
        os.system(f"tar -C {run_name} -xzf {tar}")


# raw formatting (for -x mostly) + show defaults
class RawAndDefaultsFormatter(ArgumentDefaultsHelpFormatter,
                              RawTextHelpFormatter):
    pass

def main():                                      # pylint: disable=r0914, r0915

    hardware_map = hardwired_hardware_map()

    def_slicename = "inria_mosaic@faraday.inria.fr"

    # WARNING: the core network box needs its data interface !
    # so boxes with a USRP N210 are not suitable for that job
    def_cn, def_enb = 7, 23

    def_image_cn  = "mosaic-cn"
    # hopefully available in the near future
    def_image_enb = "mosaic-ran"

    def_image_gnuradio = "gnuradio"
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
        "--enb", default=def_enb,
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
        help ="""likewise, with an xterm on top""")

    oaiue_nodes = hardware_map['OAI-UE']
    parser.add_argument(
        "-U", "--oai-ue", dest='oai_ues', default=[],
        action=ListOfChoices, type=int, choices=oaiue_nodes,
        help =f"""id(s) of nodes to be used as a OAI-based UE
choose among {oaiue_nodes} - note that these notes are also
suitable for scrambling the 2.54 GHz uplink""")
    parser.add_argument(
        "-u", "--oai-ue-xterm", dest='oai_ue_xterms', default=[],
        action=ListOfChoices, type=int, choices=oaiue_nodes,
        help ="""likewise, with an xterm on top""")

    # xxx could use choices here too
    parser.add_argument(
        "-G", "--gnuradio", dest='gnuradios', default=[], action='append',
        help="""id(s) of nodes intended to run gnuradio;
prefer using fit10 and fit11 (B210 without duplexer)""")
    parser.add_argument(
        "-g", "--gnuradio-xterm", dest='gnuradio_xterms', default=[], action='append',
        help ="""likewise, with an xterm on top""")

    parser.add_argument(
        "-l", "--load", dest='load_nodes', action='store_true', default=False,
        help='load images as well')
    parser.add_argument(
        "-f", "--fast", dest="skip_reset_usb",
        default=False, action='store_true',
        help="""Skip resetting the USB boards if set""")

    parser.add_argument(
        "-o", "--oscillo", dest='oscillo',
        action='store_true', default=False,
        help='run eNB with oscillo function; no oscillo by default')

    parser.add_argument(
        "--image-cn", default=def_image_cn,
        help="image to load in hss and epc nodes")
    parser.add_argument(
        "--image-enb", default=def_image_enb,
        help="image to load in enb node")
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
        "-v", "--verbose", action='store_true', default=False)
    parser.add_argument(
        "-n", "--dry-run", action='store_true', default=False)

    args = parser.parse_args()

    if args.map:
        show_hardware_map(probe_hardware_map())
        exit(0)

    # map is not a recognized parameter in run()
    delattr(args, 'map')

    # we pass to run and collect exactly the set of arguments known to parser
    # build a dictionary with all the values in the args
    kwds = args.__dict__.copy()

    # actually run it
    now = time.strftime("%H:%M:%S")
    print(f"Experiment STARTING at {now}")
    if not run(**kwds):
        print("exiting")
        return

    print("Experiment READY at {now}")
    # then prompt for when we're ready to collect
    try:
        run_name = input("type capture name when ready : ")
        if not run_name:
            raise KeyboardInterrupt
        collect(run_name, args.slicename, args.hss, args.epc, args.enb, args.verbose)
    except KeyboardInterrupt as e:
        print("OK, skipped collection, bye")

    # this should maybe be taken care of in asynciojobs
    asyncio.get_event_loop().close()

main()
