#!/usr/bin/env python3

import os.path
import time
import asyncio

from asynciojobs import Scheduler, Job, Sequence

from apssh import SshNode, SshJob, Run, RunScript, Pull
from apssh.formatters import ColonFormatter

# to be added to apssh
from localjob import LocalJob

def r2lab_hostname(x):
    """
    Return a valid hostname from a name like either
    1 (int), 1(str), 01, fit1 or fit01 ...
    """
    return "fit{:02d}".format(int(str(x).replace('fit','')))

def locate_local_script(s):
    """
    all the scripts are located in the same place
    find that place among a list of possible locations
    """
    paths = [
        "../../infra/user-env",
        os.path.expanduser("~/git/r2lab/infra/user-env/"), 
        os.path.expanduser("~/r2lab/infra/user-env/"),
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
def run(slice, hss, epc, enb, extras, load_nodes, image_gw, image_enb, image_extra,
        reset_nodes, reset_usrp, spawn_xterms, verbose):
    """
    ##########
    # 3 methods to get nodes ready
    # (*) load images
    # (*) reset nodes that are known to have the right image
    # (*) do nothing, proceed to experiment

    expects e.g.
    * slice : s.t like inria_oai.skype@faraday.inria.fr
    * hss : 23
    * epc : 16
    * enb : 19
    * extras : a list of ids that will be loaded with the gnuradio image

    Plus
    * load_nodes: whether to load images or not - in which case
                  image_gw, image_enb and image_extra
                  are used to tell the image names
    * reset_nodes: if load_nodes is false and reset_nodes is true, the nodes are reset - i.e. rebooted
    * otherwise (both False): do nothing
    * reset_usrp : if not False, the USRP board won't be reset
    * spawn_xterms : if set, starts xterm on all extra nodes
    * image_* : the name of the images to load on the various nodes
    """

    # what argparse knows as a slice actually is a gateway (user + host)
    gwuser, gwhost = slice.split('@')
    gwnode = SshNode(hostname = gwhost, username = gwuser,
                     formatter = ColonFormatter(verbose=verbose), debug=verbose)

    hostnames = hssname, epcname, enbname = [ r2lab_hostname(x) for x in (hss, epc, enb) ]
    extra_hostnames = [ r2lab_hostname(x) for x in extras ]
    
    hssnode, epcnode, enbnode = [
        SshNode(gateway = gwnode, hostname = hostname, username = 'root',
                formatter = ColonFormatter(verbose=verbose), debug=verbose)
        for hostname in hostnames
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
    job_stop_phone = SshJob(
        node = gwnode,
        command = RunScript(
            locate_local_script("faraday.sh"), "macphone", "r2lab/infra/user-env/macphone.sh", "phone-off",
            includes = includes),
        label = "stop phone",
        required = job_check_for_lease,
    )

    jobs_prepare = [job_check_for_lease, job_stop_phone]
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

    msg = "wait for HSS to warm up"
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
        label = "load and wait ENB",
        required = jobs_prepare,
    )
        
    # start service
    
    msg = "wait for EPC to warm up"
    job_service_enb = Sequence(
        Job(
            verbose_delay(15, msg),
            label = msg),
        SshJob(
            node = enbnode,
            # run-enb expects the id of the epc as a parameter
            command = RunScript(locate_local_script("oai-enb.sh"), "run-enb", epc, reset_usrp,
                                includes = includes),
            label = "start softmodem on ENB",
            ),
        required = (job_load_enb, job_service_hss, job_service_epc),
    )

    jobs_enb = job_load_enb, job_service_enb

    ########## run experiment per se
    
    # the phone
    # we need to wait for the USB firmware to be loaded
    duration = 30 if reset_usrp is not False else 8
    msg = "wait for enodeb firmware to load on USRP".format(duration)
    job_wait_enb = Job(
        verbose_delay(duration, msg),
        label = msg,
        required = job_service_enb)
    
    job_start_phone = SshJob(
        node = gwnode,
        commands = [
            RunScript(locate_local_script("faraday.sh"), "macphone", "r2lab/infra/user-env/macphone.sh", "phone-on",
                      includes=includes),
            RunScript(locate_local_script("faraday.sh"), "macphone", "r2lab/infra/user-env/macphone.sh", "phone-start-app",
                      includes=includes),
        ],
        label = "start phone 4g and speedtest app",
        required = job_wait_enb,
    )

    job_ping_phone_from_epc = SshJob(
        node = epcnode,
        commands = [
            Run("sleep 10"),
            Run("ping -c 100 -s 100 -i .05 172.16.0.2 &> /root/ping-phone"),
            ],
        label = "ping phone from EPC",
        critical = False,
        required = job_wait_enb,
    )

    jobs_exp = job_wait_enb, job_start_phone, job_ping_phone_from_epc

    ########## extra nodes
    # ssh -X not yet supported in apssh, so one option is to start them using
    # a local process
    # xxx to update: The following code kind of works, but it needs to be 
    # turned off, because the process in question would be killed
    # at the end of the Scheduler orchestration (at the end of the run function)
    # which is the exact time where it would be useful :)
    # however the code for LocalJob appears to work fine, it would be nice to
    # move it around - maybe in apssh ?

    commands = []
    if not extras:
        commands.append(Run("echo no extra nodes specified - ignored"))
    else:
        if load_nodes:
            commands.append(Run("rhubarbe", "usrpoff", *extra_hostnames))
            commands.append(Run("rhubarbe", "load", "-i", image_extra, *extra_hostnames))
            commands.append(Run("rhubarbe", "wait", "-t", 120, *extra_hostnames))
            commands.append(Run("rhubarbe", "usrpon", *extra_hostnames))
        elif reset_nodes:
            commands.append(Run("rhubarbe", "reset", extra_hostnames))
        commands.append(Run("rhubarbe", "wait", "-t", "120", *extra_hostnames))
    job_load_extras = SshJob(
        node = gwnode,
        commands = commands,
        label = "load and wait extra nodes",
        required = job_check_for_lease,
    )
                             
    jobs_extras = [job_load_extras]

    if spawn_xterms:
        jobs_xterms_extras = [
            LocalJob(command = "ssh -X {} ssh -X root@fit{} xterm".format(slice, extra),
                     label = "xterm on node {}".format(extra),
                     required = job_load_extras,
                     forever = True,
                     eternal = True,
                 ) for extra in extras
        ]
        jobs_extras += jobs_xterms_extras

    # schedule the load phases only if required
    sched = Scheduler(verbose=verbose)
    # this is just a way to add a collection of jobs to the scheduler
    sched.update(jobs_prepare)
    sched.update(jobs_infra)
    sched.update(jobs_enb)
    sched.update(jobs_exp)
    sched.update(jobs_extras)
    # remove dangling requirements - if any - should not be needed but won't hurt either
    sched.sanitize()
    
    print(40*"*")
    if load_nodes:
        print("LOADING IMAGES: (gw->{}, enb->{}, extras->{})"
              .format(load_nodes, image_gw, image_enb, image_extra))
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

    gwuser, gwhost = slice.split('@')
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
            required = capturer,
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

    def_slice = "inria_oai.skype@faraday.inria.fr"
# to enable the scrambler by default:
#    def_hss, def_epc, def_enb, def_scr = 37, 36, 19, 11
    def_hss, def_epc, def_enb, def_scr = 37, 36, 23, 6
    
    def_image_gw  = "u14.48-oai-gw"
    def_image_enb = "u14.319-oai-enb"
    def_image_extra = "gnuradio"

    from argparse import ArgumentParser
    parser = ArgumentParser()
    # xxx faire une première phase de vérifications diverses (clés, scripts, etc..)
    # xxx ajouter une option -k pour spécifier une clé ssh
    parser.add_argument("-s", "--slice", default=def_slice,
                        help="defaults to {}".format(def_slice))

    parser.add_argument("-l", "--load", dest='load_nodes', action='store_true', default=False,
                        help='load images as well')
    parser.add_argument("-r", "--reset", dest='reset_nodes', action='store_true', default=False,
                        help='reset nodes instead of loading images')
    parser.add_argument("--image-gw", default=def_image_gw,
                        help="image to load in hss and epc nodes (default={})"
                        .format(def_image_gw))
    parser.add_argument("--image-enb", default=def_image_enb,
                        help="image to load in enb node (default={})"
                        .format(def_image_enb))
    parser.add_argument("--image-extra", default=def_image_extra,
                        help="image to load in extra nodes (default={})"
                        .format(def_image_extra))

    parser.add_argument("-f", "--fast", dest="reset_usrp", default=True, action='store_false')

    parser.add_argument("--hss", default=def_hss,
                        help="""id of the node that runs the HSS
                        / defaults to {}"""
                        .format(def_hss))
    parser.add_argument("--epc", default=def_epc,
                        help="""id of the node that runs the EPC
                        / defaults to {}"""
                        .format(def_epc))
    parser.add_argument("--enb", default=def_enb,
                        help="""id of the node that runs the eNodeB
                        / requires a USRP b210 for now 
                        / defaults to {}"""
                        .format(def_enb))
    parser.add_argument("-x", "--extra", dest='extras', default=[], action='append',
                        help="""id of an extra node(s) for scrambling or observation;
                        will be loaded with the gnuradio image""")
    parser.add_argument("-X", "--xterm", dest='spawn_xterms', default=False, action='store_true',
                        help="if set, spawns xterm on all extra nodes")

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
