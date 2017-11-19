#!/usr/bin/env python3

import asyncio


from asynciojobs import Scheduler, Job, Sequence

from apssh import SshNode, SshJob, Run, RunScript
from apssh.formatters import ColonFormatter

default_slice = "inria_oai@faraday.inria.fr"

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

    scheduler = Scheduler( Sequence(
        SshJob(
            node = gwnode,
            command = Run("rhubarbe", "leases", "--check"),
            label = "check we have a current lease",
        ),
        SshJob(
            node = gwnode,
            command = Run("rhubarbe", "bye"),
            label = "turn off",
        )
    ))
        
    result = scheduler.orchestrate()
    if not result:
        if check_for_lease.raised_exception():
            print("slice {} does not appear to hold a valid lease".format(slice))
        else:
            print("RUN KO : {}".format(scheduler.why()))
            sched.debrief()
    else:
        print("faraday turned off OK")

    return 0 if result else 1
        

def main():


    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument("-v", "--verbose", action='store_true', default=False)
    parser.add_argument("-d", "--debug", action='store_true', default=False)
    parser.add_argument("-s", "--slice", default=default_slice)

    args = parser.parse_args()
    all_off(args.slice, args.verbose, args.debug)
    
exit(main())
