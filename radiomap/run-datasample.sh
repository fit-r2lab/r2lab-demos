#!/bin/bash
# here is how datasample was obtained
# this script accepts acquiremap options like -n or -l or -s
#
# do not forget to
# * get a lease,
# * specify that slice with -s
# * and to load images with -l
#
./acquiremap.py "$@" -o datasample -t 5 -t 9 -t 14 -r 1 -r 54 -a 1 -a 3 -a 7 -c 1 -c 11 -c 40
