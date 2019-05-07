#!/bin/bash

BINDIR="./bin"
CONFIGDIR="./Cefore-Config"
CEFCONF="/usr/local/cefore/cefnetd.conf"
CEFFIB="/usr/local/cefore/cefnetd.fib"

#==== Fit06(UE) =====
HOST="root@fit06"
FIB="ccn:/streaming udp 172.16.0.1"
scp $BINDIR/cefnetd $BINDIR/cefctrl ${HOST}:/usr/local/sbin
scp $BINDIR/cefstatus $BINDIR/cefnetdstart ${HOST}:/usr/local/bin
ssh $HOST mkdir -p /usr/local/cefore
scp $CONFIGDIR/* ${HOST}:/usr/local/cefore
ssh $HOST echo "CS_MODE=1" \> $CEFCONF
ssh $HOST echo $FIB \> $CEFFIB
ssh $HOST killall cefnetd 
ssh $HOST cefnetdstart 

#==== Fit19(UE) =====
#HOST="root@fit19"
#FIB="ccn:/streaming udp 172.16.0.1"
#scp $BINDIR/cefnetd $BINDIR/cefctrl ${HOST}:/usr/local/sbin
#scp $BINDIR/cefstatus $BINDIR/cefnetdstart $BINDIR/streamtest ${HOST}:/usr/local/bin
#ssh $HOST mkdir -p /usr/local/cefore
#scp $CONFIGDIR/* ${HOST}:/usr/local/cefore
#ssh $HOST echo "CS_MODE=1" \> $CEFCONF
#ssh $HOST echo $FIB \> $CEFFIB
#ssh $HOST killall cefnetd 
#ssh $HOST cefnetdstart 

#==== Fit07(EPC) =====
HOST="root@fit07"
PUBADDR=""; # Specify Publisher Address
FIB="ccn:/streaming tcp ${PUBADDR}:80"
scp $BINDIR/cefnetd $BINDIR/cefctrl ${HOST}:/usr/local/sbin
scp $BINDIR/cefstatus $BINDIR/cefnetdstart ${HOST}:/usr/local/bin
ssh $HOST mkdir -p /usr/local/cefore
scp $CONFIGDIR/* ${HOST}:/usr/local/cefore
ssh $HOST echo "CS_MODE=1" \> $CEFCONF
ssh $HOST echo $FIB \> $CEFFIB
ssh $HOST killall cefnetd 
ssh $HOST cefnetdstart 

<< COMMENTOUT
COMMENTOUT
