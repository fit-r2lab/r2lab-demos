#!/bin/bash

slice=onelab.inria.oai.oai_build

for arg in "$@"; do
    fitname=fit$(printf "%02d" $arg)
    echo Starting xterm on $fitname as slice $slice
    ssh -X $slice@faraday.inria.fr ssh -X root@$fitname xterm &
done
