#!/usr/bin/env python3

import os.path
import time
import asyncio
import itertools

from asynciojobs import Scheduler, Job, Sequence

from apssh import SshNode, SshJob, Run, RunScript, Pull
from apssh.formatters import ColonFormatter

#from listofchoices import ListOfChoices

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
def run(slice, hss, epc, enb, extras, load_nodes, image_gw, image_enb, image_extra, image_oai_ue, image_e3372_ue, 
        oai_ue, reset_nodes, reset_usb, spawn_xterms, n_rb, phone1, phone2, verbose):
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
    * extras : a list of ids that will be loaded with the gnuradio image

    Plus
    * load_nodes: whether to load images or not - in which case
                  image_gw, image_enb and image_extra
                  are used to tell the image names
    * reset_nodes: if load_nodes is false and reset_nodes is true, the nodes are reset - i.e. rebooted
    * otherwise (both False): do nothing
    * reset_usb : if not False, the USRP board won't be reset
    * spawn_xterms : if set, starts xterm on all extra nodes
    * image_* : the name of the images to load on the various nodes
    * oai_ue: flag set to True if OAI UE image requested on extra nodes fit06/fit19
    * phone1: flag set to True if Nexus phone used as UE
    * phone2: flag set to True if Moto G phone used as UE
    """

    # what argparse knows as a slice actually is a gateway (user + host)
    gwuser, gwhost = parse_slice(slice)
    gwnode = SshNode(hostname = gwhost, username = gwuser,
                     formatter = ColonFormatter(verbose=verbose), debug=verbose)

    hostnames = hssname, epcname, enbname = [ r2lab_hostname(x) for x in (hss, epc, enb) ]
    extra_hostnames = [ r2lab_hostname(x) for x in extras ]
    
    hssnode, epcnode, enbnode = [
        SshNode(gateway = gwnode, hostname = hostname, username = 'root',
                formatter = ColonFormatter(verbose=verbose), debug=verbose)
        for hostname in hostnames
    ]

    extra_nodes = [
        SshNode(gateway = gwnode, hostname = hostname, username='root',
                formatter = ColonFormatter(verbose=verbose), debug=verbose)
        for hostname in extra_hostnames
    ]

    ########## preparation
    job_check_for_lease = SshJob(
        node = gwnode,
        command = [ "rhubarbe", "leases", "--check" ],
        label = "check we have a current lease",
    )

    # turn off all nodes 
    turn_off_command = [ "rhubarbe", "off", "-a"]
    # except our 3 nodes and the optional extras
#    turn_off_command += [ "~{}".format(x) for x in [hss,  epc, enb] + extras + [20]]
    turn_off_command += [ "~{}".format(x) for x in [hss,  epc, enb] + extras]

    job_off_nodes = SshJob(
        node = gwnode,
        # switch off all nodes but the ones we use
        command = turn_off_command,
        label = "turn off unused nodes",
        required = job_check_for_lease,
    )

    # actually run this in the gateway, not on the mac
    # the ssh keys are stored in the gateway and we do not yet have
    # the tools to leverage such remote keys
    job_stop_phone1 = SshJob(
        node = gwnode,
        command = RunScript(
            locate_local_script("faraday.sh"), "macphone", "r2lab-embedded/shell/macphone.sh", "phone-off",
            includes = includes),
        label = "stop Nexus phone",
        required = job_check_for_lease,
    )

    job_stop_phone2 = SshJob(
        node = gwnode,
        command = RunScript(
            locate_local_script("faraday.sh"), "macphone2", "r2lab-embedded/shell/macphone.sh", "phone-off",
            includes = includes),
        label = "stop Moto G phone",
        required = job_check_for_lease,
    )

    jobs_prepare = [job_check_for_lease]
    if phone1:
        jobs_prepare.append(job_stop_phone1)
    if phone2:
        jobs_prepare.append(job_stop_phone2)
    # turn off nodes only when --load or --reset is set
    if load_nodes or reset_nodes:
        jobs_prepare.append(job_off_nodes)

    ########## infra nodes hss + epc

    # prepare nodes
    
    commands = []
    if load_nodes:
        commands.append(Run("rhubarbe", "load", "-i", image_gw, hssname, epcname))
    elif reset_nodes:
        commands.append(Run("rhubarbe", "reset", hssname, epcname))
    # always do this
    commands.append(Run("rhubarbe", "wait", "-t",  120, hssname, epcname))
    job_load_infra = SshJob(
        node = gwnode,
        commands = commands,
        label = "load and wait HSS and EPC nodes",
        required = jobs_prepare,
    )

    # start services
    
    job_service_hss = SshJob(
        node = hssnode,
        command = RunScript(locate_local_script("oai-hss.sh"), "run-hss", epc,
                            includes = includes),
        label = "start HSS service",
        required = job_load_infra,
    )

    msg = "wait 15s for HSS to warm up before running EPC"
    job_service_epc = Sequence(
        # let 15 seconds to HSS 
        Job(
            verbose_delay(15, msg),
            label = msg,
            ), 
        SshJob(
            node = epcnode,
            command = RunScript(locate_local_script("oai-epc.sh"), "run-epc", hss,
                                includes = includes),
            label = "start EPC services",
        ),
        required = job_load_infra,
    )

    jobs_infra = job_load_infra, job_service_hss, job_service_epc

    ########## enodeb

    # prepare node

    commands = []
    if load_nodes:
        commands.append(Run("rhubarbe", "usrpoff", enb))
        commands.append(Run("rhubarbe", "load", "-i", image_enb, enb))
    elif reset_nodes:
        commands.append(Run("rhubarbe", "reset", enb))
    commands.append(Run("rhubarbe", "wait", "-t", "120", enb))
    
    job_load_enb = SshJob(
        node = gwnode,
        commands = commands,
        label = "load and wait eNB",
        required = jobs_prepare,
    )
        
    # start service
    
    if load_nodes:
        # this longer delay is required to avoid cx issue occuring when loading images
        msg = "wait 40s for EPC to warm up"
        delay = 40
    else:
        msg = "wait 15s for EPC to warm up"
        delay = 15

    job_service_enb = Sequence(
        Job(
            verbose_delay(delay, msg),
            label = msg),
        SshJob(
            node = enbnode,
            # run-enb expects the id of the epc as a parameter
            # n_rb means number of resource blocks for DL, set to either 25 or 50.
            command = RunScript(locate_local_script("oai-enb.sh"), "run-enb", epc, n_rb, reset_usb,
                                includes = includes),
            label = "start softmodem on eNB",
            ),
        required = (job_load_enb, job_service_hss, job_service_epc),
    )

    jobs_enb = job_load_enb, job_service_enb

    ########## run experiment per se
    
    # the phone
    # we need to wait for the SDR firmware to be loaded
    duration = 30 if reset_usb is not False else 8
    msg = "wait for enodeb firmware to load on the SDR device".format(duration)
    job_wait_enb = Job(
        verbose_delay(duration, msg),
        label = msg,
        required = job_service_enb)
    
    job_start_phone1 = SshJob(
        node = gwnode,
        commands = [
            RunScript(locate_local_script("faraday.sh"), "macphone", "r2lab-embedded/shell/macphone.sh", "phone-on",
                      includes=includes),
            RunScript(locate_local_script("faraday.sh"), "macphone", "r2lab-embedded/shell/macphone.sh", "phone-start-app",
                      includes=includes),
        ],
        label = "start Nexus phone and speedtest app",
        required = job_wait_enb,
    )

    job_ping_phone1_from_epc = SshJob(
        node = epcnode,
        commands = [
            Run("sleep 10"),
            Run("ping -c 100 -s 100 -i .05 172.16.0.2 &> /root/ping-phone"),
            ],
        label = "ping Nexus phone from EPC",
        critical = False,
        required = job_start_phone1,
    )

    job_start_phone2 = SshJob(
        node = gwnode,
        commands = [
            RunScript(locate_local_script("faraday.sh"), "macphone2", "r2lab-embedded/shell/macphone.sh", "phone-on",
                      includes=includes),
            RunScript(locate_local_script("faraday.sh"), "macphone2", "r2lab-embedded/shell/macphone.sh", "phone-start-app",
                      includes=includes),
        ],
        label = "start Moto G phone and speedtest app",
        required = job_wait_enb,
    )

    job_ping_phone2_from_epc = SshJob(
        node = epcnode,
        commands = [
            Run("sleep 10"),
            Run("ping -c 100 -s 100 -i .05 172.16.0.3 &> /root/ping-phone"),
            ],
        label = "ping Moto G phone from EPC",
        critical = False,
        required = job_start_phone2,
    )

    jobs_exp = [job_wait_enb,]
    if phone1:
        jobs_exp.append(job_start_phone1)
        jobs_exp.append(job_ping_phone1_from_epc)
    if phone2:
        jobs_exp.append(job_start_phone2)
        jobs_exp.append(job_ping_phone2_from_epc)

    ########## extra nodes
    # ssh -X not yet supported in apssh, so one option is to start them using
    # a local process
    # xxx to update: The following code kind of works, but it needs to be 
    # turned off, because the process in question would be killed
    # at the end of the Scheduler orchestration (at the end of the run function)
    # which is the exact time where it would be useful :)
    # however the code for LocalJob appears to work fine, it would be nice to
    # move it around - maybe in apssh ?

    e3372_ue_hostnames, oai_ue_hostnames, gnuradio_hostnames = [], [], []
    commands_e3372_ue, commands_oai_ue, commands_gnuradio = [], [], []

    for host in extra_hostnames:
        if host == "fit02" or host == "fit26":
            e3372_ue_hostnames.append(host)
        elif oai_ue and (host == "fit06" or host == "fit19"):
            oai_ue_hostnames.append(host)
        else:
            gnuradio_hostnames.append(host)

    if e3372_ue_hostnames:
        commands_e3372_ue.append(Run("rhubarbe", "usrpoff", *e3372_ue_hostnames))
        if load_nodes:
            commands_e3372_ue.append(Run("rhubarbe", "load", "-i", image_e3372_ue, *e3372_ue_hostnames))
        elif reset_nodes:
            commands_e3372_ue.append(Run("rhubarbe", "reset", *e3372_ue_hostnames))
        commands_e3372_ue.append(Run("rhubarbe", "wait", "-t", "120", *e3372_ue_hostnames))

    job_load_e3372_ue = SshJob(
        node = gwnode,
        commands = commands_e3372_ue,
        label = "load and wait Huawei e3372 extra nodes",
        required = job_check_for_lease,
    )

    if oai_ue_hostnames:
        commands_oai_ue.append(Run("rhubarbe", "usrpoff", *oai_ue_hostnames))
        if load_nodes:
            commands_oai_ue.append(Run("rhubarbe", "load", "-i", image_oai_ue, *oai_ue_hostnames))
        elif reset_nodes:
            commands_oai_ue.append(Run("rhubarbe", "reset", *oai_ue_hostnames))
        commands_oai_ue.append(Run("rhubarbe", "wait", "-t", "120", *oai_ue_hostnames))

    job_load_oai_ue = SshJob(
        node = gwnode,
        commands = commands_oai_ue,
        label = "load and wait OAI UE extra nodes",
        required = job_check_for_lease,
    )

    if gnuradio_hostnames:
        if load_nodes:
            commands_gnuradio.append(Run("rhubarbe", "usrpoff", *gnuradio_hostnames))
            commands_gnuradio.append(Run("rhubarbe", "load", "-i", image_extra, *gnuradio_hostnames))
            commands_gnuradio.append(Run("rhubarbe", "wait", "-t", 120, *gnuradio_hostnames))
            commands_gnuradio.append(Run("rhubarbe", "usrpon", *gnuradio_hostnames))
        elif reset_nodes:
            commands_gnuradio.append(Run("rhubarbe", "reset", *gnuradio_hostnames))
        commands_gnuradio.append(Run("rhubarbe", "wait", "-t", "120", *gnuradio_hostnames))

    job_load_gnuradio = SshJob(
        node = gwnode,
        commands = commands_gnuradio,
        label = "load and wait extra gnuradio nodes",
        required = job_check_for_lease,
    )

    jobs_extras = []
    extras_load = ""
    if e3372_ue_hostnames:
        jobs_extras.append(job_load_e3372_ue)
        extras_load += "{} ".format(image_e3372_ue)
    if oai_ue_hostnames:
        jobs_extras.append(job_load_oai_ue)
        extras_load += "{} ".format(image_oai_ue)
    if gnuradio_hostnames:
        jobs_extras.append(job_load_gnuradio)
        extras_load += "{} ".format(image_extra)

    colors = [ "wheat", "gray", "white"]

    if spawn_xterms:
        jobs_xterms_extras = [
            SshJob(
                node = extra_node,
                command = Run("xterm -fn -*-fixed-medium-*-*-*-20-*-*-*-*-*-*-*"
                              " -bg {} -geometry 90x10".format(color),
                              x11=True),
                label = "xterm on node {}".format(extra_node.hostname),
                required = (job_load_e3372_ue, job_load_oai_ue, job_load_gnuradio),
                # don't set forever; if we do, then these xterms get killed
                # when all other tasks have completed
                # forever = True,
            ) for extra_node, color in zip(extra_nodes, itertools.cycle(colors))
        ]
        jobs_extras.append(jobs_xterms_extras)

    # schedule the load phases only if required
    sched = Scheduler(verbose=verbose)
    # this is just a way to add a collection of jobs to the scheduler
    sched.update(jobs_prepare)
    sched.update(jobs_infra)
    sched.update(jobs_enb)
    sched.update(jobs_exp)
    if jobs_extras:
        sched.update(jobs_extras)
    # remove dangling requirements - if any - should not be needed but won't hurt either
    sched.sanitize()
    
    print(40*"*")
    if load_nodes:
        if not extras_load:
            print("LOADING IMAGES: (gw->{}, enb->{} WITHOUT EXTRAS)"
                  .format(image_gw, image_enb))
        else:
            print("LOADING IMAGES: (gw->{}, enb->{}, WITH FOLLOWING EXTRAS->{})"
                  .format(image_gw, image_enb, extras_load))
    elif reset_nodes:
        print("RESETTING NODES")
    else:
        print("NODES ARE USED AS IS (no image loaded, no reset)")
    
    sched.rain_check()
    # Update the .dot and .png file for illustration purposes
    if verbose:
        sched.list()
        name = "scenario-load" if load_nodes else \
               "scenario-reset" if reset_nodes else \
               "scenario"
        sched.export_as_dotfile("{}.dot".format(name))
        os.system("dot -Tpng {}.dot -o {}.png".format(name, name))

    sched.list()

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

    from argparse import ArgumentParser, RawTextHelpFormatter
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    # xxx faire une première phase de vérifications diverses (clés, scripts, etc..)
    # xxx ajouter une option -k pour spécifier une clé ssh
    parser.add_argument("-s", "--slice", default=def_slice,
                        help="defaults to {}".format(def_slice))

    parser.add_argument("-l", "--load", dest='load_nodes', action='store_true', default=False,
                        help='load images as well')
    parser.add_argument("-r", "--reset", dest='reset_nodes', action='store_true', default=False,
                        help='reset nodes instead of loading images')
    parser.add_argument("--image-gw", default=def_image_gw,
                        help="image to load in hss and epc nodes (default to {})"
                        .format(def_image_gw))
    parser.add_argument("--image-enb", default=def_image_enb,
                        help="image to load in enb node (default to {})"
                        .format(def_image_enb))
    parser.add_argument("--image-extra", default=def_image_extra,
                        help="image to load in extra nodes (default to {})"
                        .format(def_image_extra))
    parser.add_argument("--image-oai-ue", default=def_image_oai_ue,
                        help="image to load in OAI UE nodes (default to {})"
                        .format(def_image_oai_ue))
    parser.add_argument("--image-e3372-ue", default=def_image_e3372_ue,
                        help="image to load in e3372 UE nodes (default to {})"
                        .format(def_image_e3372_ue))
    parser.add_argument("-o", "--oai-ue", dest='oai_ue', action='store_true', default=False,
                        help='load OAI UE image in case extra node fit06/fit19 is/are selected')

    parser.add_argument("-f", "--fast", dest="reset_usb", default=True, action='store_false')

    parser.add_argument("--hss", default=def_hss,
                        help="""id of the node that runs the HSS (defaults to {})"""
                        .format(def_hss))
    parser.add_argument("--epc", default=def_epc,
                        help="""id of the node that runs the EPC (defaults to {})"""
                        .format(def_epc))
    parser.add_argument("--enb", default=def_enb,
                        help='\n'.join(['id of the node that runs the eNodeB',
                        'requires a USRP b210 and duplexer for eNodeB', 
                        'defaults to {}']).format(def_enb))
    parser.add_argument("-x", "--extra", dest='extras', default=[], action='append',
                        help='\n'.join(['id of (an) extra node(s) to run;',
                        'theses nodes are of 3 types, depending on the id number selected:',
                        '\t2 or 26) Huawei e3372 UE extra node',
                        '\t6 or 19) for OAI UE or uplink 2.54GHz scrambler extra node, depending on the oai-ue flag',
                        '\t*) scrambler or observer node with gnuradio image',
                        '\t  --prefer using fit10 and fit11 (B210 without duplexer)']))
    parser.add_argument("-X", "--xterm", dest='spawn_xterms', default=False, action='store_true',
                        help="if set, spawns xterm on all extra nodes")
    parser.add_argument("-N", "--n-rb", dest='n_rb',
                        default=25,
                        type=int,
                        choices=[25, 50],
                        help="specify the Number of Resource Blocks (NRB) for the downlink")
    parser.add_argument("--nophone1", dest='phone1', action='store_false', default=True,
                        help='Disable use of Nexus Phone, used by default')
    parser.add_argument("--phone2", dest='phone2', action='store_true', default=False,
                        help='Enable use of Moto G Phone')

    parser.add_argument("-v", "--verbose", action='store_true', default=False)

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
