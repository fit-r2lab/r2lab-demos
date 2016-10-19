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

# include the same set of utility scripts
includes = [ script(x) for x in [
    "r2labutils.sh", "nodes.sh", "oai-common.sh",
] ]

def run(slice, hss, epc, enb, scr, do_load, do_reset, ubuntu, verbose, debug):
    """
    expects e.g.
    * slice : s.t like onelab.inria.oai.oai_build@faraday.inria.fr
    * hss : 23
    * epc : 16
    * enb : 19

    Plus
    * do_load: whether to load images or not (in which case ubuntu is used to find the image name)
    * do_reset: if do_load is false and do_reset is true, the nodes are reset
    * otherwise (both False): do nothing
    """

    # what argparse knows as a slice actually is a gateway (user + host)
    gwuser, gwhost = slice.split('@')
    gwnode = SshNode(hostname = gwhost, username = gwuser,
                     formatter = ColonFormatter(verbose=verbose), debug=debug)

    hostnames = hssname, epcname, enbname, scrname = [ r2lab_hostname(x) for x in (hss, epc, enb, scr) ]
    
    hssnode, epcnode, enbnode, scrnode = [
        SshNode(gateway = gwnode, hostname = hostname, username = 'root',
                formatter = ColonFormatter(verbose=verbose), debug=debug)
        for hostname in hostnames
    ]

    # preparation
    check_for_lease = SshJob(
        node = gwnode,
        command = [ "rhubarbe", "leases", "--check" ],
        label = "check we have a current lease",
    )

    off_nodes = SshJob(
        node = gwnode,
        # switch off all nodes but the ones we use
        command = [ "rhubarbe", "off", "1-37", "~{},~{},~{},~{}".format(hss,  epc, enb, scr)],
        label = "turn off unused nodes",
        required = check_for_lease,
    )

    stop_phone = SshJobScript(
        node = gwnode,
        command = [ script("faraday.sh"), "macphone", "r2lab/infra/user-env/macphone.sh", "phone-off" ],
        includes = includes,
        label = "Stopping phone",
        required = check_for_lease,
    )

    prepares = (check_for_lease, off_nodes, stop_phone)

    # 3 methods to get nodes ready
    # (*) load images
    # (*) reset nodes that are known to have the right image
    # (*) do nothing, proceed to experiment
    if do_load:
        load_infra = SshJob(
            node = gwnode,
            commands = [
                [ "rhubarbe", "load", "-i", "u{}-oai-gw".format(ubuntu), hssname, epcname ],
                [ "rhubarbe", "wait", "-t",  120, hssname, epcname ],
            ],
            label = "load and wait HSS and EPC nodes",
            required = prepares,
        )

        load_enb = SshJob(
            node = gwnode,
            commands = [
                [ "rhubarbe", "load", "-i", "u{}-oai-enb".format(ubuntu), enbname, scrname ],
                [ "rhubarbe", "wait", "-t", 120, enbname, scrname ],
            ],
            label = "load and wait ENB and SCR",
            required = prepares,
        )
        
        loads = [load_infra, load_enb]
        
    elif do_reset:
        
        reset_nodes = SshJob(
            node = gwnode,
            commands = [
                [ "rhubarbe", "reset", hss, epc, enb, scr ],
                [ "rhubarbe", "wait", "--timeout", 120, "--verbose", hss, epc, enb, scr ],
            ],
            label = "Reset all nodes",
            required = prepares,
        )

        loads = [reset_nodes]

    else:
        loads = []

# actually run this in the gateway, not on the mac
# the ssh keys are stored in the gateway and I haven't yet figured how to leverage such remote keys
#    macphone = SshNode(gateway = gwnode, hostname = 'macphone', username = 'tester',
#                       formatter = ColonFormatter(verbose=verbose), debug = debug)

    run_hss = SshJobScript(
        node = hssnode,
        command = [ script("oai-hss.sh"), "run-hss", epc ],
        includes = includes,
        label = "run HSS",
        required = (loads, prepares),
    )

    run_epc = SshJobScript(
        node = epcnode,
        command = [ script("oai-epc.sh"), "run-epc", hss ],
        includes = includes,
        label = "run EPC",
        required = (loads, prepares),
    )

    run_enb = SshJobScript(
        node = enbnode,
        # run-enb expects the id of the epc as a parameter
        command = [ script("oai-enb.sh"), "run-enb", epc ],
        includes = includes,
        label = "run softmodem on ENB",
        required = (loads, prepares),
    )

    # schedule the load phases only if required
    e = Engine(run_enb, run_epc, run_hss, verbose=verbose, debug=debug)
    e.update(prepares)
    e.update(loads)
    # remove requirements to the load phase if not added
    e.sanitize(verbose=False)
    
    print(40*"*", "ubuntu = {}, do_load = {}, do_reset = {}".format(ubuntu, do_load, do_reset))
    if verbose:
        e.list()
    if not e.orchestrate():
        print("RUN KO : {}".format(e.why()))
        e.debrief()
        return False
    else:
        print("RUN OK")
        return True

# nothing to collect on the scrambler
def collect(run_name, slice, hss, epc, enb, scr, do_load, do_reset, ubuntu, verbose, debug):
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

    default_slice = "onelab.inria.oai.oai_build@faraday.inria.fr"
    def_hss, def_epc, def_enb, def_scr = 23, 16, 19, 11
    

    from argparse import ArgumentParser
    parser = ArgumentParser()
    # xxx faire une première phase de vérifications diverses (clés, scripts, etc..)
    # xxx ajouter une option -k pour spécifier une clé ssh
    parser.add_argument("-l", "--load", dest='do_load', action='store_true', default=False,
                        help='load images as well')
    parser.add_argument("-r", "--reset", dest='do_reset', action='store_true', default=False,
                        help='reset nodes instead of loading images')
    parser.add_argument("-v", "--verbose", action='store_true', default=False)
    parser.add_argument("-d", "--debug", action='store_true', default=False)
    parser.add_argument("-s", "--slice", default=default_slice,
                        help="defaults to {}".format(default_slice))
    parser.add_argument("-u", "--ubuntu", default="16.47", choices = ("16.48", "16.47", "14.48"),
                        help="specify using images based on ubuntu 14.04 or 16.04")

    parser.add_argument("--hss", default=def_hss, help="defaults to {}".format(def_hss))
    parser.add_argument("--epc", default=def_epc, help="defaults to {}".format(def_epc))
    parser.add_argument("--enb", default=def_enb, help="defaults to {}".format(def_enb))
    parser.add_argument("--scr", default=def_scr, help="defaults to {}".format(def_scr))

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
        collect(run_name, **kwds)
    except KeyboardInterrupt as e:
        print("OK, skipped collection, bye")
    

    
main()
