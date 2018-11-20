![](oai-figures.002.png)


# Access to `macphone` : the mac controlling the phone

### from faraday

Only a command-line access; this will let you turn the phone on or off, but that's it:

```
inria_r2lab.tutorial@faraday:~$ macphone2
Last login: Wed Oct  5 15:28:08 2016 from faraday4

macphone2:~ tester$ help
#################### Native bash help
<snip bash help>
#################### R2lab: tools for managing R2lab phone from macphone
refresh 	retrieve latest git repo, and source it in this shell
phone-start-app
		start an app from its package name
phone-wifi-on   turn on wifi (tested on nexus 5)
phone-wifi-off  turn off wifi (tested on nexus 5)
phone-on	turn off airplane mode
phone-off       turn off airplane mode - does not touch wifi settings
phone-status    shows wheter airplane mode is on or off
phone-reboot    reboot phone with abd reboot

macphone2:~ tester$ phone-off
Turning OFF phone : turning on airplane mode
Broadcasting: Intent { act=android.intent.action.AIRPLANE_MODE (has extras) }
Broadcast completed: result=0
```

### visual access using *Screen sharing* or VNC

This method gives you a screen sharing, so you can access many more features.

From the public Internet, use e.g. target `faraday-macphone2.inria.fr` ->
`tester/tester++`

You can in particular open a terminal, and also do things like `help` or
`phone-status`, just like above.

# All-in-one demo

## a `nepi-ng` script is available

We have a script that sets up the experiment background completely in one run. At this point, it does:

* optionnally, with the `--load` option:
  * load adequate images on selected nodes (including accessories, like scrambler)
  * turn off the other nodes
  * turn off (put in airline mode) all phones
* and then
  * setup and start a core-network on one node,
  * setup and start an radio-access-network (e-nodeB) on one node,
  * start the phone
* at that point the **5G setup is complete** and you can do what your experiment is about
  * tweak the various pieces of the infrastructures, if needed
  * **deal with the phone manually**, run youtube or skype or chrome, etc..
* at this time the script is prompting you for an experiment name; **once you enter one**, it will:
   * capture relevant data from both nodes (i.e. put in tar remotely)
   * and these tar files are collected in the current directory.

**Warning** ***data collection in the new `mosaic` version still needs more work***

~~Typically if you enter `redeux` as the name for the experiment you will find 3 tar files as follows, which additionnally are all untared in `redeux`~~

```
~/git/r2lab/demos/oai-skype $ ls -l redeux*
to be rewritten
```

## how to use it

* install requirements `sudo pip3 install apssh asynciojobs r2lab`
  * or update requirements `sudo pip3 install --upgrade apssh asynciojobs r2lab`

Then from your git `r2lab-demos` repo:

* `cd openair`
* `git pull`
* run **with image loading** `./mosaic-demo.py --load`
* or just **restart** it all `./mosaic-demo.py`
* run with `--help` to see list of available options (like: select other nodes)

# Manually

## Preparation

### the CN box

```
n 7
rload -i mosaic-cn
rwait
s1
configure
```

### the RAN box

```
n 23
rload -i mosaic-ran
rwait
s1
configure 7
```

this the place where you tell your RAN where to find the CN


## Manage

Following commands are available:

* `start`
  * optionnally on the RAN box, you can do `start-graphical true` to start
    with a UI (requires an X11-enabled ssh session)

* `stop`
* `status`
* `journal`
  * **NOTE** that this is a wrapping call to `journalctl`,
   so you can for example use `journal -f` to observe logs as they show up.

## mosaic vs oai

This demo is essentially a refactoring of the OAI demo, that takes advantage of
the new software distribution paradigm known as mosaic5g.

As compared with the original demo:

* the core is still not quite working yet (RAN won't start)
* captures remain to be redeon entirely
* scrambling should be the same, but needs tested
* we use the `r2lab` python library - notably for preparing the testbed (load images, etc..)


****
****
****

**OBSOLETE SECTION**

****
****
****

**OBSOLETE SECTION**

****
****
****

**OBSOLETE SECTION**

****
****
****

***From this point on, the information below is obsolete and needs more work***


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

## base image

Both mosaic images are built on top of a ubuntu-16.04.5 disto,  i.e. with HWE
enabled, because a kernel >= 4.8 is required (actually is comes with 4.15)

## DB report

```
select imsi, imei, access_restriction,  mmeidentity_idmmeidentity from users where imsi = 208950000000002;

select * from mmeidentity where mmerealm='r2lab.fr' ;
```
