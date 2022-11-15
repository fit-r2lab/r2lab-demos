#!/usr/bin/env python3

"""
first version that builds all objects from pure Python code
"""

from asynciojobs import Scheduler
from apssh import SshNode, LocalNode, ColonFormatter
from apssh import SshJob, Run, RunScript, Pull

# for the epilogue that runs a command locally
import asyncio
from asynciojobs import Job

gwname = "faraday.inria.fr"
slice = "inria_admin"

def main(nodename1, nodename2, *, verbose=True):

    # show ssh outputs on stdout as they appear
    # together with corresponding hostname
    formatter = ColonFormatter(verbose=verbose)

    ########## declare the needed ssh connections
    # our main ssh connection
    gateway = SshNode(hostname = gwname, username = slice,
                      formatter = formatter)
    # the ssh connections to each of the 2 nodes
    node1, node2 = [
        SshNode(hostname = nodename, username="root",
                # this is how we create a 2-hop
                # ssh connection behind a gateway
                gateway = gateway,
                formatter = formatter, debug=verbose)
        for nodename in (nodename1, nodename2)]

    ##########
    job_warmup = SshJob(
        node = gateway,
        # with just Run()
        # you can run a command already available on the remote
        command = [
            Run("rhubarbe leases --check"),
            Run("rhubarbe on", nodename1, nodename2),
            Run("rhubarbe wait", nodename1, nodename2),
        ]
    )

    job_prep_send = SshJob(
        node = node1,
        command = [
            # an example of a compound job
            # with RunScript, we run a command whose source is local here
            RunScript("demo.sh", "prepare-sender"),
            Run("ip address show control"),
        ],
        # run this only once this job is done
        required = job_warmup,
    )
    job_prep_recv = SshJob(
        node = node2,
        command = RunScript("demo.sh", "prepare-receiver"),
        required = job_warmup,
    )

    job_run_send = SshJob(
        node = node1,
        command = [
            RunScript("demo.sh", "run-sender"),
            Pull("PREP", "PREP-SEND"),
            Pull("RUN", "RUN-SEND"),
        ],
        # start when both nodes are ready
        required = ( job_prep_send, job_prep_recv),
    )
    job_run_recv = SshJob(
        node = node2,
        command = [
            RunScript("demo.sh", "run-receiver"),
            Pull("PREP", "PREP-RECV"),
            Pull("RUN", "RUN-RECV"),
        ],
        required = ( job_prep_send, job_prep_recv),
    )

    # one could also use a raw `Job` instead, but
    # it's more elegant this way, as all the steps
    # in the demo are handled in a uniform way in the .sh
    job_epilogue = SshJob(
       node=LocalNode(),
       command=[
           RunScript("demo.sh", "epilogue"),
       ],
       required=(job_run_send, job_run_recv),
   )

    scheduler = Scheduler(
        job_warmup,
        job_prep_send, job_prep_recv,
        job_run_send, job_run_recv,
        job_epilogue,
        verbose=verbose
    )

    # this will work whether you have graphviz installed or not
    scheduler.export_as_dotfile('demo-v1.dot')
    print("# you can produce a .png file with the following command")
    print("# install dot with e.g. brew install graphviz on macos")
    print("dot -Tpng demo-v1.dot -o demo-v1.png")
    # note that if you do have graphviz installed you can
    # have the graphic-production phase made by your script itself
    # by calling this (could be png, or use export_as_graphic for other formats)
    print("writing graphic scenario in demo-v1.svg")
    scheduler.export_as_svgfile("demo-v1")
    print(20 * '=')

    ok = scheduler.orchestrate()
    if not ok:
        scheduler.debrief()

if __name__ == '__main__':
    main('fit01', 'fit02', verbose=False)
