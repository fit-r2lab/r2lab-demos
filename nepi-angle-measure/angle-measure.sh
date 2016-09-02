#!/bin/bash
#
### angle-measure.sh
#
# Usage:
#
# angle-measure.sh init-sender channel bandwidth
# e.g. channel=64
# e.g. bandwidth=HT20 (for 20MHz)
#
# angle-measure.sh init-receiver channel bandwidth
# ditto
#
# angle-measure.sh run-sender packets size period
#
# angle-measure.sh run-receiver packets size period

set -x


############################## UTILITIES for managing drivers and interfaces
# helper functions
# mostly so that
# (*) we figure the name of the intel wireless interfaces wlan<n>
# (*) we can wait for that device to be up
# (*) we can gather a complete status of the setup for the record

# http://unix.stackexchange.com/questions/41817/linux-how-to-find-the-device-driver-used-for-a-device/225496#225496?newreg=c865c93607124e70b9f530f2733aba05
function list-interfaces () {
    set +x
    for f in /sys/class/net/*; do
	dev=$(basename $f)
	driver=$(readlink $f/device/driver/module)
	[ -n "$driver" ] && driver=$(basename $driver)
	addr=$(cat $f/address)
	operstate=$(cat $f/operstate)
	flags=$(cat $f/flags)
	printf "%10s [%s]: %10s flags=%6s (%s)\n" "$dev" "$addr" "$driver" "$flags" "$operstate"
    done
}

function details-on-interface () {
    dev=$1; shift
    echo ==================== ip addr sh $dev
    ip addr sh $dev
    echo ==================== ip link sh $dev
    ip link sh $dev
    echo ==================== iwconfig $dev
    iwconfig $dev
    echo ==================== iw dev $dev info
    iw dev $dev info
}    

# actually returns first interface using a given driver
# prints interface name on stdout
function find-interface-by-driver () {
    set +x
    search_driver=$1; shift
    for f in /sys/class/net/*; do
	_if=$(basename $f)
	driver=$(readlink $f/device/driver/module)
	[ -n "$driver" ] && driver=$(basename $driver)
	if [ "$driver" == "$search_driver" ]; then
	    echo $_if
	    return
	fi
    done
}

# wait for one interface to show up using this driver
# prints interface name on stdout
function wait-for-interface-on-driver() {
    driver=$1; shift
    while true; do
	# use the first device that runs on iwlwifi
	_found=$(find-interface-by-driver $driver)
	if [ -n "$_found" ]; then
	    >&2 echo Using wlan device $_found
	    echo $_found
	    return
	else
	    >&2 echo "Waiting for some interface to run on driver $driver"; sleep 1
	fi
    done
}

# wait for device dev to be in state wait_state
function wait-for-device () {
    set +x
    dev=$1; shift
    wait_state="$1"; shift
    
    while true; do
	f=/sys/class/net/$dev
	operstate=$(cat $f/operstate 2> /dev/null)
	if [ "$operstate" == "$wait_state" ]; then
	    2>& echo Device $dev is $wait_state
	    break
	else
	    >&2 echo "Device $dev is $operstate - waiting 1s"; sleep 1
	fi
    done
}

############################## successive steps of the experiment
function init-sender() {
    ### 2 arguments are required
    channel=$1; shift       # e.g. 64
    bandwidth=$1; shift     # e.g. HT20 

    # unload any wireless driver 
    # useful when the experiment is restarted
    modprobe -r iwlwifi mac80211 cfg80211
    # load our driver
    modprobe iwlwifi debug=0x40000

#    list-interfaces
    
    wlan=$(wait-for-interface-on-driver iwlwifi)

    # create the monitor interface
    iw dev $wlan interface add mon0 type monitor
    # bring it up
    ip link set dev mon0 up
    # init monitor interface
    iw mon0 set channel $channel $bandwidth

    ### define the number of Space time streams
    # and the number of Antenna for transmission
    txs=$(find /sys -name monitor_tx_rate)
    for tx in $txs; do
	echo tweaking $tx
	echo 0x4101 > $tx
    done

    details-on-interface $wlan
    details-on-interface mon0
}



function init-receiver() {
    ### 2 arguments are required
    channel=$1; shift       # e.g. 64
    bandwidth=$1; shift     # e.g. HT20 

    modprobe -r iwlwifi mac80211 cfg80211
    modprobe iwlwifi connector_log=0x1

    wlan=$(wait-for-interface-on-driver iwlwifi)

    while true; do
	iwconfig $wlan mode monitor && break # >&/dev/null
	sleep 1
    done

    # turn on 
    ip link set $wlan up
    # set on same channel
    iw $wlan set channel $channel $bandwidth

    details-on-interface $wlan
    
}



# the image that we use contains the csitool packages installed here
# root@fit04:~# ls -l /root
# total 8
# drwxr-xr-x 24 root root 4096 Jan  8 11:55 linux-80211n-csitool
# drwxr-xr-x  9 root root 4096 Jan 25 21:29 linux-80211n-csitool-supplementary

function run-sender () {
    # 2 arguments are required
    packets=$1; shift
    size=$1; shift
    period=$1; shift

    echo "Sending $packets packets $size-long with period $period us"

    echo $(date) - begin traffic
    set -x
    # random_packets uses the mon0 interface which is hard-wired in the binary
    /root/linux-80211n-csitool-supplementary/injection/random_packets $packets $size 1 $period
    # which means:
    # * send $packets packets
    # * of $size bytes each
    # * 1: on the injection MAC
    # * each $period microseconds 
    set +x
    
    echo $(date) - end traffic

    # unload driver to be 100% sure we will be silent
    echo unloading intel drivers
    modprobe -r iwlwifi mac80211 cfg80211

    # for extra safety
    sleep 60

}



# echo everything on stderr so we can just redirect stdout
# so stdout receives the output of log_to_file
function run-receiver () {
    # 2 arguments are required
    packets=$1; shift
    size=$1; shift
    period=$1; shift

    ### estimate experiment duration
    # in theory overall duration is $packets * $period
    # but in fact the time  for sending a packet must be included as well
    # and with small periods this is substantially different
    # we work around this problem by using a minimal period of 1ms per packet
    minimum=1000
    # compute min of period and minimum
    actual_period=$(( $period <= $minimum ? $minimum : $period))
    duration=$(( $packets * $actual_period / 1000000))
    # then add another 30s for safety
    duration=$(( duration + 30))
    echo "Recording CSI data for $duration seconds"

    # for forensics
    echo $(date) - begin 
    # start a job that logs indefinitely the csi data into file rawdata
    /root/linux-80211n-csitool-supplementary/netlink/log_to_file rawdata &
    # record its pid
    pid=$!
    # wait for the estimated duration
    sleep $duration
    # kill the recording job
    kill $pid
    # for forensics
    echo $(date) - end
    md5sum rawdata
}

########################################
# just a wrapper around the individual functions
function main() {
    command=$1; shift
    case $command in
	init-sender|init-receiver|run-sender|run-receiver)
	    $command "$@" ;;
	*) echo unknown command \"$command\" ;;
    esac
}

main "$@"
