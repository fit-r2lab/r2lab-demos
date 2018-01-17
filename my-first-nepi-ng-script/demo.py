#!/usr/bin/env python3

from asynciojobs import Scheduler
from apssh import SshNode, ColonFormatter
from apssh import SshJob, Run, RunScript, Pull

gwname = "faraday.inria.fr"
slice = "inria_r2lab.tutorial"

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
        
    scheduler = Scheduler(
        job_warmup,
        job_prep_send, job_prep_recv,
        job_run_send, job_run_recv,
        verbose=verbose
    )

    scheduler.export_as_dotfile('demo.dot')
    print("# produce .png file with the following command")
    print("# install dot with e.g. brew install graphviz on macos")
    print("dot -Tpng demo.dot -o demo.png")
    print(20 * '=')

    ok = scheduler.orchestrate()
    if not ok:
        scheduler.debrief()

if __name__ == '__main__':
    main('fit01', 'fit31', verbose=False)
