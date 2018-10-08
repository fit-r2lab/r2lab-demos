#!/usr/bin/env python3

from argparse import ArgumentParser

from asynciojobs import Scheduler, PrintJob

from apssh import SshNode, LocalNode, SshJob
from apssh import Run, RunString, Pull

def fitname(node_id):
    """
    Return a valid hostname from a node number - either str or int
    """
    int_id = int(node_id)
    return "fit{:02d}".format(int_id)

##########
gateway_hostname  = 'faraday.inria.fr'
gateway_username  = 'inria_ns3'
verbose_ssh = False

# Default fit ids for server and client
def_server, def_client = 3, 4
# Default ns-3 duration
def_duration = 25
# Default ns-3 node target in which the tap device is created
def_target = 2

# Images names for server and client
image_server = "ubuntu"
image_client = "ubuntu-ns3-dev"

parser = ArgumentParser()
parser.add_argument("-s", "--slice", default=gateway_username,
                    help="specify an alternate slicename, default={}"
                         .format(gateway_username))
parser.add_argument("-S", "--server", default=def_server,
                    help="id of the node that runs the server, default={}".format(def_server))
parser.add_argument("-C", "--client", default=def_client,
                    help="id of the node that runs the server, default={}".format(def_client))
parser.add_argument("-d", "--duration", default=def_duration,
                    help="duration of the ns-3 simulation, default={}".format(def_duration))
parser.add_argument("-o", "--olsr", default=False, action='store_true',
                    help="run OLSR ns-3 simulation script, default is CSMA ns-3 script")
parser.add_argument("-m", "--multicast", default=False, action='store_true',
                    help="run multicast scenario, default is point-to-point")
parser.add_argument("-V", "--vlc", default=False, action='store_true',
                    help="run scenario with vlc by default, else ping or mc_send will be used")
parser.add_argument("-t", "--target", default=def_target,
                    help="id of the ns-3 node in the which the tap device is created, default={}".format(def_target))
parser.add_argument("-v", "--verbose-ssh", default=False, action='store_true',
                    help="run ssh in verbose mode")
parser.add_argument("-l", "--load-images", default=False, action='store_true',
                    help = "enable to load the default image on nodes before the exp")
args = parser.parse_args()

gateway_username = args.slice
verbose_ssh = args.verbose_ssh
duration = args.duration
multicast_mode = args.multicast
olsr_mode = args.olsr
vlc_mode = args.vlc
target_node = args.target

if olsr_mode and multicast_mode:
    waf_script = """ cd ns-3-dev; ./waf --run "scratch/olsr --remote={} --local={} --dstnNode={} --stopTime={} --multicast=true" """.format(args.server,args.client,target_node,duration)
elif olsr_mode:
    waf_script = """ cd ns-3-dev; ./waf --run "scratch/olsr --remote={} --local={} --dstnNode={} --stopTime={} --multicast=false" """.format(args.server,args.client,target_node,duration)
elif multicast_mode:
    waf_script = """ cd ns-3-dev; ./waf --run "scratch/csma --remote={} --local={} --dstnNode={} --stopTime={} --multicast=true" """.format(args.server,args.client,target_node,duration)
else:
    waf_script = """ cd ns-3-dev; ./waf --run "scratch/csma --remote={} --local={} --dstnNode={} --stopTime={} --multicast=false" """.format(args.server,args.client,target_node,duration)

if vlc_mode:
    if multicast_mode:
#        send_script= "cvlc /root/rassegna2.avi --ttl=16 --sout '#transcode{acodec=none,vcodec=h264}:rtp{dst=225.1.2.4:1234}'"
#        send_script= "cvlc /root/rassegna2.avi --ttl=16 --sout '#transcode{acodec=none,vcodec=h264}:udp{dst=225.1.2.4:1234}'"
        send_script= "cvlc /root/big_buck_bunny.mp4 --ttl=16 --sout '#transcode{acodec=none}:rtp{mux=ts,dst=225.1.2.4,port=1234}'"
    else:
#        send_script= "cvlc /root/rassegna2.avi --sout '#rtp{dst=10.1.1." + str(target_node) + ",port=1234,mux=ts}'"
        send_script= "cvlc /root/big_buck_bunny.mp4 --sout '#transcode{acodec=none}:rtp{dst=10.1.1." + str(target_node) + ",port=1234,mux=ts}'"
    stop_sender_script= "pkill vlc; echo 'pkill vlc'"
else: # not vlc
    if multicast_mode:
        # Hack to avoid usage of Critical=False to fix the issue...
        send_script= "(mcsender -t16 -idata 225.1.2.4:1234 ; ret=$?; if [ $ret -eq '143' ]; then exit 0; fi; exit $ret)"
        #send_script= "mcsender -t16 -idata 225.1.2.4:1234"
        stop_sender_script= "pkill mcsender; echo 'pkill mcsender'"
    else:
        send_script= "(ping 10.1.1.{} ; ret=$?; if [ $ret -eq '143' ]; then exit 0; fi; exit $ret)".format(target_node)
        stop_sender_script= "pkill ping; echo 'pkill ping'"

if vlc_mode:
    stop_client_script="pkill vlc; echo 'pkill vlc'; pkill --signal SIGUSR2 tcpdump; echo 'pkill tcpdump'"
else:
    stop_client_script="pkill --signal SIGUSR2 tcpdump; echo 'pkill tcpdump'"

tcpdump_script= "(tcpdump -i tap0 -w tap0.pcap; ret=$?; if [ $ret -eq '140' ]; then exit 0; fi; exit $ret)"

if vlc_mode:
    if multicast_mode:
        recv_script= "cvlc --miface-addr=10.1.2.1 rtp://@225.1.2.4 --sout file/ps:video.mpg" 
    else:
        recv_script= "cvlc --miface-addr=10.1.2.1 rtp:// --sout file/ps:video.mpg"

server, client = fitname(args.server), fitname(args.client)

# Wait 5s before running vlc sender on the server to avoid congestion on the link before waf starts
if vlc_mode:
    settle_delay = 5
else:
    settle_delay = 0


print("Running scenario with server {} and client {}".format(server,client))
print("with following sender script: {}".format(send_script))
print("and following waf command: {}".format(waf_script))

###
#######
faraday = SshNode(hostname = gateway_hostname, username = gateway_username,
                  verbose = verbose_ssh)

server = SshNode(gateway = faraday, hostname = server, username = "root",
                 verbose = verbose_ssh)
client = SshNode(gateway = faraday, hostname = client, username = "root",
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
            Run("rhubarbe", "load", "-i", image_server, args.server),
            Run("rhubarbe", "load", "-i", image_client, args.client),
            Run("rhubarbe", "wait", "-t",  120, args.server, args.client),
        ]
    )

##########
# setting up the data interface on both server and client
# setting up routing on server only

# NOTE: If for a second experiment, you wish to change the client node while 
# keeping the server node the same; delete the existing route to 10.1.1.0 on 
# the server node and other problematic routes.

server_init_script = """
apt install -y vlc smcroute
sed -i 's/geteuid/getppid/' /usr/bin/vlc
wget http://clips.vorwaerts-gmbh.de/big_buck_bunny.mp4
wget https://cinelerra-cv.org/footage/rassegna2.avi
route add -net 224.0.0.0 netmask 240.0.0.0 dev data
route add -net 10.1.1.0 gw 192.168.2.{} netmask 255.255.255.0 dev data
""".format(args.client)

client_init_script = """
apt install -y vlc uml-utilities
sudo tunctl -t tap0
sudo ifconfig tap0 hw ether 08:00:2e:00:00:01
sudo ifconfig tap0 10.1.2.1 netmask 255.255.255.0 up
sed -i 's/geteuid/getppid/' /usr/bin/vlc
ifconfig data promisc up
"""


# following two inits should be done only when load_images is true
if args.load_images:
    init_server = SshJob(
        node = server,
        scheduler = scheduler,
        required = green_light,
        commands = [
            Run("turn-on-data"),
            RunString(server_init_script, label="init server node"),
        ],
    )

    init_client = SshJob(
        node = client,
        scheduler = scheduler,
        required = green_light,
        commands = [
            Run("turn-on-data"),
            RunString(client_init_script, label="init client node"),
        ],
    )

if args.load_images:
    init_done = (init_server,init_client)
else:
    init_done = green_light

# let the ns-3 network settle before starting vlc server and client
settle_ns3 = PrintJob(
    "Let the ns-3 network settle before starting vlc",
    sleep=settle_delay,
    scheduler=scheduler,
    required=init_done,
    label="settling for {} seconds".format(settle_delay)
)

run_ns3 = SshJob(
    node = client,
    scheduler = scheduler,
    command = RunString(waf_script, label="Run ns-3 script on client"),
    required = init_done,
)



run_tcpdump_job = [
    SshJob(
        #scheduler=scheduler
        node=client,
        forever=True,
        command = RunString(tcpdump_script,label="run tcpdump tap0 on client"),
    )
]
run_tcpdump = Scheduler(*run_tcpdump_job,
                         scheduler=scheduler,
                         required=init_done,
                         label="Run tcpdump on tap0 client")

run_sender_job = [
    SshJob(
        #scheduler=scheduler
        node=server,
        forever=True,
#        critical=False,
        command = RunString(send_script,label=send_script),
    )
]
run_sender = Scheduler(*run_sender_job,
                        scheduler=scheduler,
                        required=settle_ns3,
                        label="Run the sender on server")

if vlc_mode:
    run_vlc_receiver_job = [
        SshJob(
            #scheduler=scheduler
            node=client,
            forever=True,
            command = RunString(recv_script,label=recv_script),
            )
    ]
    run_vlc_receiver = Scheduler(*run_vlc_receiver_job,
                                  scheduler=scheduler,
                                  required=settle_ns3,
                                  label="Run vlc receiver on ns-3 at client")


stop_all_job = [
    SshJob(
        #scheduler=scheduler,
        node = server,
        label = "kill sender on the server",
        command = RunString(stop_sender_script,label=stop_sender_script),
    ),
    SshJob(
        node = client,
        #scheduler=scheduler,
        label = "kill apps on the client",
        command = RunString(stop_client_script,label=stop_client_script),
    ),
]


stop_all = Scheduler(*stop_all_job,
                      scheduler=scheduler,
                      required=run_ns3,
                      label="Stop tcpdump, sender and vlc receiver",)

pull_files = SshJob(
    node = client,
    scheduler = scheduler,
    critical=False,
    commands = [
        Pull (remotepaths="ns-3-dev/packets-{}-0.pcap".format(def_target),localpath="."),
        Pull (remotepaths="tap0.pcap",localpath="."),
        Pull (remotepaths="video.mpg",localpath="."),
    ],
    required = stop_all,
    label="Retrieve the pcap traces and received video",
)

##########
# run the scheduler
ok = scheduler.orchestrate()

# give details if it failed
ok or scheduler.debrief()

success = ok 

# producing a png file for illustration
scheduler.export_as_pngfile("ns3-scenario")

exit(0 if success else 1)

