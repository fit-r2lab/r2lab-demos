#!/usr/bin/env python3

"""
This script is a rewrite of an experiment initially based on NEPI
This version relies on a combination of 
* asynciojobs
* and apssh's jobs plugins SshJob*


Purpose is to reproduce the measurement of the angle of arrival
of a wireless flow between
* a sender that uses a single antenna
* a receiver that uses 3 aligned antennas, iso-spaced by 3cm:

     (1) <-- 3cm --> (2) <-- 3cm --> (3)
  
You can see this python script as a description of the dependencies between
* initializations, i.e. setting up wireless drivers, devices,
  antennas and monitoring for data capture
* running (actually sending traffic)
* data retrieval 

The details of each of these steps are written as a single shell
script code (angle-measure.sh) that gives the details of each of these steps 
on a single host (either sender or receiver)

So e.g.
angle-measure.sh run-sender 50000 100 1000
would cause the sender node to send 50000 random packets of 100 bytes every millisecond

"""

########################################
import os, os.path
import time
import logging
from argparse import ArgumentParser

# the Engine object is the core of asynciojobs
from asynciojobs import Engine

# we use only ssh-oriented jobs in this script
from apssh import SshNode, SshJob, SshJobScript, SshJobCollector
from apssh import load_agent_keys

# output formats
from apssh.formatters import TimeColonFormatter, SubdirFormatter

# using external shell script like e.g.:
# angle-measure.sh init-sender channel bandwidth

#################### a R2lab specific helper
# so that one can say stuff like --receiver "8 9" --sender 10 --sender fit12
# which means we want to use receivers fit09 and fit 09 and senders fit10 and fit12

def r2lab_nodes(parser_args):
    """
    normalize a list of nodenames as provided on the command line
    with e.g. 
    parser.add_argument("-r", "--receivers", action='append', default=[])
    """

    # compute receivers and senders
    def flatten(grandpa):
        return [x for father in grandpa for x in father if x]
    nodenames = []
    for arg in parser_args:
        args = [ arg ]
        args = flatten([ arg.split(' ') for arg in args])
        args = flatten([ arg.split(',') for arg in args])
        args = [ arg.replace('fit', '') for arg in args]
        args = [ int(arg) for arg in args ]
        args = [ "fit{:02d}".format(arg) for arg in args]
        nodenames += args
    return nodenames

#################### one experiment
def one_run(gwhost, gwuser, keys,
            sendername, receivername, packets, size, period,
            formatter, verbose=False, debug=False):
    """
    gwhost, gwuser, keys: where to reach the testbed gateway
    sendername, receivername : hostnames for the test nodes
    packets, size, period : details of the traffic to send
    formatter: how to report results
    """

    # we keep all 'environment' data for one run in a dedicated subdir
    # using this name scheme to store results locally
    # xxx inherited from the NEPI version - unused for now
    dataname = os.path.join("csi-{}-{}-{}-{}-{}"
                            .format(receivername, sendername, packets, size, period))

    # we have reused the shell script from the NEPI version as-is
    auxiliary_script = "./angle-measure.sh"

    # the proxy to enter faraday
    r2lab_gateway = SshNode(
        hostname = gwhost,
        username = gwuser,
        keys = keys,
        formatter = formatter,
        debug = debug,
    )

    # the sender node
    sender = SshNode(
        # specifying the gateway attribute means this node will be reached
        # through the ssh connection to the gateway
        gateway = r2lab_gateway,
        # hostname needs to make sense in the context of the gateway; so e.g. 'fit01' is fine
        hostname = sendername,
        # from the gateway we enter the R2lab nodes as root
        username = 'root',
        formatter = formatter,
        debug = debug,
    )

    # the receiver node - ditto
    receiver = SshNode(
        hostname = receivername,
        username = 'root',
        gateway = r2lab_gateway,
        formatter = formatter,
    )

    # one initialization job per node
    init_sender = SshJobScript(
        # on what node to run the command
        node = sender,
        # the command to run; being a JobSshScript, the first item in this
        # list is expected to be a **LOCAL** script that gets puhed remotely
        # before being run
        # a simple JobSsh is more suitable to issue standard Unix commands for instance
        command = [ auxiliary_script, "init-sender", 64, "HT20" ],
        # for convenience purposes
        label = "init-sender")

    init_receiver = SshJobScript(
        node = receiver,
        command = [ auxiliary_script, "init-receiver", 64, "HT20" ],
        label = "init-receiver")

    # ditto for actually running the experiment
    run_sender = SshJobScript(
        node = sender,
        command = [ auxiliary_script, "run-sender", packets, size, period ],
        label = "run-sender")

    # run the sender only once both nodes are ready
    run_sender.requires(init_sender, init_receiver)

    run_receiver = SshJobScript(
        node = receiver,
        command = [ auxiliary_script, "run-receiver", packets, size, period ],
        label = "run-receiver")
    # ditto
    run_receiver.requires(init_sender, init_receiver)

    collector = SshJobCollector(
        node = receiver,
        remotepaths = 'rawdata',
        localpath = dataname,
        label = "collector")
    collector.requires(run_receiver)

    # print a one-liner for that receiver, sender couple
    summary = "{} ==> {} - {} packets of {} bytes, each {}us"\
        .format(sendername, receivername, packets, size, period)
    print(10*'-', summary)

    # create an Engine object that will orchestrate this scenario
    e = Engine(init_sender, init_receiver,
               run_sender, run_receiver,
               collector,
               verbose = verbose,
               debug = debug)

    if  e.orchestrate(timeout = 3*60):
        print("========== experiment OK")
    else:
        print("!!!!!!!!!! orchestration KO")
        e.debrief()

        # still missing as compared to the NEPI equivalent
###     # collect data
###     print(10*'-', summary, 'Collecting data in {}'.format(dataname))
###     get_app_stdout(ec, init_sender, "sender-init", dataname)
###     get_app_stdout(ec, init_receiver, "receiver-init", dataname)
###     get_app_stdout(ec, run_sender, "sender-run", dataname)
###     get_app_stdout(ec, run_receiver, "receiver-run", dataname)
###     # raw data gets to go in the current directory as it's more convenient to manage
###     # also it's safe to wait for a little while
###     time.sleep(5)
###     get_app_trace(ec, run_receiver, "receiver-run", ".", "rawdata", dataname+".raw")


####################
# globals for now - could be add_argument'ed of course
default_gateway = "onelab.inria.oai.oai_build@faraday.inria.fr"

def main():

    parser = ArgumentParser()

    parser.add_argument("-r", "--receivers", action='append', default=[],
                        help="hostnames for the receiver nodes, additive")
    parser.add_argument("-s", "--senders", action='append', default=[],
                        help="hostnames for the sender node, additive")
    
    parser.add_argument("-d", "--storage-dir", default=None,
                        help="specify a directory for storing all results")
    # select how many packets, and how often they are sent
    parser.add_argument("-p", "--packets", type=int, default=10000,
                        help="nb of packets to send")
    parser.add_argument("-i", "--size", type=int, default=100,
                        help="packet size in bytes")
    parser.add_argument("-e", "--period", type=int, default=1000,
                        help="time between packets in micro-seconds")
    parser.add_argument("-g", "--gateway", default=default_gateway,
                        help="R2lab slicename and gateway - default={}".format(default_gateway))
    # partial runs, dry runs
    parser.add_argument("-n", "--dry-run", action='store_true',
                        default=False, help="Show experiment context and exit - do nothing")
    parser.add_argument("-v", "--verbose", action='store_true',
                        default=False, help="Make it verbose")
    parser.add_argument("-D", "--debug", action='store_true',
                        default=False, help="Turn on debugging")
    args = parser.parse_args()

    packets = args.packets
    size = args.size
    period = args.period
    verbose = args.verbose
    debug = args.debug
    
    # nodes to use
    if not args.receivers or not args.senders:
        parser.print_help()
        exit(1)

    # parse gateway argument expected to be user@hostname
    gwslice, gwhost = args.gateway.split('@')

    # locate nodes - normalizing 
    receivernames, sendernames = r2lab_nodes(args.receivers), r2lab_nodes(args.senders)

    # initialize formatter
    # TimeColonFormatter shows stuff on stdout, with a format like
    # 17-14-24:fit31:actual output from the remote command
    formatter = TimeColonFormatter(verbose = verbose) if args.storage_dir is None \
                else SubdirFormatter(args.storage_dir, verbose = verbose)

###     if args.dry_run:
###         print(10*'-', "Using gateway {gwhost} with account {gwuser} and key {key}"
###               .format(**locals()))

    for sendername in sendernames:
        for receivername in receivernames:
            ########## dry run : just display context
            if args.dry_run:
                print(4*'-', "{sendername} => {receivername}, "
                      "Sending {packets} packets, {size} bytes long,"
                      " every {period} micro-seconds"
                      .format(**locals()))
            else:
                # simplest keys policy : use ssh-agent only for now
                keys = load_agent_keys()
                #for key in keys:
                #    print("loading from agent: {}".format(key))
                one_run(gwhost, gwslice, keys,
                        sendername, receivername, packets, size, period,
                        formatter, verbose, debug)

if __name__ == '__main__':
    main()
