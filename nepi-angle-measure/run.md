# Run scope

    receiver=5
    senders="15 14 24 8 9 12 7"

# Nodes imaging

### log onto the R2lab gateway
    ssh onelab.inria.r2lab.admin@faraday.inria.fr

### turn off all nodes 
    off -a

### load the image on all subject nodes
    rload --curses --image intelcsi $receiver $senders 

# launch experiments 
    ./angle-measure.py -d run5-recvduration -r $receiver -s "$senders" --packets 50000 --size 100 --period 100

****

# List of nodes that have an Intel card

 5 7 8 9 10 12 14 15 18 22 24 25 26 30 31 32 33 34 35 36 37

# Other runs

### run2 : receiver on node 31
    receiver=31
    senders="26 24 25 30"

### single-node run
    receiver=5
    senders="15 8"

### more complete run (see run5)
    senders="15 14 24 8 9 12 7 31 32 33"
