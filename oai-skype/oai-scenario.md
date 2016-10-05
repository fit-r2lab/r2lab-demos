![](oai-nodes.001.png)


# Access to `macphone` : the mac controlling the phone

## from faraday

Only a command-line access; this will let you turn the phone on or off, but that's it:

```
onelab.inria.oai.oai_build@faraday:~$ macphone
Last login: Wed Oct  5 15:28:08 2016 from faraday4
macphone:~ tester$ help
#################### Native bash help
<snip bash help>
#################### R2lab: tools for managing R2lab phone from macphone
phone-on	      turn off airplane mode
phone-off       turn off airplane mode
phone-status    shows wheter airplane mode is on or off
phone-reboot    reboot phone with abd reboot
refresh 	      retrieve latest git repo, and source it in this shell
```

## from another mac using *Screen sharing* - 

This method gives you a screen sharing, so you can access many more features

From the public Internet, use target `faraday.inria.fr` -> `tester/tester++`

You can in particular open a terminal, and also do things like `help` or `phone-status`

# All-in-one

## a `nepi-ng` script is available

We have a script that sets up the experiment background completely in one run. At this point, it does:

* optionnally load correct images on all 4 nodes (including scrambler)
* turn the phone off in all cases
* and then 
  * kill, init, configure and start
  * on all 3 nodes (except scrambler for now)
* at that point the **5G setup is complete** and you can do what your experiment is about: **play with the phone**, place calls, etc..
* all this time the script is prompting you for an experiment name; **once you enter one*, it will:
   * all 3 nodes the relevant nodes are captured (put in tar remotely)
   * and then collected in the current directory

Typically if you enter `redeux` as the name for the experiment you will find 

```
~/git/r2lab/demos/oai-skype $ ls -l redeux*
-rw-r--r--  1 parmentelat  staff  3778 Oct  5 18:53 redeux-enb.tgz
-rw-r--r--  1 parmentelat  staff  8755 Oct  5 18:53 redeux-epc.tgz
-rw-r--r--  1 parmentelat  staff  5767 Oct  5 18:53 redeux-hss.tgz  
```

## to use it

* install requirements `sudo pip3 install apssh asynciojobs`
* or update requirements `sudo pip3 install --upgrade apssh asynciojobs`
* where `cd r2lab/demos/oai-skype`
* run **with image loading** `./oai-scenario.py --load`
* or just **restart** it all `./oai-scenario.py`
* run with `--help` to see list of available options (like: select other nodes)

# Manually


## Preparation

### the HSS box

```
n 23
rload -i u16-oai-gw 23 16
rwait -t 120
ss
refresh
demo
```

### the EPC box

```
n 16
rwait -t 500
ss
refresh
demo
```
### the ENB box

```
n 19
rload -i u16-oai-enb 19 
rwait -t 300
ss
refresh
demo
```

## Run it

## common scenario for the 3 boxes

```
init
configure
start
```

At this point, or if you have used the all-in-one script, you can just do

```
logs
```

## Captures

The capture system requires you to use the same name on all 3 boxes

```
capture my-experiment
```

To retrieve them, you can use from your laptop this utility script



# Scrambling

## Prep

```
n 11
rload -i oai-scrambler
rwait
ss
refresh
demo
```

## run

```
scrambler [-blast]
```

*****
*****
*****


# Various notes

## Note on base images - ubuntu 16 vs 14

Images are available for ubuntu 16 for now; they are named `oai16-gw-base` and `oai16-enb-base`.

I'm working on redoing the same for ubuntu14, the names will of course be `oaiu14*` when they are ready

## DB report

```
select imsi, imei, access_restriction,  mmeidentity_idmmeidentity from users where imsi = 208950000000002;

select * from mmeidentity where mmerealm='r2lab.fr' ;
```
