# OpenAirInterface demo

The script `oai-scenario.py` here can be used to run a simple experiment in R2lab, that

* deploys an LTE infrastructure on a wired network
  * using 2 regular nodes for running a HSS and an EPC
  * and one USRP-enabled node for running a e-nodeB (base station)

* optionnally, various optional configurations can be deployed as well, with
  * additional nodes to be used as soft UE's based on a E3372 hardware
  * additional nodes to be used as soft UE's based on OAI's code for the UE
  * the default is to associate the nexus phone in this setup, but the other Moto can be involved as well - or none

# Requirements

This script requires python-3.5

It uses [nepi-ng](https://nepi-ng.inria.fr/), that you can install with

```
pip3 install asynciojobs apssh
```

# Resources

* Downlink: 2.56G
* Uplink:   2.68G

In addition to the defaults for the 3 core nodes, it is advisable to use

* `fit11` to watch traffic in both directions (it has no duplexer)
* `fit16` to scramble the **uplink** (it has a UE duplexer)

# Commands
    oai-scenario.py --load --xterm 11 --xterm 16

or shorter

    oai-scenario.py -l -x 11 -x 16


## scrambler

On the scrambler node you should have commands like (double-check you duplexer though):

* `scramble-downlink`,
* `scramble-downlink-mid` and
* `scramble-downlink-blast`,
* as well as 3 similar like `scramble-uplink` on the uplink side

**NOTE**

On older images, you can gain access to these new commands by doing

```
cd /root/r2lab/
git checkout public
refresh
```

## spectrum-analyzer

You can run either

* `watch-downlink` or
* `watch-uplink`
