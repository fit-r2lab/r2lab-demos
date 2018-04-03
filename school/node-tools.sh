#!/bin/bash

function init-ad-hoc-network () {
    interface=$1; shift;
    netname=$1; shift

    echo "whatever it takes to init ad-hoc net $netname on interface $interface"

}

subcommand="$1"; shift

$subcommand "$@"
