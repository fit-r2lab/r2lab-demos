# OpenAirInterface demo

The script `oai-scenario.py` here can be used to run a simple experiment in R2lab, that

* deploys an LTE infrastructure on a wired network 
  * using 2 regular nodes for running a HSS and an EPC
  * and one USRP-enabled node for running a e-nodeB (base station)

* associates the Nexus phone in this cell

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

	