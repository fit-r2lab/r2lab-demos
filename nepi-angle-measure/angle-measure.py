#!/usr/bin/env python2

"""
This NEPI script is for orchestrating an experiment on R2lab

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
# for using print() in python3-style even in python2
from __future__ import print_function

import os, os.path
import time
import logging
from argparse import ArgumentParser

# import nepi library and other required packages
from nepi.execution.ec import ExperimentController
from nepi.execution.resource import ResourceAction, ResourceState

# using external shell script like e.g.:
# angle-measure.sh init-sender channel bandwidth

########## helpers
# this can run on the prep-lab for dry runs
def credentials():
    "returns a triple (hostname, username, key)"
    return 'faraday.inria.fr', 'onelab.inria.mario.tutorial', '~/.ssh/onelab.private'
    
########## how and where to store results
def get_app_trace(ec, app, appname, rundir, tracename, outfile):
    if not os.path.isdir(rundir):
        os.makedirs(rundir)
    outpath = os.path.join(rundir, outfile)
    with open(outpath, 'w') as f:
        f.write(ec.trace(app, tracename))
    print(4*'=', "Stored trace {} for app {} in {}"
          .format(tracename, appname, outpath))

def get_app_stdout(ec, app, appname, rundir):
    get_app_trace(ec, app, appname, rundir, "stdout", "{}.out".format(appname))

########## one experiment
def one_run(gwhost, gwuser, key, sendername, receivername, packets, size, period, storage):
    # we keep all 'environment' data for one run in a dedicated subdir
    # using this name scheme to store results locally
    dataname = os.path.join(storage, "csi-{}-{}-{}-{}-{}"
                            .format(receivername, sendername, packets, size, period))

    summary = "{} ==> {} {}x{} each {}us"\
        .format(sendername, receivername, packets, size, period)

    ec = ExperimentController(exp_id="angle-measure")

    # the sender node
    sender = ec.register_resource(
        "linux::Node",
        username = 'root',
        hostname = sendername,
        gateway = gwhost,
        gatewayUser = gwuser,
        identity = key,
        cleanExperiment = True,
        cleanProcesses = True,
        autoDeploy = True)

    # the receiver node
    receiver = ec.register_resource(
        "linux::Node",
        username = 'root',
        hostname = receivername,
        gateway = gwhost,
        gatewayUser = gwuser,
        identity = key,
        cleanExperiment = True,
        cleanProcesses = True,
        autoDeploy = True)

    # an app to init the sender
    init_sender = ec.register_resource(
        "linux::Application",
        code = "angle-measure.sh",
        command = "${CODE} init-sender 64 HT20",
        autoDeploy = True,
        connectedTo = sender)

    # an app to init the receiver
    init_receiver = ec.register_resource(
        "linux::Application",
        code = "angle-measure.sh",
        command = "${CODE} init-receiver 64 HT20",
        autoDeploy = True,
        connectedTo = receiver)

    # init phase
    print(10*'-', summary, 'Drivers Initialization')
    ec.wait_finished( [init_sender, init_receiver] )
        
    # an app to run the sender
    run_sender = ec.register_resource(
        "linux::Application",
        code = "angle-measure.sh",
        # beware of curly brackets with format
        command = "${{CODE}} run-sender {} {} {}".format(packets, size, period),
        autoDeploy = True,
        connectedTo = sender)

    # an app to run the receiver
    run_receiver = ec.register_resource(
        "linux::Application",
        code = "angle-measure.sh",
        # beware of curly brackets with format
        command = "${{CODE}} run-receiver {} {} {}".format(packets, size, period),
        autoDeploy = True,
        connectedTo = receiver)

    # run
    print(10*'-', summary, 'Managing radio traffic')
    ec.wait_finished( [run_sender, run_receiver] )

    # collect data
    print(10*'-', summary, 'Collecting data in {}'.format(dataname))
    get_app_stdout(ec, init_sender, "sender-init", dataname)
    get_app_stdout(ec, init_receiver, "receiver-init", dataname)
    get_app_stdout(ec, run_sender, "sender-run", dataname)
    get_app_stdout(ec, run_receiver, "receiver-run", dataname)
    # raw data gets to go in the current directory as it's more convenient to manage
    # also it's safe to wait for a little while
    time.sleep(5)
    get_app_trace(ec, run_receiver, "receiver-run", ".", "rawdata", dataname+".raw")
    
    # we're done
    print(10*'-', summary, 'Shutting down')
    ec.shutdown()

def main():

#    logging.getLogger('sshfuncs').setLevel(logging.DEBUG)
#    logging.getLogger('application').setLevel(logging.DEBUG)

    parser = ArgumentParser()

    # select sender and receiver nodes
    parser.add_argument("-r", "--receivers", action='append', default=[],
                        help="hostnames for the receiver nodes, additive")
    parser.add_argument("-s", "--senders", action='append', default=[],
                        help="hostnames for the sender node, additive")
    
    parser.add_argument("-d", "--storage-dir", default=".",
                        help="specify a directory for storing all results")
    # select how many packets, and how often they are sent
    parser.add_argument("-a", "--packets", type=int, default=10000,
                        help="nb of packets to send")
    parser.add_argument("-i", "--size", type=int, default=100,
                        help="packet size in bytes")
    parser.add_argument("-e", "--period", type=int, default=1000,
                        help="time between packets in micro-seconds")

    # partial runs, dry runs
    parser.add_argument("-n", "--dry-run", action='store_true',
                        default=False, help="Show experiment context and exit - do nothing")
    args = parser.parse_args()

    # get credentials
    gwhost, gwuser, key = credentials()

    packets = args.packets
    size = args.size
    period = args.period

    # nodes to use
    if not args.receivers or not args.senders:
        parser.print_help()
        exit(1)

    def flatten(grandpa):
        return [x for father in grandpa for x in father if x]
    def select_nodes(parser_args):
        """
        normalize a list of incoming nodenames
        """
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

    receivernames = select_nodes(args.receivers)
    sendernames = select_nodes(args.senders)

    if args.dry_run:
        print(10*'-', "Using gateway {gwhost} with account {gwuser} and key {key}"
              .format(**locals()))
    for sendername in sendernames:
        for receivername in receivernames:
            ########## dry run : just display context
            if args.dry_run:
                print(4*'-', "{sendername} => {receivername}, "
                      "Sending {packets} packets, {size} bytes long,"
                      " every {period} micro-seconds"
                      .format(**locals()))
            else:
                one_run(gwhost, gwuser, key, sendername, receivername,
                        packets, size, period, args.storage_dir)

if __name__ == '__main__':
    main()
