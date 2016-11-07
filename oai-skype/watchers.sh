#!/bin/bash

for arg in "$@"; do
    fitname=fit$(printf "%02d" $arg)
    echo $fitname
    ssh -X onelab.inria.oai.oai_build@faraday.inria.fr ssh -X root@$fitname xterm &
done
