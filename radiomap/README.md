# Purpose

R2lab's radiomap is a set of measurements that act as a calibration of the testbed.
The goal is to measure **received power** at all node locations when a radio signal is sent **from any given sender** node.
Additionally, that same experiment is carried out with **various settings** for the emitted signal, like emission power, Tx rate, and with various antenna setups (single antenna, multiple antennas).

# Workflow

End to end experiment involves 3 successive stages:

1. data acquisition per se, including post-processing (aggregation)
1. data visualization per se

Each of these phases can be carried out with 

* a `acquiremap.py` python script for data acquisition per se, and
* a `visumap.ipynb` interactive notebook, that again is written in python.

For convenience, this git repository also features a directory `datasample` that contains one dataset obtained by running the first-stage acquisition script, so that visualization can be performed right away, as a way to give a quick sense of the results. 

# `acquiremap.py`

Run in R2lab a scenario in which each node runs a tcpdump and, in turn, 
sends a number of ping packets to each other node.

At the end, pcap files (called `fit<N>.pcap`) at node `N` is analyzed locally at node N to 
retrieve the RSSI values received from each other node on its antenna(s), and the result 
is in file `result-N.txt`.

Then create locally a directory called `trace-T{}-r{}-a{}-t1-i0.008-S64-N10` containing all the files retrieved from all nodes, i.e., `fitN.pcap`, `result-N.txt` for all N nodes.

With:

* `T{}` identifies Tx sending power for nodes (e.g. 500 to 1400):
* `r{}` identifies PHY Tx rate used on all nodes (1 to 54 Mbps)
* `a{}` identifies the antennas on nodes

Then, it calls locally the post-processing function `processmap.py` to generate files `rssi-<N>.txt` and the final file `RSSI.txt` that will be used to plot the heatmap.

NOTE: Currently only Atheros NIC (with ath9k driver) are supported in these scripts, despite the presence of the `-w` option.

```
$ ./acquiremap.py --help
usage: acquiremap.py [-h] [-s SLICE] [-l] [-m MAX] [-p PARALLEL] [-a {1,3,7}]
                    [-r PHY_RATE] [-f CHANNEL_FREQUENCY] [-T TX_POWER]
                    [-t PING_TIMEOUT] [-i PING_INTERVAL] [-S PING_SIZE]
                    [-N PING_NUMBER] [-n] [-v] [-d]

optional arguments:
  -h, --help            show this help message and exit
  -s SLICE, --slice SLICE
                        specify an alternate slicename (default:
                        inria_radiomap)
  -l, --load-images     if set, load image on nodes before running the exp
                        (default: False)
  -m MAX, --max MAX     will run on all nodes between 1 and this number
                        (default: 5)
  -p PARALLEL, --parallel PARALLEL
                        run in parallel, with this value as the limit to the
                        number of simultaneous pings - -p 0 means no limit
                        (default: None)
  -a {1,3,7}, --antenna-mask {1,3,7}
                        specify antenna mask for each node (default: 7)
  -r PHY_RATE, --phy-rate PHY_RATE
                        specify PHY rate (default: 1)
  -f CHANNEL_FREQUENCY, --channel-frequency CHANNEL_FREQUENCY
                        specify the channel frequency for each node (default:
                        2412)
  -T TX_POWER, --tx-power TX_POWER
                        specify Tx power (default: 1400)
  -t PING_TIMEOUT, --ping-timeout PING_TIMEOUT
                        specify timeout for each individual ping (default: 1)
  -i PING_INTERVAL, --ping-interval PING_INTERVAL
                        specify time interval between ping (default: 0.008)
  -S PING_SIZE, --ping-size PING_SIZE
                        specify packet size for each individual ping (default:
                        64)
  -N PING_NUMBER, --ping-number PING_NUMBER
                        specify number of ping packets to send (default: 100)
  -n, --dry-run         do not run anything, just print out scheduler, and
                        generate .dot file (default: False)
  -v, --verbose-ssh     run ssh in verbose mode (default: False)
  -d, --debug           run jobs and engine in verbose mode (default: False)
```  
  

---
# Utility

## `run-all.sh`

Simple shell script to run all the different possible scenarios with heatmap.py with different Tx power, PHY Tx rate and Antenna configurations. Book R2lab for 2 hours to run it.

It can also be used to select the ping parameters.

It will create a different directory for each scenario.

## `post-process.py` 

This is actually called by `acquiremap.py`. It computes average RSSI values for each node, and fill values when they are missing with either `RSSI_MIN` or `RSSI_MAX`

* input RSSI files `result-X.txt` obtained through tshark for each receiving node, contain RSSI values corresponding to ICMP ping packets sent by other nodes. The number of RSSI values for each ping depends on the number of antennas used;
* output RSSI files `rssi-X.txt` contain the average RSSI values received at node X;
* global unique output file `RSSI.txt` contains the overall RSSI information that will be used to plot the radiomap.

---
# Plotting

Now how to plot the radiomaps. You have several options...

## notebook

The most convenient way is using jupyter notebook:

### Installation 

First if not installed, use the following steps (on OSX):

```
$ sudo pip3 install jupyter
$ sudo pip3 install --upgrade notebook
$ jupyter nbextension enable --py --sys-prefix widgetsnbextension
```

Then start a notebook server as usual; you may need to mention this extra option if you run an early release of jupyter-5.0
```
$ jupyter notebook --NotebookApp.iopub_data_rate_limit=10000000000
```

Double click on the file `heatmap-rssi.ipynb` on your browser, and evaluate the commands using "Shift-Enter" (if needed, see other Internet resources about how to use a notebook)

The notebook contains all information about its own capabilities.


## other option

XXX I suspect this section is obsolete XXX

If you prefer plotting 3D heatmaps, you can use the two other options:
one using matplotlib (called plot-heatmap.py) and the other one using plotly
(called plotly-heatmap.py). plot-all.py allows you to animate heatmaps, and
it is based on plot-heatmap.py.


```
Usage: plot-heatmap.py [-h] [-s SENDER] [-a {0,1,2,3}] [-v] [-d]

optional arguments:
  -h, --help            show this help message and exit
  -s SENDER, --sender SENDER
                        FIT node sender between 1 and the number of R2lab
                        nodes
  -a {0,1,2,3}, --rssi-pos {0,1,2,3}
                        specify the RSSI value to plot according to antennas,
                        default is 0
  -v, --verbose
  -d, --debug
```

---

```
Usage: plot-all.py [-h] [-m MAX] [-s SENDER] [-a {0,1,2,3}] [-t TIME] [-l]
                   [-x] [-d]

optional arguments:
  -h, --help            show this help message and exit
  -m MAX, --max MAX     max FIT node number
  -s SENDER, --sender SENDER
                        target FIT node sender
  -a {0,1,2,3}, --rssi-pos {0,1,2,3}
                        specify the RSSI value to plot according to antennas,
                        default is 0
  -t TIME, --time TIME  delay between each display, default=1000 for 1s
  -l, --loop
  -x, --xterm-view
  -d, --debug
```
