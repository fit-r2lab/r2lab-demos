#!/usr/bin/env python3

from argparse import ArgumentParser

from asynciojobs import Scheduler

from apssh import SshNode, LocalNode, SshJob
from apssh import Run, RunString, Pull

##########
gateway_hostname  = 'faraday.inria.fr'
gateway_username  = 'inria_ns3'
verbose_ssh = False

parser = ArgumentParser()
parser.add_argument("-s", "--slice", default=gateway_username,
                    help="specify an alternate slicename, default={}"
                         .format(gateway_username))
parser.add_argument("-v", "--verbose-ssh", default=False, action='store_true',
                    help="run ssh in verbose mode")
parser.add_argument("-l", "--load-images", default=False, action='store_true',
                    help = "enable to load the default image on nodes before the exp")
args = parser.parse_args()

gateway_username = args.slice
verbose_ssh = args.verbose_ssh

###
#######
faraday = SshNode(hostname = gateway_hostname, username = gateway_username,
                  verbose = verbose_ssh)

node1 = SshNode(gateway = faraday, hostname = "fit10", username = "root",
                verbose = verbose_ssh)
node2 = SshNode(gateway = faraday, hostname = "fit11", username = "root",
                verbose = verbose_ssh)

##########
# create an orchestration scheduler
scheduler = Scheduler()

##########
check_lease = SshJob(
    # checking the lease is done on the gateway
    node = faraday,
    critical = True,
    command = Run("rhubarbe leases --check"),
    scheduler = scheduler,
)

########## load images on the two nodes if requested

green_light = check_lease

if args.load_images:
    # replace green_light in this case
    green_light = SshJob(
        node = faraday,
        required = check_lease,
        critical = True,
        scheduler = scheduler,
        commands = [
            Run("rhubarbe load -i ns-3-dev 10 11"),
            Run("rhubarbe wait 10-11"),
        ]
    )

##########
# setting up the data interface on both fit01 and fit02  
# setting up routing on fit01

server_init = """
turn-on-data
route add -net 10.1.1.0 gw 192.168.2.11 netmask 255.255.255.0 dev data
sed -i 's/geteuid/getppid/' /usr/bin/vlc
wget https://cinelerra-cv.org/footage/rassegna2.avi
"""

client_init = """
turn-on-data
ifconfig data promisc up
sed -i 's/geteuid/getppid/' /usr/bin/vlc
sudo tunctl -t tap0
sudo ifconfig tap0 hw ether 08:00:2e:00:00:01
sudo ifconfig tap0 10.1.2.1 netmask 255.255.255.0 up
"""

waf_script = """
cd ns-3-dev
./waf --run "scratch/check" 
"""

video_script= """
cvlc /root/rassegna2.avi --sout '#rtp{dst=10.1.1.2,port=1234,mux=ts}'
"""

init_server = SshJob(
    node = node1,
    command = RunString(
        server_init, label="init server node1",
    ),
    required = green_light,
    scheduler = scheduler,
)

init_client = SshJob(
    node = node2,
    command = RunString(
        client_init, label="init client node2",
    ),
    required = green_light,
    scheduler = scheduler,
)

run_tcpdump_job = [
    SshJob(
        #scheduler=scheduler
        node=node2,
        forever=True,
        label="run tcpdump tap0 on node2",
        commands = Run("tcpdump -i tap0 -s 65535 -w tap.txt"),
        )
]
run_tcpdump = Scheduler(*run_tcpdump_job,
                         scheduler=scheduler,
                         required=(init_server,init_client),
                         label="Run tcpdump on node2")

run_vlc_sender_job = [
    SshJob(
        #scheduler=scheduler
        node=node1,
        forever=True,
        command = RunString(video_script,label="vlc --sout '#rtp{dst=10.1.1.2,port=1234,mux=ts}'"),
        )
]
run_vlc_sender = Scheduler(*run_vlc_sender_job,
                            scheduler=scheduler,
                            required=(init_server,init_client),
                            label="Run cvlc sender on node1")


run_vlc_receiver_job = [
    SshJob(
        #scheduler=scheduler
        node=node2,
        forever=True,
        command = Run("cvlc --miface-addr 10.1.2.1 rtp://",
                      label="vlc --miface-addr 10.1.2.1 rtp://"),
        )
]
run_vlc_receiver = Scheduler(*run_vlc_receiver_job,
                              scheduler=scheduler,
                              required=(init_server,init_client),
                              label="Run vlc receiver on ns-3 at node2")

run_ns3 = SshJob(
    scheduler = scheduler,
    node = node2,
    command = RunString(waf_script, label="Run ns-3 script on node2"),
    required = (init_server,init_client),
)

stop_all_job = [
    SshJob(
        #scheduler=scheduler,
        node = node1,
        label = "kill vlc sender at node1",
        command = Run("pkill vlc; echo 'pkill vlc'"),
        ),
    SshJob(
        #scheduler=scheduler,
        node = node2,
        label = "kill vlc receiver and tcpdump at node2",
        commands=[
            Run("pkill vlc; echo 'pkill vlc'"),
            Run("pkill tcpdump; echo 'pkill tcpdump'"),
            ],
        ),
]
stop_all = Scheduler(*stop_all_job,
                      scheduler=scheduler,
                      required=run_ns3,
                      label="Stop tcpdump and vlc sender/receiver",)

##########
# run the scheduler
ok = scheduler.orchestrate()

# give details if it failed
ok or scheduler.debrief()

success = ok 

# producing a dot file for illustration
scheduler.export_as_pngfile("vlc-csma")


exit(0 if success else 1)
