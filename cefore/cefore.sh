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
    cefnetdstart
    csmgrdstop
    csmgrdstart
    cefputfile ccn:/realRemote/test ./big_buck_bunny.mp4
}


