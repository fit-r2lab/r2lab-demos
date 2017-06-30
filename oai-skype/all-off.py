#!/usr/bin/env python3

import os.path
import asyncio

from asynciojobs import Scheduler, Job, Sequence

from apssh import SshNode, SshJob, Run, RunScript
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
    try:
        gwuser, gwhost = slice.split('@')
    except:
        gwuser, gwhost = slice, "faraday.inria.fr"
        
    gwnode = SshNode(hostname = gwhost, username = gwuser,
                         formatter = ColonFormatter(verbose=verbose), debug=debug)

    sched = Scheduler(verbose=verbose)
    
    check_for_lease = SshJob(
        node = gwnode,
        command = Run("rhubarbe", "leases", "--check"),
        label = "check we have a current lease",
    )
    sched.add(check_for_lease)
    
    for command in (Run("rhubarbe", "off", "-a"),
                    Run("rhubarbe", "usrpoff", "-a"),
                    RunScript(script("faraday.sh"), "macphone", "r2lab/infra/user-env/macphone.sh", "phone-off",
                              includes = includes)):
        sched.add(
            SshJob(
                node = gwnode,
                command = command,
                required = check_for_lease,
                critical = False,
            ))

    result = sched.orchestrate()
    if not result:
        if check_for_lease.raised_exception():
            print("slice {} does not appear to hold a valid lease".format(slice))
        else:
            print("RUN KO : {}".format(sched.why()))
            sched.debrief()
    else:
        print("RUN OK")

    return 0 if result else 1
        

def main():

    def_slice = "inria_oai@faraday.inria.fr"

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
    
exit(main())
