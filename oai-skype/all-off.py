#!/usr/bin/env python3

import os.path
import asyncio

from asynciojobs import Engine, Job, Sequence

from apssh import SshNode, SshJob, SshJobScript, SshJobCollector
from apssh.formatters import ColonFormatter

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

def all_off(slice, verbose, debug):
    """
    expects a slice name, and turns off faraday completely
    """

    # what argparse knows as a slice actually is a gateway (user + host)
    gwuser, gwhost = slice.split('@')
    gwnode = SshNode(hostname = gwhost, username = gwuser,
                     formatter = ColonFormatter(verbose=verbose), debug=debug)

    ########## preparation
    check_for_lease = SshJob(
        node = gwnode,
        command = [ "rhubarbe", "leases", "--check" ],
        label = "check we have a current lease",
    )

    off_nodes = SshJob(
        node = gwnode,
        # switch off all nodes but the ones we use
        command = [ "rhubarbe", "off", "-a"],
        label = "turn off unused nodes",
        critical = False,
        required = check_for_lease,
    )

    uoff_nodes = SshJob(
        node = gwnode,
        # switch off all nodes but the ones we use
        command = [ "rhubarbe", "usrpoff", "-a"],
        label = "turn off unused nodes",
        critical = False,
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
        critical = False,
        required = check_for_lease,
    )

    prepares = (check_for_lease, off_nodes, uoff_nodes, stop_phone)
    
    # schedule the load phases only if required
    e = Engine(verbose=verbose, debug=debug)
    # this is just a way to add a collection of jobs to the engine
    e.update(prepares)
    if not e.orchestrate():
        print("RUN KO : {}".format(e.why()))
        e.debrief()
        return False
    else:
        print("RUN OK")
        return True

def main():

    def_slice = "onelab.inria.oai.oai_build@faraday.inria.fr"

    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("-s", "--slice", default=def_slice,
                        help="defaults to {}".format(def_slice))

    parser.add_argument("-v", "--verbose", action='store_true', default=False)
    parser.add_argument("-d", "--debug", action='store_true', default=False)

    args = parser.parse_args()

    # we pass to run and collect exactly the set of arguments known to parser
    # build a dictionary with all the values in the args
    kwds = args.__dict__.copy()

    # actually run it
    all_off(**kwds)
    
main()
