#!/bin/bash

function put-media-on-publisher() {
    [ -f ./big_buck_bunny.mp4 ] && echo "File big_buck_bunny.mp4 already there" || wget http://clips.vorwaerts-gmbh.de/big_buck_bunny.mp4
    cefputfile ccn:/realRemote/test -f ./big_buck_bunny.mp4 -t 100000
}

function configure-ip-ap() {
    node=$1; shift
    echo "In configure-ip-ap(): configure atheros driver with IP 10.0.0.$node"
    ifconfig atheros 10.0.0."$node" netmask 255.255.255.0 up
}


function connect-to-ap() {
    node=$1; shift
    echo "In connect-to-ap(): configure atheros driver with IP 10.0.0.$node"
    ifconfig atheros down
    ifconfig atheros 10.0.0."$node" netmask 255.255.255.0 up
    echo "connect to SSID: Cefore Experiment"
    iw dev atheros connect "Cefore Experiment"
}

function enable-usrp-ethernet() {
    ifconfig data down 2>/dev/null
    ip link set data name usrp
    ifconfig usrp 192.168.10.1 netmask 255.255.255.0 broadcast 192.168.10.255
    ifconfig usrp up
}

# this is IMPORTANT, otherwise calling this script .. does nothing
"$@"
