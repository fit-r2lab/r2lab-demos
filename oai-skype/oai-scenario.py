#!/usr/bin/env python3

import os.path
import asyncio

from asynciojobs import Engine, Job, Sequence

from apssh import SshNode, SshJob, SshJobScript, SshJobCollector
from apssh.formatters import ColonFormatter

def r2lab_hostname(x):
    """
    Return a valid hostname from a name like either
    1 (int), 1(str), 01, fit1 or fit01 ...
    """
    return "fit{:02d}".format(int(str(x).replace('fit','')))

def script(s):
    """
    all the scripts are located in the same place
    """
    paths = [ "../../infra/user-env",
              os.path.expanduser("~/git/r2lab/infra/user-env/"), 
              os.path.expanduser("~/r2lab/infra/user-env/"),
              ]
    for path in paths:
        candidate = os.path.join(path, s)
        if os.path.exists(candidate):
            return candidate

async def verbose_delay(duration, *args):
    print(20*'*', "Waiting for {} s".format(duration), *args)
    await asyncio.sleep(duration)
    print("Done waiting for {} s".format(duration), *args)

# include the same set of utility scripts
includes = [ script(x) for x in [
    "r2labutils.sh", "nodes.sh", "oai-common.sh",
] ]

def run(slice, hss, epc, enb, extras, load_nodes, image_gw, image_enb,
        reset_nodes, reset_usrp, verbose, debug):
    """
    expects e.g.
    * slice : s.t like onelab.inria.oai.oai_build@faraday.inria.fr
    * hss : 23
    * epc : 16
    * enb : 19
    * extras : a list of ids that will be loaded with the gnuradio image

    Plus
    * load_nodes: whether to load images or not - in which case image_gw and image_enb
                  are used to tell the image names
    * reset_nodes: if load_nodes is false and reset_nodes is true, the nodes are reset - i.e. rebooted
    * reset_usrp : if not False, the USRP board won't be reset - makes it all much
    * otherwise (both False): do nothing
    """

    # what argparse knows as a slice actually is a gateway (user + host)
    gwuser, gwhost = slice.split('@')
    gwnode = SshNode(hostname = gwhost, username = gwuser,
                     formatter = ColonFormatter(verbose=verbose), debug=debug)

    hostnames = hssname, epcname, enbname = [ r2lab_hostname(x) for x in (hss, epc, enb) ]
    extra_hostnames = [ r2lab_hostname(x) for x in extras ]
    
    hssnode, epcnode, enbnode = [
        SshNode(gateway = gwnode, hostname = hostname, username = 'root',
                formatter = ColonFormatter(verbose=verbose), debug=debug)
        for hostname in hostnames
    ]

    ########## preparation
    check_for_lease = SshJob(
        node = gwnode,
        command = [ "rhubarbe", "leases", "--check" ],
        label = "check we have a current lease",
    )

    # turn off all nodes 
    turn_off_command = [ "rhubarbe", "off", "-a"]
    # except our 3 nodes and the optional extras
    turn_off_command += [ "~{}".format(x) for x in [hss,  epc, enb] + extras]

    off_nodes = SshJob(
        node = gwnode,
        # switch off all nodes but the ones we use
        command = turn_off_command,
        label = "turn off unused nodes",
        required = check_for_lease,
    )

    # actually run this in the gateway, not on the mac
    # the ssh keys are stored in the gateway and we do not yet have
    # the tools to leverage such remote keys
    stop_phone = SshJobScript(
        node = gwnode,
        command = [ script("faraday.sh"), "macphone", "r2lab/infra/user-env/macphone.sh", "phone-off" ],
        includes = includes,
        label = "stop phone",
        required = check_for_lease,
    )

    prepares = (check_for_lease, off_nodes, stop_phone)

    ##########
    # 3 methods to get nodes ready
    # (*) load images
    # (*) reset nodes that are known to have the right image
    # (*) do nothing, proceed to experiment
    if load_nodes:
        load_infra = SshJob(
            node = gwnode,
            commands = [
                [ "rhubarbe", "load", "-i", image_gw, hssname, epcname ],
                [ "rhubarbe", "wait", "-t",  120, hssname, epcname ],
            ],
            label = "load and wait HSS and EPC nodes",
            required = prepares,
        )

        load_enb = SshJob(
            node = gwnode,
            commands = [
                [ "rhubarbe", "load", "-i", image_enb, enbname ],
                [ "rhubarbe", "wait", "-t", 120, enbname ],
            ],
            label = "load and wait ENB",
            required = prepares,
        )
        
        loads = [load_infra, load_enb]
        
        if extras:
            # the image for this extra node is hard-wired for now
            image_extras = "gnuradio" # it's an alias to gr
            load_extras = SshJob(
                node = gwnode,
                commands = [
                    [ "rhubarbe", "load", "-i", image_extras ] + extra_hostnames,
                    [ "rhubarbe", "wait", "-t", 120 ] + extra_hostnames,
                    [ "rhubarbe", "usrpoff"] + extra_hostnames,
                    [ "rhubarbe", "usrpon"] + extra_hostnames,
                ],
                label = "load and wait extra nodes",
                required = prepares,
            )
            loads.append(load_extras)
            


    elif reset_nodes:
        
        reset_nodes = SshJob(
            node = gwnode,
            commands = [
                [ "rhubarbe", "reset", hss, epc, enb ],
                [ "rhubarbe", "wait", "--timeout", 120, "--verbose", hss, epc, enb ],
            ],
            label = "reset all nodes",
            required = prepares,
        )

        loads = [reset_nodes]

    else:
        loads = []

    ########## start services
    service_hss = SshJobScript(
        node = hssnode,
        command = [ script("oai-hss.sh"), "run-hss", epc ],
        includes = includes,
        label = "start HSS service",
        required = (prepares, loads),
    )

    msg = "wait for HSS to warm up"
    service_epc = Sequence(
        Job(
            verbose_delay(2, msg),
            label = msg,
            ), 
        SshJobScript(
            node = epcnode,
            command = [ script("oai-epc.sh"), "run-epc", hss ],
            includes = includes,
            label = "start EPC services",
        ),
        required = (prepares, loads, service_hss),
    )

    msg = "wait for EPC to warm up"
    service_enb = Sequence(
        Job(
            verbose_delay(2, msg),
            label = msg),
        SshJobScript(
            node = enbnode,
            # run-enb expects the id of the epc as a parameter
            command = [ script("oai-enb.sh"), "run-enb", epc, reset_usrp ],
            includes = includes,
            label = "start softmodem on ENB",
            ),
        required = (prepares, loads, service_hss, service_epc),
    )

    services = (service_hss, service_epc, service_enb)

    ########## run experiment per se
    # we need to wait for the USB firmware to be loaded
    duration = 30 if reset_usrp is not False else 8
    msg = "wait for {}s for 5G infrastructure to settle".format(duration)
    delay = Job(
        verbose_delay(duration, msg),
        label = msg,
        required = services
    )

    start_phone = SshJobScript(
        node = gwnode,
        commands = [
            [ script("faraday.sh"), "macphone", "r2lab/infra/user-env/macphone.sh", "phone-on" ],
            [ script("faraday.sh"), "macphone", "r2lab/infra/user-env/macphone.sh", "phone-start-app" ],
        ],
        includes = includes,
        label = "start phone 4g and speedtest app",
        required = delay,
    )

    ping_phone_from_epc = SshJob(
        node = epcnode,
        commands = [
            ["sleep 10"],
            ["ping -c 100 -s 100 -i .05 172.16.0.2 &> /root/ping-phone"],
            ],
        label = "ping phone from EPC",
        critical = False,
        required = delay,
    )

    runs = (delay, start_phone, ping_phone_from_epc)
    
    # schedule the load phases only if required
    e = Engine(verbose=verbose, debug=debug)
    # this is just a way to add a collection of jobs to the engine
    e.update(prepares)
    # loads contents depends on the --load or --reset options; might as well be empty
    e.update(loads)
    # always start services and exp
    e.update(services)
    e.update(runs)
    # remove dangling requirements - if any - should not be needed but won't hurt either
    e.sanitize(verbose=False)
    
    print(40*"*", "load_nodes = {} (gw->{}, enb->{}), reset_nodes = {}"
          .format(load_nodes, image_gw, image_enb, reset_nodes))
    e.rain_check()
    if verbose:
        e.list()
        name = "scenario-load" if load_nodes else \
               "scenario-reset" if reset_nodes else \
               "scenario"
        e.store_as_dotfile("{}.dot".format(name))
        os.system("dot -Tpng {}.dot -o {}.png".format(name, name))

    if not e.orchestrate():
        print("RUN KO : {}".format(e.why()))
        e.debrief()
        return False
    else:
        print("RUN OK")
        return True

# use the same signature in addition to run_name by convenience
def collect(run_name, slice, hss, epc, enb, verbose, debug):
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
                     formatter = ColonFormatter(verbose=verbose), debug=debug)

    functions = "hss", "epc", "enb"

    hostnames = hssname, epcname, enbname = [ r2lab_hostname(x) for x in (hss, epc, enb) ]
    
    nodes = hssnode, epcnode, enbnode = [
        SshNode(gateway = gwnode, hostname = hostname, username = 'root',
                formatter = ColonFormatter(verbose=verbose), debug=debug)
        for hostname in hostnames
    ]

    # first run a 'capture' function remotely to gather all the relevant
    # info into a single tar named <run_name>.tgz

    capturers = [
        SshJobScript(
            node = node,
            command = [ script("oai-common.sh"), "capture-{}".format(function), run_name ],
            label = "capturer on {}".format(function),
            # capture-enb will run oai-as-enb and thus requires oai-enb.sh
            includes = [script("oai-{}.sh".format(function))],
        )
        for (node, function) in zip(nodes, functions) ]
        
    collectors = [
        SshJobCollector(
            node = node,
            remotepaths = [ "{}-{}.tgz".format(run_name, function) ],
            localpath = ".",
            label = "collector on {}".format(function),
            required = capturer,
        )
        for (node, function, capturer) in zip(nodes, functions, capturers) ]

    e = Engine(verbose=verbose, debug=debug)
    e.update(capturers)
    e.update(collectors)
    
    if verbose:
        e.list()

    if not e.orchestrate():
        print("KO")
        e.debrief()
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

    def_slice = "onelab.inria.oai.oai_build@faraday.inria.fr"
# to enable the scrambler by default:
#    def_hss, def_epc, def_enb, def_scr = 37, 36, 19, 11
    def_hss, def_epc, def_enb, def_scr = 37, 36, 23, 6
    
    def_image_gw  = "u14.48-oai-gw"
    def_image_enb = "u14.319-oai-enb"

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
    parser.add_argument("-g", "--image-gw", default=def_image_gw,
                        help="image to load in hss and epc nodes (default={})"
                        .format(def_image_gw))
    parser.add_argument("-e", "--image-enb", default=def_image_enb,
                        help="image to load in enb and scrambler nodes (default={})"
                        .format(def_image_enb))

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

    parser.add_argument("-v", "--verbose", action='store_true', default=False)
    parser.add_argument("-d", "--debug", action='store_true', default=False)

    args = parser.parse_args()

    # we pass to run and collect exactly the set of arguments known to parser
    # build a dictionary with all the values in the args
    kwds = args.__dict__.copy()

    # actually run it
    if not run(**kwds):
        print("exiting")
        return

    # then prompt for when we're ready to collect
    try:
        run_name = input("type capture name when ready : ")
        if not run_name:
            raise KeyboardInterrupt
        collect(run_name, args.slice, args.hss, args.epc, args.enb, args.verbose, args.debug)
    except KeyboardInterrupt as e:
        print("OK, skipped collection, bye")
    

    
main()
