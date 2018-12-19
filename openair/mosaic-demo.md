![](oai-figures.002.png)


# commercial phones

There are **2 commercial phones** in the room. Both run some **Android**.
Each is controlled through a dedicated MAC called `macphone1` or `macphone2`, here's how to manage these.

### from faraday

Using ssh you can gain a command-line access to the phone; this will let you turn the phone on or off, but not much more:

```
mylaptop $ ssh inria_r2lab.tutorial@faraday.inria.fr
...
inria_r2lab.tutorial@faraday:~$
```

At that point the `macphone2` command (for example) is an alias for logging in through ssh in the mac controlling phone 2:

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

You can in particular:

* use Vysor to display the phone UI and use it as if you had it in your hand,
* open a terminal, and also do things like `help` or `phone-status`, just like above.

# All-in-one demo

## a `nepi-ng` script

We have a script that sets up the experiment background completely in one run. At this point, it does:

* optionnally, with the `--load` option:
  * load adequate images on selected nodes (including accessories, like scrambler)
  * turn off the other nodes
  * turn off (put in airline mode) all phones
* and then
  * setup and start a core-network on one node,
  * setup and start an radio-access-network (e-nodeB) on one node,
  * start the phone, and pop up the 'speedtest' app
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

### git repos
You will need to clone 2 repos from the `fit-r2lab` github organization, that are named
* `r2lab-embedded`
* `r2lab-demos`

Because the demo script uses code in the embedded area, it is recommended to have **these 2 clones being siblings** on your filesystem.

### python3 libraries
The following python3 libraries are required:

    pip3 install apssh asynciojobs r2lab

Also note that depending on your system, you might need to invoke `pip3` through `sudo`.
Also remember to update them as needed without

    pip3 install --upgrade apssh asynciojobs r2lab

### run the script

**Get a reservation** at the R2lab website; then you can

* go to your `r2lab-demos` repo
* `cd openair`
* `git pull`

From there:
* **to specify your slicename** run the script with
    - `./mosaic-demo.py -s inria_myslice`
* run **with image loading**
    - `./mosaic-demo.py -s inria_myslice`--load`
* or just **restart** it all
    - `./mosaic-demo.py -s inria_myslice`
* **get help** to see list of available options (like: select other nodes)
    - `./mosaic-demo.py --help`

## Manually

Here's a list of commands that you can run from faraday to accomplish parts of the script manually:

### Prepare the CN box

```
n 7
rload -i mosaic-cn
rwait
s1
configure
```

#### Prepare the RAN box

```
n 23
rload -i mosaic-ran
rwait
s1
configure 7
```

this the place where you tell your RAN where to find the CN


### Manage

Following commands are available on both boxes:

* `start`
  * optionnally on the RAN box, you can do `start -x` to start
    with a UI (requires an X11-enabled ssh session)

* `stop`
* `status`
* `journal`
  * **NOTE** that this is a wrapping call to `journalctl`,
   so you can for example use `journal -f` to observe logs as they show up.

### Data collection

Once the script has been able to provision and start everything on both the core
network (cn) and the radio acces network (ran), it will prompt you for a name
where to store data from that experiment.

    Experiment READY at 11:29:30
    type capture name when ready :

If you type 'Control-C' or `Enter`, the script will terminate. Otherwise if you
do provide a name, it will be used to store various pieces from the nodes
involved, like .e.g:

    type capture name when ready : tata
    Creating directory tata
    11-30-41:fit23:Gathering journal (current boot) about radio access network into tata-ran.log
    11-30-41:fit07:Gathering journal (current boot) about core network into tata-cn.log
    Collected data stored locally in:
    tata/cn.log tata/ran.log tata/data-network.pcap


****
****
****

**OBSOLETE SECTION**

***From this point on, the information below is obsolete and needs more work***


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


# mosaic vs oai

This demo is essentially a refactoring of the OAI demo, that takes advantage of
the new software distribution paradigm known as mosaic5g.

As compared with the original demo:

* the core is still not quite working yet (RAN won't start)
* captures remain to be redeon entirely
* scrambling should be the same, but needs tested
* we use the `r2lab` python library - notably for preparing the testbed (load images, etc..)

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
