#!/bin/bash
# here is how datasample was obtained
# this script accepts acquiremap options like -n or -l or -s
#
# do not forget to
# * get a lease,
# * specify that slice with -s
# * and to load images with -l
#
# keep channel 40 out of scope for now as we need an eprom upgrade
# to get our atheros cards to run the 5GHz band
#

./acquiremap.py -o datasample -t 5 -t 9 -t 14 -r 1 -a 1 -a 3 -a 7 -c 1 -c 11 "$@"

# it is recommended to redirect the out/err flows like this
#
# rm -rf mymap; run-datasample.sh -o mymap 2>&1 | tee mymap.log
#

