#!/bin/bash                                                                                                       
# Run all experiments and post-process the traces
#
#
# TT 21/3/2017
#

NODES=37
PHY_RATE="1 54"
TX_POWER="500 1400"
ANT_MASK="1 3 7"
CHANNEL=2462
PING_NB=10

# 1st step is to run the experimentation on R2lab with the required parameters.
# The "heatmap.py" nepi-ng script will do all the job and will create at the
# end a  directory for each scenario with all the ping logs and the pcap traces for each node
# 

# LOAD must be set to 1 if nodes are not yet running on R2lab to switch them on and load the right images
LOAD=1

for tx_power in `echo $TX_POWER`
do 
    for phy_rate in `echo $PHY_RATE`
    do
	for ant_mask in `echo $ANT_MASK`
	do
	    if test $LOAD -eq 1
	    then
		./heatmap.py  -m "$NODES" -f "$CHANNEL" -r "$phy_rate" -a "$ant_mask" -T "$tx_power" -N "$PING_NB" -l
		LOAD=0
	    else
		./heatmap.py  -m "$NODES" -f "$CHANNEL" -r "$phy_rate" -a "$ant_mask" -T "$tx_power" -N "$PING_NB"
	    fi
	done
    done
done

echo "*********** NOW POSTPROCESS ALL TRACES ON NEW DIRECTORIES *************"

for d in `ls |grep trace-T`
do
    cd "$d"
    echo "postprocessing $d"
    for ((j=1; j<="$NODES"; j++))
    do
        tshark -2 -r fit"$j".pcap  -R "ip.dst==10.0.0.$j && icmp"  -Tfields -e "ip.src" -e "ip.dst" -e "radiotap.dbm_antsignal" >> result"-$j".txt
    done
# Retrieve the number of antennas from the directory name
# which is on the form: "trace-T1400-r1-a1-t1-i0.008-S64-N10"
    ant_number=`echo "$d" | awk -F- '/a/ {print $4}' | sed s/a//`
# Then call the last processing step to create rssi*.txt files
    ../post-process.py -m "$NODES" -a "$ant_number"
    cd ..
done

