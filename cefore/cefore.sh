#!/bin/bash

function put-media-on-publisher() {
    [ -f ./big_buck_bunny.mp4 ] && echo "File big_buck_bunny.mp4 already there" || wget http://clips.vorwaerts-gmbh.de/big_buck_bunny.mp4
    cefputfile ccn:/realRemote/test -f ./big_buck_bunny.mp4 -t 100000
}

# this is IMPORTANT, otherwise calling this script .. does nothing
"$@"
