#!/bin/bash

function route-sample-batman(){
    sample="0"
    #echo $$ > sampling.pid

    while [ 1 ]
    do
    echo "SAMPLE : $sample "
    ip route ls table 66 | grep src
    sleep 0.5
    sample=$[$sample+1]
    done

    return 0
}
function route-sample-olsr(){
    sample="0"

#trap 'end-route-sample olsr' INT
    #echo $$ > sampling.pid

    while [ 1 ]
    do
    echo "SAMPLE : $sample "
    route -n | grep 10.0.0.* | grep UGH
    sleep 0.5
    sample=$[$sample+1]
    done
    return 0
}
#function end-sample(){
#  exit 0
#}
function route-sample(){
    trap 'end-sample' TERM

    route-sample-$2 > /root/$1

    return 0
}
#function kill-route-sample(){
#prot=$1; shift
#    sleep 1
#    echo $(cat sampling.pid)
    #kill -s SIGTERM $(cat sampling.pid)
#    sleep 1
#    return 0
#}
"$@"
