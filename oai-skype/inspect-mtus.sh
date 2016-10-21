#!/bin/bash

#node_ints="fit19:data fit16:data fit16:control faraday:control faraday:data"
node_ints="fit19:data fit16:data"
for node_int in $node_ints; do
	node=$(cut -d: -f1 <<< $node_int)
	int=$(cut -d: -f2 <<< $node_int)
	echo "========== interface $int on $node"
	echo "******** MTU"
#	ssh root@$node ip link show $int | grep mtu | Sed -e 's,qdisc.*,,' -e 's,\<.*\>,,'
	ssh root@$node ip link show $int | grep mtu | sed -e 's,qdisc.*,,' -e 's,\<.*\>,,'
	echo "******** OFFLOAD"
#	ssh root@$node ethtool -k $int
	ssh root@$node ethtool -k $int | egrep '(tcp|udp|generic|large).*segmentation'
done

#echo "========== git diff in SRC/SGW in openair-cn on fit16"
#ssh root@fit16 "(cd openair-cn/SRC/SGW; git diff)"
