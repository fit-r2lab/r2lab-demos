#!/bin/bash

# just retrieve MTU and offload information at the specified node
function probe_mtu_offload() {
    targets=""
    for number in "$@"; do
	targets="$targets root@fit$number"
    done
    apssh -t "$targets" "ip link show data | grep mtu | sed -e 's,qdisc.*,,' -e 's,\<.*\>,,' ; ethtool -k $int | egrep '(tcp|udp|generic|large).*segmentation'"
}

# run ping between $from and $to on the data interface using various sizes
function test_ping() {
    from=$1; shift
    to=$1; shift
    # need to log into fit<nn>
    nodefrom=fit$from
    # but to ping data<nn> on interface <data>
    nodeto=data$to
    for size in 1450 1500 1580 5000 9000 12000; do
	echo -n "ping in $nodefrom -> $nodeto with size $size ... "
	ssh root@$nodefrom ping -I data -M do -c 1 -W 1 -s $size $nodeto >& /dev/null && echo OK || echo KO
    done
}

# bind both tools
function main() {
    from="$1"; shift
    to="$1"; shift
    probe_mtu_offload $from $to
    test_ping $from $to
}

# defaults in sync with oai-scenario.py
if [[ -z "$@" ]]; then
    from=16
    to=19
else
    from=$1; shift
    to=$1; shift
fi

echo "from=$from (should be your EPC) - to=$to (should be your enb)"
main $from $to
