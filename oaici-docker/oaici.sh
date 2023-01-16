#!/bin/bash


# fitname returns the FIT name from id
#
function fitname() {
    id=$1; shift

    if [ "${id}" -lt 10 ]; then
	echo -n "fit0$id"
    else
	echo -n "fit$id"
    fi
}

####################
# These are functions used to handle OAICI functions from faraday
#
#


# init-epc expects the following argument
# * the fit ID (01-37) where to run the EPC, e.g., 17
# * the fit ID (01-37) where to run the eNB, e.g., 23
function init-epc (){
    epc=$1; shift
    enb=$1; shift

    fit_epc=$(fitname $epc)
    ssh root@$fit_epc \
	    "echo 'Do some network manipulations for containers to talk to each other';
    	    sysctl net.ipv4.conf.all.forwarding=1;
    	    iptables -P FORWARD ACCEPT;
    	    ip route add 192.168.61.0/26 via 192.168.3.$enb dev control"
}

# start-epc expects the following argument
# * the fit ID (01-37) where to run the EPC, e.g., 17
function start-epc (){
    epc=$1; shift

    fit_epc=$(fitname $epc)
    echo "****** fit_epc: $fit_epc"
    sshpass -p "linux" ssh oaici@$fit_epc \
	    "echo 'Deploy the EPC';
    	    cd openair-epc-fed/docker-compose/inria-oai-mme/;
    	    echo 'docker-compose config --service'; docker-compose config --service;
    	    echo 'docker-compose up -d db_init'; docker-compose up -d db_init;
    	    echo 'wait for 50s'; sleep 50;
	    docker logs prod-db-init;
    	    echo 'docker-compose up -d oai_spgwu trf_gen'; docker-compose up -d oai_spgwu trf_gen;
    	    echo 'Wait for 30s'; sleep 30;
	    docker logs prod-oai-mme;"
    
}

# stop-epc expects the following argument
# * the fit ID (01-37) where runs the EPC, e.g., 17
function stop-epc (){
    epc=$1; shift
    
    fit_epc=$(fitname $epc)
    sshpass -p "linux" ssh oaici@$fit_epc \
	    "echo 'Stop the EPC';
    	    cd openair-epc-fed/docker-compose/inria-oai-mme/;
    	    echo 'docker-compose down'; docker-compose down"
}


# init-enb expects the following argument
# * the fit ID (01-37) where to run the eNB, e.g., 23
# * the fit ID (01-37) where to run the EPC, e.g., 17
function init-enb (){
    enb=$1; shift
    epc=$1; shift
    
    fit_enb=$(fitname $enb)
    ssh root@$fit_enb \
	    "echo 'Do some network manipulations for containers to talk to each other'; 
	    sysctl net.ipv4.conf.all.forwarding=1; 
    	    iptables -P FORWARD ACCEPT; 
    	    ip route add 192.168.61.192/26 via 192.168.3.$epc dev control;"
}

# start-enb expects the following argument
# * the fit ID (01-37) where to run the eNB, e.g., 23
function start-enb (){
    enb=$1; shift
    
    fit_enb=$(fitname $enb)
    sshpass -p "linux" ssh oaici@$fit_enb \
	    "echo 'Deploy the eNB';
    	    cd ~/openairinterface5g/ci-scripts/yaml_files/inria_enb_mono_fdd;
	    echo 'docker-compose config --service'; docker-compose config --service;
    	    echo 'docker-compose up -d enb_mono_fdd'; docker-compose up -d enb_mono_fdd;"
}

# stop-enb expects the following argument
# * the fit ID (01-37) where to run the eNB, e.g., 23
function stop-enb (){
    enb=$1; shift
    
    fit_enb=$(fitname $enb)
    sshpass -p "linux" ssh oaici@$fit_enb \
	    "echo 'Stop the eNB';
    	    cd ~/openairinterface5g/ci-scripts/yaml_files/inria_enb_mono_fdd;
	    echo "docker-compose down"; docker-compose down"
}

# logs-mme expects the following argument
# * the fit ID (01-37) where EPC runs, e.g., 17
function logs-mme (){
    epc=$1; shift

    fit_epc=$(fitname $epc)
    sshpass -p "linux" ssh oaici@$fit_epc \
	    "cd openair-epc-fed/docker-compose/inria-oai-mme/;
    	    echo 'docker logs prod-oai-mme --follow'; docker logs prod-oai-mme --follow"
}

# logs-enb expects the following argument
# * the fit ID (01-37) where runs the eNB, e.g., 23
function logs-enb (){
    enb=$1; shift

    fit_enb=$(fitname $enb)
    sshpass -p "linux" ssh oaici@$fit_enb \
            "cd ~/openairinterface5g/ci-scripts/yaml_files/inria_enb_mono_fdd;
            echo 'docker logs prod-enb-mono-fdd --follow';
            docker logs prod-enb-mono-fdd --follow"
}

########################################
# just a wrapper so we can call the individual functions from faraday. so e.g.
# oaici.sh logs-enb 23
#

"$@"

