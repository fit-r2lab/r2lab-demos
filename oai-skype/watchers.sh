#!/bin/bash

slice=onelab.inria.oai.oai_build

font="-*-fixed-medium-*-*-*-20-*-*-*-*-*-*-*"
xterm_args="-fn $font -bg wheat -geometry 90x10"

for arg in "$@"; do
    fitname=fit$(printf "%02d" $arg)
    echo Starting xterm on $fitname as slice $slice
    ssh -X $slice@faraday.inria.fr ssh -X root@$fitname xterm "$xterm_args" &
done
