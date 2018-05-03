#!/bin/bash

function route-sample-batman(){
    sample="0"

    while [ 1 ]
    do
    echo "SAMPLE : $sample "
    ip route ls table 66 | grep src
    sleep 1
    sample=$[$sample+1]
    done

    return 0
}
function route-sample-olsr(){
    sample="0"
#trap 'end-route-sample olsr' INT

    while [ 1 ]
    do
    echo "SAMPLE : $sample "
    route -n | grep 10.0.0.* | grep UGH
    sleep 1
    sample=$[$sample+1]
    done
    return 0
}
function route-sample(){
    route-sample-$2 > $1
}
"$@"
