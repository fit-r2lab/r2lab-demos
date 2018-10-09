#!/bin/bash

# Run the Cefore daemon on the simulator host
function run-cefore-sim() {
    echo 'In run-cefore-sim'
    cefnetdstop
    cefnetdstart
}

# Run the Cefore and Csmg daemons on the publisher host
function run-cefore-publisher() {
    echo 'In run-cefore-publisher'
    cefnetdstop
    csmgrdstop
    cefnetdstart
    sleep 2
    csmgrdstart
    sleep 1
    [ -f ./big_buck_bunny.mp4 ] && echo "File big_buck_bunny.mp4 already there" || wget http://clips.vorwaerts-gmbh.de/big_buck_bunny.mp4
    cefputfile ccn:/realRemote/test -f ./big_buck_bunny.mp4
}

# this is IMPORTANT, otherwise calling this script .. does nothing
"$@"
