#!/bin/bash

#mod_params="xt_GTPUSP:mtu"
#nodes="fit16"
#for node in $nodes; do
#    for mod_param in $mod_params; do
#	module=$(cut -d: -f1 <<< $mod_param)
#	param=$(cut -d: -f2 <<< $mod_param)
#	echo ========== module $module on node $node has param $param = $(ssh root@$node cat /sys/module/$module/parameters/$param)
#    done
#done

node_ints="fit19:data fit16:data fit16:control faraday:control faraday:data"
for node_int in $node_ints; do
	node=$(cut -d: -f1 <<< $node_int)
	int=$(cut -d: -f2 <<< $node_int)
	echo ========== interface $int on $node $(ssh root@$node ip link show $int | grep mtu | sed -e 's,qdisc.*,,' -e 's,\<.*\>,,')
done

node_ints="fit19:data fit16:data fit16:control faraday:control"
for node_int in $node_ints; do
	node=$(cut -d: -f1 <<< $node_int)
	int=$(cut -d: -f2 <<< $node_int)
	echo ========== interface $int on $node
	ssh root@$node ethtool -k $int | egrep 'tation-offload|receive-offload'
done

#echo "========== git diff in SRC/SGW in openair-cn on fit16"
#ssh root@fit16 "(cd openair-cn/SRC/SGW; git diff)"
