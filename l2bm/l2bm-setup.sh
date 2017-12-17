#!/bin/bash

####################
# This is our own brewed script for setting up a wifi network
# it run on the remote machine - either sender or receiver
# and is in charge of initializing a small ad-hoc network
#
#


# init-ad-hoc-network expects the following arguments
# * wireless driver name, here for atheros: ath9k
# * the wifi network name to join
# * the wifi frequency to use

function init-ad-hoc-network (){
    driver=$1; shift
    netname=$1; shift
    freq=$1;   shift

    # load the r2lab utilities - code can be found here:
    # https://github.com/parmentelat/r2lab/blob/master/infra/user-env/nodes.sh
    source /root/r2lab/infra/user-env/nodes.sh

    # make sure to use the latest code on the node
    git-pull-r2lab

    turn-off-wireless
    
    ipaddr_mask=10.0.0.$(r2lab-ip)/24

    echo loading module $driver
    modprobe $driver
    
    # some time for udev to trigger its rules
    sleep 1
    
    ifname=$(wait-for-interface-on-driver $driver)
    phyname=`iw $ifname info|grep wiphy |awk '{print "phy"$2}'`
    moniname="moni-$driver"

    echo configuring interface $ifname
    # make sure to wipe down everything first so we can run again and again
    ip address flush dev $ifname
    ip link set $ifname down
    # configure wireless
    iw dev $ifname set type ibss
    ip link set $ifname up
    # set to ad-hoc mode
    iw dev $ifname ibss join $netname $freq
    ip address add $ipaddr_mask dev $ifname

    # set the wireless interface in monitor mode
    echo "Creating monitor interface $moniname at $phyname"
    iw phy $phyname interface add $moniname type monitor 2>/dev/null
    ip link set $moniname up

    # install iperf and tcpdump
    apt-get install -y iperf tcpdump

}

function ovs-setup(){

    # Install missing packages useful for ovs and libfluid
    apt-get install -y autoconf libtool build-essential pkg-config libevent-dev libssl-dev

    # Manage the atheros wireless interface through ovs
    echo "Configure ovs and interface it with atheros Wi-Fi interface"
    ip addr del 10.0.0.2/24  dev atheros

    ovs-vsctl add-br br0
    ovs-vsctl add-port br0 atheros

    ip addr add 10.0.0.2/24 broadcast 10.0.0.255 dev br0
    ip link set br0 up

    ovs-vsctl set bridge br0 protocols=OpenFlow13
    ovs-vsctl set bridge br0 other_config:disable-in-band=true
    ovs-vsctl set-manager ptcp:6640
    ovs-vsctl set-controller br0 tcp:0.0.0.0:7777

    # Install libfluid and the L2BM controller
    echo "Install Libfluid controller and L2BM multicast function"
    git clone https://github.com/hksoni/libfluid.git
    cd libfluid/
    ./bootstrap.sh
    cd libfluid_base/
    ./configure
    make
    make install

    cd ../libfluid_msg
    ./configure
    make
    make install

    cd ../examples/controller/
    make

    # Run the mc_controller
    echo "Run the mc_controller: mc_controller mc-app 10.0.0.6 8888 7777"
    LD_LIBRARY_PATH=/usr/local/lib ./mc_controller mc-app 10.0.0.6 8888 7777

}


function iperf_sender () {
    echo "run iperf sender: iperf -l 1400  -c 239.0.0.1 -u -b 100k -f m -i 3 -t 1200"
    route add -host 239.0.0.1 br0
    iperf -l 1400 -c 239.0.0.1 -u -b 100k -f m -i 3 -t 1200
}


function iperf_receiver () {
    echo "run iperf receiver: iperf -l 1400  -c 239.0.0.1 -u -b 100k -f m -i 3 -t 1200"
    route add -host 239.0.0.1 br0
    iperf -s -B 239.0.0.1 -u -f m -i 3
}

function my-ping (){
    dest=$1; shift
    maxwait=$1; shift
    
    start=$(date +%s)

    while true; do
	# allow for one second timeout only; try one packet
	if ping -w 1 -c 1 $dest >& /dev/null; then
	    end=$(date +%s)
	    duration=$(($end - $start))
	    echo "$(hostname) -> $dest: SUCCESS after ${duration}s"
	    return 0
	else
	    echo "$dest not reachable"
	    end=$(date +%s)
	    duration=$(($end - $start))
	    if [ "$duration" -ge "$maxwait" ]; then
		echo "$(hostname) -> $dest: FAILURE after ${duration}s"
		return 1
	    fi
	fi
    done
}

########################################
# just a wrapper so we can call the individual functions. so e.g.
# B3-wireless.sh tracable-ping 10.0.0.2 20
# results in calling tracable-ping 10.0.0.2 20

"$@"
