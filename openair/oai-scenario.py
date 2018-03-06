#!/usr/bin/env python3

import os.path
import time
import asyncio
import itertools
from collections import defaultdict

from asynciojobs import Scheduler, Job, Sequence

from apssh import SshNode, SshJob, Run, RunScript, Pull
from apssh.formatters import ColonFormatter

from listofchoices import ListOfChoices

hardware_map = {
    'E3372-UE' : (2, 26),
    'OAI-UE' : (6, 19),
}
hardware_reverse_map = {
    id: kind for (kind, ids) in hardware_map.items()
    for id in ids
}

# to be added to apssh
from localjob import LocalJob

def r2lab_hostname(x):
    """
    Return a valid hostname from a name like either
    1 (int), 1(str), 01, fit1 or fit01 ...
    """
    return "fit{:02d}".format(int(str(x).replace('fit','')))

def parse_slice(slice):
    """
    returns username and hostname from a slice
    can be either username@hostname or just username
    in the latter case the hostname defaults to 
    the r2lab gateway faraday.inria.fr
    """
    if slice.find('@') > 0:
        user, host = slice.split('@')
        return user, host
    else:
        return slice, "faraday.inria.fr"

def locate_local_script(s):
    """
    all the scripts are located in the same place
    find that place among a list of possible locations
    """
    paths = [
        "../../r2lab-embedded/shell/",
        os.path.expanduser("~/git/r2lab-embedded/shell/"), 
        os.path.expanduser("~/r2lab-embedded/shell/"),
    ]
    for path in paths:
        candidate = os.path.join(path, s)
        if os.path.exists(candidate):
            return candidate
    print("WARNING: could not locate local script {}".format(s))
    for path in paths:
        print("W: searched in {}".format(path))

async def verbose_delay(duration, *print_args):
    """
    a coroutine that just sleeps for some time - and says so
    print_args are passed to print
    """
    print(20*'*', "Waiting for {} s".format(duration), *print_args)
    await asyncio.sleep(duration)
    print("Done waiting for {} s".format(duration), *print_args)

# include the set of utility scripts that are included by the r2lab kit
includes = [ locate_local_script(x) for x in [
    "r2labutils.sh", "nodes.sh", "oai-common.sh",
] ]

############################## first stage 
def run(*,
        # the pieces to use
        slice, hss, epc, enb, phones, e3372_ues, oai_ues, extras,
        # boolean flags
        load_nodes, reset_nodes, skip_reset_usb,
        # the images to load
        image_gw, image_enb, image_oai_ue, image_e3372_ue, image_extra,
        # miscell
        n_rb, verbose, dry_run):
    """
    ##########
    # 3 methods to get nodes ready
    # (*) load images
    # (*) reset nodes that are known to have the right image
    # (*) do nothing, proceed to experiment

    expects e.g.
    * slice : s.t like inria_oai.skype@faraday.inria.fr
    * hss : 04
    * epc : 03
    * enb : 23
    * phones: list of indices of phones to use

    * e3372_ues : list of nodes to use as a UE using e3372
    * oai_ues   : list of nodes to use as a UE using OAI
    * extras    : list of extra nodes that will simply run an xterm

    * image_* : the name of the images to load on the various nodes

    Plus
    * load_nodes: whether to load images or not - in which case
                  image_gw, image_enb and image_*
                  are used to tell the image names
    * reset_nodes: if load_nodes is false and reset_nodes is true, the nodes are reset - i.e. rebooted
    * otherwise (both load_nodes and reset_nodes are False): do nothing
    * skip_reset_usb : the USRP board will be reset as well unless this is set
    """

    # what argparse knows as a slice actually is a gateway (user + host)
    gwuser, gwhost = parse_slice(slice)
    gwnode = SshNode(hostname = gwhost, username = gwuser,
                     formatter = ColonFormatter(verbose=verbose), debug=verbose)

    hostnames = hssname, epcname, enbname = [ r2lab_hostname(x) for x in (hss, epc, enb) ]

    optional_ids = e3372_ues + oai_ues + extras
    
    hssnode, epcnode, enbnode = [
        SshNode(gateway = gwnode, hostname = hostname, username = 'root',
                formatter = ColonFormatter(verbose=verbose), debug=verbose)
        for hostname in hostnames
    ]

    sched = Scheduler(verbose=verbose)

    ########## preparation
    job_check_for_lease = SshJob(
        node = gwnode,
        command = [ "rhubarbe", "leases", "--check" ],
        label = "check we have a current lease",
        scheduler = sched,
    )

    # turn off all nodes 
    turn_off_command = [ "rhubarbe", "off", "-a"]

    # except our 3 nodes and the optional ones
    turn_off_command += [ "~{}".format(x) for x in [hss,  epc, enb] + optional_ids]

    # only do the turn-off thing if load_nodes or reset_nodes
    if load_nodes or reset_nodes:
        job_off_nodes = SshJob(
            node = gwnode,
            # switch off all nodes but the ones we use
            command = turn_off_command,
            label = "turn off unused nodes",
            required = job_check_for_lease,
            scheduler = sched,
        )

    # actually run this in the gateway, not on the macphone
    # the ssh keys are stored in the gateway and we do not yet have
    # the tools to leverage such remote keys
    job_stop_phones = [ SshJob(
        node = gwnode,
        command = RunScript(
            # script
            locate_local_script("faraday.sh"),
            # arguments
            "macphone{}".format(id), "r2lab-embedded/shell/macphone.sh", "phone-off",
            # options
            includes = includes),
        label = "put phone{} in airplane mode".format(id),
        required = job_check_for_lease,
        scheduler = sched,
    ) for id in phones ]

    ########## prepare the image-loading phase
    # this will be a dict of items imagename -> ids
    to_load = defaultdict(list)
    to_load[image_gw] += [hss, epc]
    to_load[image_enb] += [enb]
    if e3372_ues:
        to_load[image_e3372_ue] += e3372_ues
    if oai_ues:
        to_load[image_oai_ue] += oai_ues
    if extras:
        to_load[image_extra] += extras
        
    prep_job_by_node = {}
    for image, nodes in to_load.items():
        commands = []
        if load_nodes:
            commands.append(Run("rhubarbe", "usrpoff", *nodes))
            commands.append(Run("rhubarbe", "load", "-i", image, *nodes))
            commands.append(Run("rhubarbe", "usrpon", *nodes))
        elif reset_nodes:
            commands.append(Run("rhubarbe", "reset", *nodes))
        # always do this
        commands.append(Run("rhubarbe", "wait", "-t",  120, *nodes))
        job = SshJob(
            node = gwnode,
            commands = commands,
            label = "Prepare node(s) {}".format(nodes),
            required = job_check_for_lease,
            scheduler = sched,
        )
        for node in nodes:
            prep_job_by_node[node] = job


    # start services
    job_service_hss = SshJob(
        node = hssnode,
        command = RunScript(locate_local_script("oai-hss.sh"), "run-hss", epc,
                            includes = includes),
        label = "start HSS service",
        required = prep_job_by_node[hss],
        scheduler = sched,
    )

    delay = 15
    job_service_epc = SshJob(
        node = epcnode,
        commands = [
            Run("echo giving HSS {delay}s to warm up; sleep {delay}"
                .format(delay=delay)),
            RunScript(locate_local_script("oai-epc.sh"), "run-epc", hss,
                      includes = includes),
        ],
        label = "start EPC services",
        required = prep_job_by_node[epc],
        scheduler = sched,
    )

    ########## enodeb

    # start service
    
    # this longer delay is required to avoid cx issue occuring when loading images
    delay = 40 if load_nodes else 15

    job_service_enb = SshJob(
        node = enbnode,
        # run-enb expects the id of the epc as a parameter
        # n_rb means number of resource blocks for DL, set to either 25 or 50.
        commands = [
            Run("echo Waiting for {delay}s for EPC to warm up; sleep {delay}"
                .format(delay=delay)),
            RunScript(locate_local_script("oai-enb.sh"),
                      "run-enb", epc, n_rb, not skip_reset_usb,
                      includes = includes),
        ],
        label = "start softmodem on eNB",
        required = (prep_job_by_node[enb], job_service_hss, job_service_epc),
        scheduler = sched,
    )

    ########## run experiment per se
    
    # the phone
    # we need to wait for the SDR firmware to be loaded
    duration = 30 if not skip_reset_usb else 8
    msg = "wait for enodeb firmware to load on the SDR device".format(duration)
    job_wait_enb = Job(
        verbose_delay(duration, msg),
        label = msg,
        required = job_service_enb,
        scheduler = sched,
    )
    
    job_start_phones = [ SshJob(
        node = gwnode,
        commands = [
            RunScript(locate_local_script("faraday.sh"),
                      "macphone{}".format(id), "r2lab-embedded/shell/macphone.sh", "phone-on",
                      includes=includes),
            RunScript(locate_local_script("faraday.sh"),
                      "macphone{}".format(id), "r2lab-embedded/shell/macphone.sh", "phone-start-app",
                      includes=includes),
        ],
        label = "start Nexus phone and speedtest app",
        required = job_wait_enb,
    ) for id in phones ]

    job_ping_phones_from_epc = [ SshJob(
        node = epcnode,
        commands = [
            Run("sleep 10"),
            Run("ping -c 100 -s 100 -i .05 172.16.0.{ip} &> /root/ping-phone".format(ip=id+1)),
            ],
        label = "ping Nexus phone from EPC",
        critical = False,
        required = job_start_phones,
    ) for id in phones ]

    ########## extra nodes

    colors = [ "wheat", "gray", "white", "darkolivegreen" ]

    for extra, color in zip(extras, itertools.cycle(colors)):
        extra_node = SshNode(
            gateway = gwnode, hostname = r2lab_hostname(extra), username='root',
            formatter = ColonFormatter(verbose=verbose), debug=verbose)
        SshJob(
            node = extra_node,
            command = Run("xterm -fn -*-fixed-medium-*-*-*-20-*-*-*-*-*-*-*"
                          " -bg {} -geometry 90x10".format(color),
                          x11=True),
            label = "xterm on node {}".format(extra_node.hostname),
            required = prep_job_by_node[extra],
            scheduler = sched,
            # don't set forever; if we do, then these xterms get killed
            # when all other tasks have completed
            # forever = True,
            )
#    # remove dangling requirements - if any - should not be needed but won't hurt either
    sched.sanitize()
    
    print(20*"*", "nodes usage summary")
    if load_nodes:
        for image, nodes in to_load.items():
            for node in nodes:
                print("node {node} : {image}".format(node=node, image=image))
    elif reset_nodes:
        for image, nodes in to_load.items():
            for node in nodes:
                print("reset of node {node}".format(node=node))
    else:
        print("NODES ARE USED AS IS (no image loaded, no reset)")

    sched.rain_check()
    # Update the .dot and .png file for illustration purposes
    if verbose or dry_run:
        sched.list()
        name = "scenario-load" if load_nodes else \
               "scenario-reset" if reset_nodes else \
               "scenario"
        sched.export_as_dotfile("{}.dot".format(name))
        os.system("dot -Tpng {}.dot -o {}.png".format(name, name))

    if dry_run:
        return False
        
    input('OK ? - press control C to abort ? ')

    if not sched.orchestrate():
        print("RUN KO : {}".format(sched.why()))
        sched.debrief()
        return False
    else:
        print("RUN OK")
        return True

# use the same signature in addition to run_name by convenience
def collect(run_name, slice, hss, epc, enb, verbose):
    """
    retrieves all relevant logs under a common name 
    otherwise, same signature as run() for convenience

    retrieved stuff will be 3 compressed tars named
    <run_name>-(hss|epc|enb).tar.gz

    xxx - todo - it would make sense to also unwrap them all 
    in a single place locally, like what "logs.sh unwrap" does
    """

    gwuser, gwhost = parse_slice(slice)
    gwnode = SshNode(hostname = gwhost, username = gwuser,
                     formatter = ColonFormatter(verbose=verbose), debug=verbose)

    functions = "hss", "epc", "enb"

    hostnames = hssname, epcname, enbname = [ r2lab_hostname(x) for x in (hss, epc, enb) ]
    
    nodes = hssnode, epcnode, enbnode = [
        SshNode(gateway = gwnode, hostname = hostname, username = 'root',
                formatter = ColonFormatter(verbose=verbose), debug=verbose)
        for hostname in hostnames
    ]

    # first run a 'capture' function remotely to gather all the relevant
    # info into a single tar named <run_name>.tgz

    capturers = [
        SshJob(
            node = node,
            command = RunScript(locate_local_script("oai-common.sh"), "capture-{}".format(function), run_name,
                                includes = [locate_local_script("oai-{}.sh".format(function))]),
            label = "capturer on {}".format(function),
            # capture-enb will run oai-as-enb and thus requires oai-enb.sh
        )
        for (node, function) in zip(nodes, functions) ]
        
    collectors = [
        SshJob(
            node = node,
            command = Pull(remotepaths = [ "{}-{}.tgz".format(run_name, function) ],
                           localpath = "."),
            label = "collector on {}".format(function),
            required = capturers,
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
        print("local directory {} already exists = NOT UNWRAPPED !".format(run_name))
        return
    os.mkdir(run_name)
    local_tars = [ "{run_name}-{ext}.tgz".format(run_name=run_name, ext=ext) for ext in ['hss', 'epc', 'enb']]
    for tar in local_tars:
        print("Untaring {} in {}".format(tar, run_name))
        os.system("tar -C {} -xzf {}".format(run_name, tar))
            
        
def main():

    def_slice = "inria_oai@faraday.inria.fr"
    # WARNING: initially we used 37 and 36 for hss and epc,
    # but these boxes now have a USRP N210 and can't use the data network anymore
    def_hss, def_epc, def_enb, def_scr = 7, 8, 23, 6
    
    def_image_gw  = "oai-cn"
    def_image_enb = "oai-enb"
    def_image_extra = "gnuradio"
    def_image_oai_ue = "oai-ue"
    def_image_e3372_ue = "e3372-ue"

    # raw formatting (for -x mostly) + show defaults
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, RawTextHelpFormatter
    class RawAndDefaultsFormatter(ArgumentDefaultsHelpFormatter, RawTextHelpFormatter):
        pass
    parser = ArgumentParser(formatter_class=RawAndDefaultsFormatter)
    
    parser.add_argument("-s", "--slice", default=def_slice,
                        help="slice to use for entering")

    parser.add_argument("--hss", default=def_hss,
                        help="""id of the node that runs the HSS"""
                        .format(def_hss))
    parser.add_argument("--epc", default=def_epc,
                        help="""id of the node that runs the EPC"""
                        .format(def_epc))
    parser.add_argument("--enb", default=def_enb,
                        help="""id of the node that runs the eNodeB',
requires a USRP b210 and 'duplexer for eNodeB'""")

    parser.add_argument("-p", "--phones", dest='phones',
                        action=ListOfChoices, type=int, choices=(1, 2),
                        default=[1],
                        help='Commercial phones to use')

    e3372_nodes = hardware_map['E3372-UE']
    parser.add_argument("-e", "--e3372", dest='e3372_ues', default=[],
                        action=ListOfChoices, type=int, choices=e3372_nodes,
                        help ="""id(s) of nodes to be used as a E3372-based UE
choose among {}"""
                        .format(e3372_nodes))

    oaiue_nodes = hardware_map['OAI-UE']
    parser.add_argument("-u", "--oai-ue", dest='oai_ues', default=[],
                        action=ListOfChoices, type=int, choices=oaiue_nodes,
                        help ="""id(s) of nodes to be used as a OAI-based UE
choose among {} - note that these notes are also
suitable for scrambling the 2.54 GHz uplink"""
                        .format(oaiue_nodes))


    extras_help = """id(s) of extra nodes to run;
these nodes typically run a gnuradio image and X11-based graphical
tools for demos; 
prefer using fit10 and fit11 (B210 without duplexer)"""
    parser.add_argument("-x", "--xterm", dest='extras', default=[], action='append',
                        help = extras_help)

    parser.add_argument("-l", "--load", dest='load_nodes', action='store_true', default=False,
                        help='load images as well')
    parser.add_argument("-r", "--reset", dest='reset_nodes', action='store_true', default=False,
                        help='reset nodes instead of loading images')
    parser.add_argument("-f", "--fast", dest="skip_reset_usb",
                        default=False, action='store_true',
                        help="""Skip resetting the USB boards if set""")

    parser.add_argument("--image-gw", default=def_image_gw,
                        help="image to load in hss and epc nodes"
                        .format(def_image_gw))
    parser.add_argument("--image-enb", default=def_image_enb,
                        help="image to load in enb node"
                        .format(def_image_enb))
    parser.add_argument("--image-e3372-ue", default=def_image_e3372_ue,
                        help="image to load in e3372 UE nodes"
                        .format(def_image_e3372_ue))
    parser.add_argument("--image-oai-ue", default=def_image_oai_ue,
                        help="image to load in OAI UE nodes"
                        .format(def_image_oai_ue))
    parser.add_argument("--image-extra", default=def_image_extra,
                        help="image to load in extra nodes"
                        .format(def_image_extra))


    parser.add_argument("-N", "--n-rb", dest='n_rb',
                        default=25,
                        type=int,
                        choices=[25, 50],
                        help="specify the Number of Resource Blocks (NRB) for the downlink")

    parser.add_argument("-v", "--verbose", action='store_true', default=False)
    parser.add_argument("-n", "--dry-run", action='store_true', default=False)

    args = parser.parse_args()
    
    # we pass to run and collect exactly the set of arguments known to parser
    # build a dictionary with all the values in the args
    kwds = args.__dict__.copy()

    # actually run it
    print("Experiment STARTING at {}".format(time.strftime("%H:%M:%S")))
    if not run(**kwds):
        print("exiting")
        return

    print("Experiment READY at {}".format(time.strftime("%H:%M:%S")))
    # then prompt for when we're ready to collect
    try:
        run_name = input("type capture name when ready : ")
        if not run_name:
            raise KeyboardInterrupt
        collect(run_name, args.slice, args.hss, args.epc, args.enb, args.verbose)
    except KeyboardInterrupt as e:
        print("OK, skipped collection, bye")
    
    # this should maybe be taken care of in asynciojobs
    asyncio.get_event_loop().close()

main()
