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
            Run("rhubarbe load -i ns-3 10"),
            Run("rhubarbe load -i ns-3 11"),
            Run("rhubarbe wait 10-11"),
        ]
    )

##########
# setting up the data interface on both fit01 and fit02  
# setting up routing on fit01

server_script = """
route add -net 10.1.1.0 gw 192.168.2.11 netmask 255.255.255.0 dev data
sed -i 's/geteuid/getppid/' /usr/bin/vlc
wget https://cinelerra-cv.org/footage/rassegna2.avi
"""

client_script = """
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

init_node_01 = SshJob(
    node = node1,
    command = Run("turn-on-data"),
    required = green_light,
    scheduler = scheduler,
)
init_node_02 = SshJob(
    node = node2,
    command = Run("turn-on-data"),
    required = green_light,
    scheduler = scheduler,
)
final_node_01 = SshJob(
    node = node1,
    command = RunString(
        server_script,
    ),
    required = (init_node_01, init_node_02),
    scheduler = scheduler,
)

final_node_02 = SshJob(
    node = node2,
    command = RunString(
        client_script,
    ),
    required = final_node_01,
    scheduler = scheduler,
)

waf_action = SshJob(
   node = node2,
    commands = [
    Run("tcpdump -i tap0 -s 65535 -w tap.txt"),
    Run("cvlc --miface-addr 10.1.2.1 rtp://"),
    RunString(waf_script,),
    ],
    required = final_node_02,
    scheduler = scheduler,
)

video_action = SshJob(
   node = node1,
    command = RunString(
    video_script,
    ),
    required = waf_action,
    scheduler = scheduler,
)

##########
# run the scheduler
ok = scheduler.orchestrate()

# give details if it failed
ok or scheduler.debrief()

success = ok 

# producing a dot file for illustration
scheduler.export_as_dotfile("vlc.dot")

exit(0 if success else 1)
