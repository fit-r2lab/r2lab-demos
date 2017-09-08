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
    
#    # Avoid unexpected upgrades that could lock our apt-get update and limit reproducibility
#    apt-get -y purge unattended-upgrades

    # make sure to use the latest code on the node
    git-pull-r2lab

#    turn-off-wireless

    echo "Setting regulatory domain to CR"
    iw reg set CR

    ipaddr_mask=10.0.0.$(r2lab-ip)/24

#    echo loading module $driver
#    modprobe $driver
    
    # sleep some random time for udev to trigger its rules and prevent 
    # errors when all nodes simulataneously want to apt-get install tshark
#    TSLEEP=$[($RANDOM % 10)+1]   
#    echo "Now sleep for $TSLEEP seconds"
#    sleep $TSLEEP

    # install tshark on the node for the post-processing step
## following for debug only
#    lsof /var/lib/dpkg/lock
#    ps axu
    # For now, as we are unsure unattended upgrades are running, remove possible lock. Ugly hack to be fixed...
#    rm -rf /var/lib/dpkg/lock
##
    echo  "Installing tshark"
    apt-get install -y tshark
    
    ifname=$(wait-for-interface-on-driver $driver)
    phyname=`iw $ifname info|grep wiphy |awk '{print "phy"$2}'`
#    moniname=`iw $ifname info|grep wiphy |awk '{print "moni"$2}'`
    moniname="moni-$driver"

    echo "Configuring interface $ifname on $phyname"
    # make sure to wipe down everything first so we can run again and again
    ip address flush dev $ifname
    ip link set $ifname down
    # Warning! if $moniname interface is up, it will prevent following configurations...
    echo "Removing monitor interface $moniname" 
    ip link set $moniname down 2>/dev/null
    # configure wireless
    if test ${ifname} == "atheros";  then
        # configure antennas
	echo "Configuring $phyname with antenna mask $antmask"
	iw phy $phyname set antenna $antmask
    fi
    iw dev $ifname set type ibss
    ip link set $ifname up
    # enable ad-hoc mode and set the target frequency
#    echo "Joining $netname with ibss mode on frequency $freq MHz"
#    iw dev $ifname ibss join $netname $freq
    # set the Tx power. Note that for Atheros, range is between 5dbm (500) and 14dBm (1400)
    echo "Setting the transmission power to $txpower"
    iw dev $ifname set txpower fixed $txpower
    ip address add $ipaddr_mask dev $ifname
    ip link set $ifname down
    ip link set $ifname up
    echo "Joining $netname with ibss mode on frequency $freq MHz"
    iw dev $ifname ibss join $netname $freq
    sleep 2
    if test $freq -le 3000
      then 
	echo "Configuring bitrates to legacy-2.4 $phyrate Mbps"
	iw dev $ifname set bitrates legacy-2.4 $phyrate
      else
	echo "Configuring bitrates to legacy-5 $phyrate Mbps"
	iw dev $ifname set bitrates legacy-5 $phyrate
    fi

    # set the wireless interface in monitor mode
    echo "Creating monitor interface $moniname at $phyname"
    iw phy $phyname interface add $moniname type monitor 2>/dev/null
    ip link set $moniname up

    echo "List of authorized frequencies on $phyname:"
    iw $phyname info |grep -v -e disabled -e IR -e radar -e GI | grep MHz


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

    echo "Run tshark post-processing on node fit$node"
    tshark -2 -r /tmp/fit"$node".pcap  -R "ip.dst==10.0.0.$node && icmp"  -Tfields -e "ip.src" -e "ip.dst" -e "radiotap.dbm_antsignal" > /tmp/result"-$node".txt
    return 0
}



########################################
# just a wrapper so we can call the individual functions. so e.g.
# node-utilities.sh tracable-ping 10.0.0.2 20
# results in calling tracable-ping 10.0.0.2 20

"$@"
