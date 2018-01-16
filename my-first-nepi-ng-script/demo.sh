#!/bin/bash

case $1 in
    prepare-receiver)
        echo "prepare receiver on $(hostname)" | tee > PREP
        sleep 1
        ;;
    prepare-sender)
        echo "prepare sender on $(hostname)" | tee > PREP
        sleep 2
        ;;
    run-receiver)
        echo "run receiver on $(hostname)" | tee > RUN
        sleep 1
        ;;
    run-sender)
        echo "run sender on $(hostname)" | tee > RUN
        sleep 2
        ;;
esac
