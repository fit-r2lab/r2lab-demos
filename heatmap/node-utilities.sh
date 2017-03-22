#!/bin/bash

####################
# This is our own brewed script for setting up a wifi network
# it run on the remote machine - either sender or receiver
# and is in charge of initializing a small ad-hoc network
#
# Thanks to the RunString class, we can just define this as
# a python string, and pass it arguments from python variables
#


# we expect the following arguments
# * wireless driver name (iwlwifi or ath9k)
# * the wifi network name to join
# * the wifi frequency to use

function init-ad-hoc-network (){
    driver=$1; shift
    netname=$1; shift
    freq=$1;   shift
    phyrate=$1; shift
    antmask=$1; shift
    txpower=$1; shift

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

    # install tshark on the node for the post-processing step
    apt-get install tshark
    
    ifname=$(wait-for-interface-on-driver $driver)

    echo configuring interface $ifname
    # make sure to wipe down everything first so we can run again and again
    ip address flush dev $ifname
    ip link set $ifname down 
    # configure wireless
    iw phy phy0 set antenna $antmask
    echo "iw phy phy0 set antenna $antmask"
    sleep 1
    iw dev $ifname set type ibss
    # set the Tx power Atheros'range is between 5dbm (500) and 14dBm (1400)
    echo "iw dev $ifname set txpower fixed $txpower"
    iw dev $ifname set txpower fixed $txpower
    ip link set $ifname up
    # set to ad-hoc mode and set the right PHY rate
    iw dev $ifname ibss join $netname $freq
    echo "iw dev $ifname ibss join $netname $freq"
    ip address add $ipaddr_mask dev $ifname
    iw dev $ifname set bitrates legacy-2.4 $phyrate
    echo "iw dev $ifname set bitrates legacy-2.4 $phyrate"


    # set the wireless interface in monitor mode                                                                           
    iw phy phy0 interface add moni0 type monitor
    ip link set moni0 up
    # then, run tcpdump with the right parameters 
    
#    tcpdump -U -W 2 -i moni0 -y ieee802_11_radio -w "/tmp/"$(hostname)".pcap"


    ### addition - would be cool to come up with something along these lines that
    # works on both cards
    # a recipe from Naoufal for Intel
    # modprobe iwlwifi
    # iwconfig wlan2 mode ad-hoc
    # ip addr add 10.0.0.41/16 dev wlan2
    # ip link set wlan2 up
    # iwconfig wlan2 essid mesh channel 1
    
}

function my-ping (){
    dest=$1; shift
    ptimeout=$1; shift
    pint=$1; shift
    psize=$1; shift
    pnumber=$1; shift
    
    echo "ping -W $ptimeout -c $pnumber -i $pint -s $psize -q $dest >& /tmp/ping.txt"
    ping -w $ptimeout -c $pnumber -i $pint -s $psize -q $dest >& /tmp/ping.txt
    result=$(grep "%" /tmp/ping.txt)
    echo "$(hostname) -> $dest: ${result}"
    return 0
}


function process-pcap (){
    node=$1; shift

    tshark -2 -r /tmp/fit"$node".pcap  -R "ip.dst==10.0.0.$node && icmp"  -Tfields -e "ip.src" -e "ip.dst" -e "radiotap.dbm_antsignal" > /tmp/result"-$node".txt
    echo "Run tshark post-processing on node fit$node"
    return 0
}



########################################
# just a wrapper so we can call the individual functions. so e.g.
# node-utilities.sh tracable-ping 10.0.0.2 20
# results in calling tracable-ping 10.0.0.2 20

"$@"
