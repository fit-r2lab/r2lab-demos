#!/bin/bash

case $1 in
    prepare-receiver)
        echo $(date) "prepare receiver on $(hostname)" | tee PREP
        sleep 1
        ;;
    prepare-sender)
        echo $(date) "prepare sender on $(hostname)" | tee PREP
        sleep 2
        ;;
    run-receiver)
        echo $(date +"%M:%S") "run receiver on $(hostname)" | tee RUN
        sleep 1
        ;;
    run-sender)
        echo $(date +"%M:%S") "run sender on $(hostname)" | tee RUN
        sleep 2
        ;;
    epilogue)
        results="PREP-RECV PREP-SEND RUN-RECV RUN-SEND"
        ls -l $results
        grep -n . $results
        ;;
esac
