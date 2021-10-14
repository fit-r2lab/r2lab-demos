# How to use the latest oaici docker images

Author: Raphael Defosseux <raphael.defosseux@openairinterface.org>


The two oaici docker images are:

1. **oai-ci-cd-u18-epc-latest** for the EPC
2. **oai-ci-u18-lowlatency-enb-ue-docker-latest** for the eNB


You have the choice to either deploy them automatically, through the  **deploy.py** nepi-ng script or to launch them manually, step-by-step:

1. If you choose to deploy them automatically, just run on your local machine: (replace slicename with your slice name)

 ``oaici-docker $ deploy.py -s slicename``

 We assume that you have installed nepi-ng on your host before, see [nepi-ng tuto](https://r2lab.inria.fr/tuto-030-nepi-ng-install.md) and that you booked a R2lab timeslot with your slice, see [R2lab reservation](https://r2lab.inria.fr/tuto-010-registration.md).

 The above script takes about 8mn to complete. It has several options, use ``deploy.py --help`` to see all of them. Once it finishes, you can directly go to Step 4 "Logs & Testing".


2. In the following you will learn how to manually launch, step-by-step, the latest oaici docker images on two R2lab nodes. In this example,  **fit17** is used for the EPC and **fit23** for the eNB.

___

**TABLE OF CONTENT**

1. What you need...
2. EPC terminal
   1. Load the EPC image
   2. Do some network manipulations for containers to talk to each other
   3. Deploy the EPC
3. eNB terminal
   1. Load the eNB image
   2. Do some network manipulations for containers to talk to each other
   3. Deploy the eNB
4. Logs & Testing 
   1. On the MACPHONE2 terminal
   2. MME log 
   3. eNB log
   4. Test traffic
5. Properly disconnect

## What you need...

You will need 3 terminals:

* one for the EPC
* one for the eNB
* one for the MACPHONE2

You can have more if you deploy also a UE, another eNB...

In the following, please replace your_slicename with your slice name :-)
___

# EPC terminal

## Load the EPC image

```bash
ssh your_slicename@faraday.inria.fr
$ rload -i oai-ci-cd-u18-epc-latest 17
Found binary frisbeed as /usr/sbin/frisbeed
Found binary nc as /usr/bin/nc
10:29:25 - +000s: Selection: fit17
10:29:25 - +000s: Loading image saving__fit17__2021-02-11@15-13__oai-ci-cd-u18-epc-docker-2021-02-11.ndz
10:29:25 - +000s: AUTH: checking for a valid lease
10:29:25 - +000s: AUTH: access granted
....
10:32:08 - +163s: stopped <frisbeed@234.5.6.1:10001 on saving__fit17__2021-02-11@15-13__oai-ci-cd-u18-epc-docker-2021-02-11.ndz at 500 Mibps>
$ rwait 17
<Node fit17>:ssh OK
```

## Do some network manipulations for containers to talk to each other

```bash
ssh your_slicename@faraday.inria.fr
$ ssh oaici@fit17              # password is `linux`
oaici@fit17$ sudo sysctl net.ipv4.conf.all.forwarding=1
net.ipv4.conf.all.forwarding = 1
oaici@fit17$ sudo iptables -P FORWARD ACCEPT
oaici@fit17$ sudo ip route add 192.168.61.0/26 via 192.168.3.23 dev control
```

## Deploy the EPC

**CAUTION: This SHALL be done in 2 steps!**

```bash
ssh your_slicename@faraday.inria.fr
$ ssh oaici@fit17
oaici@fit17$ cd openair-epc-fed/docker-compose/inria-oai-mme/
oaici@fit17$ docker-compose config --service
cassandra
db_init
oai_hss
oai_mme
oai_spgwc
oai_spgwu
trf_gen
oaici@fit17$ docker-compose up -d db_init
Creating network "prod-oai-private-net" with the default driver
Creating network "prod-oai-public-net" with the default driver
Creating prod-cassandra ... done
Creating prod-db-init   ... done
```

Wait a bit (around 30-50 seconds)

```bash
oaici@fit17$ docker logs prod-db-init
Connection error: ('Unable to connect to any servers', {'prod-cassandra': error(111, "Tried connecting to [('192.168.68.2', 9042)]. Last error: Connection refused")})
OK
```

You can remove the prod-db-init container. It's useless (this step is optional)

```bash
oaici@fit17:~/openair-epc-fed/docker-compose/inria-oai-mme$ docker rm prod-db-init
prod-db-init
```

**CAUTION: if you do NOT have the "OK" message as above, no need to go further**

```bash
oaici@fit17$ docker-compose up -d oai_spgwu trf_gen
Building with native build. Learn about native build in Compose here: https://docs.docker.com/go/compose-native-build/
prod-cassandra is up-to-date
Creating prod-trf-gen ... done
Creating prod-oai-hss ... done
Creating prod-oai-mme ... done
Creating prod-oai-spgwc ... done
Creating prod-oai-spgwu-tiny ... done
```

After a while (again 20-30 seconds), the EPC shall be ready

```bash
oaici@fit17:~/openair-epc-fed/docker-compose/inria-oai-mme$ docker-compose ps -a
       Name                      Command                  State                            Ports                      
----------------------------------------------------------------------------------------------------------------------
prod-cassandra        docker-entrypoint.sh cassa ...   Up (healthy)   7000/tcp, 7001/tcp, 7199/tcp, 9042/tcp, 9160/tcp
prod-oai-hss          /openair-hss/bin/entrypoin ...   Up (healthy)   5868/tcp, 9042/tcp, 9080/tcp, 9081/tcp          
prod-oai-mme          /openair-mme/bin/entrypoin ...   Up (healthy)   2123/udp, 3870/tcp, 5870/tcp                    
prod-oai-spgwc        /openair-spgwc/bin/entrypo ...   Up (healthy)   2123/udp, 8805/udp                              
prod-oai-spgwu-tiny   /openair-spgwu-tiny/bin/en ...   Up (healthy)   2152/udp, 8805/udp                              
prod-trf-gen          /bin/bash -c ip route add  ...   Up (healthy)                                                   
```

Then you can follow live the action on MME:

```bash
oaici@fit17$ docker logs prod-oai-mme --follow
....
```
___
# eNB terminal

## Load the eNB image

```bash
ssh your_slicename@faraday.inria.fr
$ rload -i oai-ci-u18-lowlatency-enb-ue-docker-latest 23
Found binary frisbeed as /usr/sbin/frisbeed
Found binary nc as /usr/bin/nc
10:29:48 - +000s: Selection: fit23
10:29:48 - +000s: Loading image saving__fit23__2021-02-11@15-17__docker-oai-u18-lowlatency-enb-ue.ndz
10:29:48 - +000s: AUTH: checking for a valid lease
10:29:48 - +000s: AUTH: access granted
...
10:33:02 - +193s: fit23 reboot = Sending message 'reset' to CMC reboot23
10:33:04 - +195s: stopped <frisbeed@234.5.6.2:10002 on saving__fit23__2021-02-11@15-17__docker-oai-u18-lowlatency-enb-ue.ndz at 500 Mibps>
$ $ rwait 23
<Node fit23>:ssh OK
$ uon 23
reboot23:ok
$ uon 23
reboot23:ok
```

## Do some network manipulations for containers to talk to each other

```bash
ssh inria_oaici@faraday.inria.fr
$ ssh oaici@fit23   # once again password is `linux`
oaici@fit23$ sudo sysctl net.ipv4.conf.all.forwarding=1
oaici@fit23$ sudo iptables -P FORWARD ACCEPT
oaici@fit23$ sudo ip route add 192.168.61.192/26 via 192.168.3.17 dev control
```

## Deploy the eNB

```bash
ssh your_slicename@faraday.inria.fr
$ ssh oaici@fit23
oaici@fit23$ cd ~/openairinterface5g/ci-scripts/yaml_files/inria_enb_mono_fdd
$ docker-compose config --service
enb_mono_fdd
oaici@fit23$ docker-compose up -d enb_mono_fdd
Creating network "prod-oai-public-net" with the default driver
Creating prod-enb-mono-fdd ... done
oaici@fit23$ docker logs prod-enb-mono-fdd --follow
[INFO] Images destination: /usr/share/uhd/images
[INFO] No inventory file found at /usr/share/uhd/images/inventory.json. Creating an empty one.
[INFO] Downloading b2xx_b200_fpga_default-gfde2a94e.zip, total size: 478.32 kB
[INFO] Downloading b2xx_b200mini_fpga_default-gfde2a94e.zip, total size: 463.516 kB
[INFO] Downloading b2xx_b210_fpga_default-gfde2a94e.zip, total size: 878.644 kB
[INFO] Downloading b2xx_b205mini_fpga_default-gfde2a94e.zip, total size: 522.303 kB
[INFO] Downloading b2xx_common_fw_default-g2bdad498.zip, total size: 161.492 kB
[INFO] Images download complete.
==================================
== Starting eNB soft modem
Additional option(s): --RUs.[0].max_rxgain 115 --RUs.[0].max_pdschReferenceSignalPower -27 --eNBs.[0].component_carriers.[0].pucch_p0_Nominal -96
/opt/oai-enb/bin/lte-softmodem.Rel15 -O /opt/oai-enb/etc/enb.conf --RUs.[0].max_rxgain 115 --RUs.[0].max_pdschReferenceSignalPower -27 --eNBs.[0].component_carriers.[0].pucch_p0_Nominal -96
[LOADER] library libNB_IoT.so is not loaded: libNB_IoT.so: cannot open shared object file: No such file or directory
[CONFIG] get parameters from libconfig /opt/oai-enb/etc/enb.conf , debug flags: 0x00000000
[CONFIG] function config_libconfig_init returned 0
[CONFIG] config module libconfig loaded
[LIBCONFIG] config: 1/1 parameters successfully set, (1 to default value)
# /dev/cpu_dma_latency set to 0us
....
[SCTP]   sctp_bindx SCTP_BINDX_ADD_ADDR socket bound to : 192.168.61.30
[SCTP]   Converted ipv4 address 192.168.61.195 to network type
[SCTP]   connectx assoc_id  1 in progress..., used 1 addresses
[SCTP]   Inserted new descriptor for sd 95 in list, nb elements 1, assoc_id 1
[SCTP]   Found data for descriptor 95
[SCTP]   Received notification for sd 95, type 32769
[SCTP]   Client association changed: 0
[SCTP]   ----------------------
[SCTP]   Peer addresses:
[SCTP]       - [192.168.61.195]
[SCTP]   ----------------------
[SCTP]   ----------------------
[SCTP]   SCTP Status:
[SCTP]   assoc id .....: 1
[SCTP]   state ........: 4
[SCTP]   instrms ......: 2
[SCTP]   outstrms .....: 2
[SCTP]   fragmentation : 1452
[SCTP]   pending data .: 0
[SCTP]   unack data ...: 0
[SCTP]   rwnd .........: 106496
[SCTP]   peer info     :
[SCTP]       state ....: 2
[SCTP]       cwnd .....: 4380
[SCTP]       srtt .....: 0
[SCTP]       rto ......: 3000
[SCTP]       mtu ......: 1500
[SCTP]   ----------------------
[SCTP]   Comm up notified for sd 95, assigned assoc_id 1
[S1AP]   3584 -> 00e000
[SCTP]   Successfully sent 54 bytes on stream 0 for assoc_id 1
[SCTP]   Found data for descriptor 95
[SCTP]   [1][95] Msg of length 27 received from port 36412, on stream 0, PPID 18
[S1AP]   servedGUMMEIs.list.count 1
[S1AP]   servedPLMNs.list.count 1
[S1AP]   S1AP_FIND_PROTOCOLIE_BY_ID: /oai-ran/openair3/S1AP/s1ap_eNB_handlers.c 380: ie is NULL
[ENB_APP]   [eNB 0] Received S1AP_REGISTER_ENB_CNF: associated MME 1
```

At that point, the eNB SHOULD be connected with the MME:

```
oaici@fit17$ docker logs prod-oai-mme --follow
000382 00110:853675 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0039    ======================================= STATISTICS ============================================

000383 00110:853696 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0042                   |   Current Status| Added since last display|  Removed since last display |
000384 00110:853703 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0048    Connected eNBs |          0      |              0              |             0               |
000385 00110:853710 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0054    Attached UEs   |          0      |              0              |             0               |
000386 00110:853715 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0060    Connected UEs  |          0      |              0              |             0               |
000387 00110:853721 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0066    Default Bearers|          0      |              0              |             0               |
000388 00110:853728 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0072    S1-U Bearers   |          0      |              0              |             0               |

000389 00110:853734 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0075    ======================================= STATISTICS ============================================

000390 00112:416004 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0469    Client association changed: 0
000391 00112:416027 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0101    ----------------------
000392 00112:416032 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0102    SCTP Status:
000393 00112:416035 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0103    assoc id .....: 1
000394 00112:416038 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0104    state ........: 4
000395 00112:416041 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0105    instrms ......: 2
000396 00112:416044 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0106    outstrms .....: 2
000397 00112:416047 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0108    fragmentation : 1452
000398 00112:416050 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0109    pending data .: 0
000399 00112:416053 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0110    unack data ...: 0
000400 00112:416056 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0111    rwnd .........: 106496
000401 00112:416059 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0112    peer info     :
000402 00112:416061 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0114        state ....: 2
000403 00112:416064 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0116        cwnd .....: 4380
000404 00112:416067 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0118        srtt .....: 0
000405 00112:416070 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0120        rto ......: 3000
000406 00112:416073 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0122        mtu ......: 1500
000407 00112:416076 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0123    ----------------------
000408 00112:416079 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0479    New connection
000409 00112:416093 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0205    ----------------------
000410 00112:416104 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0206    Local addresses:
000411 00112:416110 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0217        - [192.168.61.195]
000412 00112:416113 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0234    ----------------------
000413 00112:416119 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0151    ----------------------
000414 00112:416122 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0152    Peer addresses:
000415 00112:416126 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0163        - [192.168.3.23]
000416 00112:416128 7F81A17FA700 DEBUG SCTP   enair-mme/src/sctp/sctp_common.c:0178    ----------------------
000417 00112:416141 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0554    SCTP RETURNING!!
000418 00112:416196 7F81F9FFB700 DEBUG S1AP   mme/src/s1ap/s1ap_mme_handlers.c:2826    Create eNB context for assoc_id: 1
000419 00112:417350 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0547    [1][48] Msg of length 54 received from port 36412, on stream 0, PPID 18
000420 00112:417383 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0554    SCTP RETURNING!!
000422 00112:420248 7F81F9FFB700 DEBUG S1AP   mme/src/s1ap/s1ap_mme_handlers.c:0361    S1-Setup-Request macroENB_ID.size 3 (should be 20)
000421 00112:420243 7F81F9FFB700 DEBUG S1AP   mme/src/s1ap/s1ap_mme_handlers.c:0321    New s1 setup request incoming from macro eNB id: 00e00
000423 00112:420263 7F81F9FFB700 DEBUG S1AP   mme/src/s1ap/s1ap_mme_handlers.c:0423    Adding eNB to the list of served eNBs
000424 00112:420266 7F81F9FFB700 DEBUG S1AP   mme/src/s1ap/s1ap_mme_handlers.c:0438    Adding eNB id 3584 to the list of served eNBs
000425 00112:420776 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0283    [48][1] Sending buffer 0x7f8164009f90 of 27 bytes on stream 0 with ppid 18
000426 00112:420815 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0296    Successfully sent 27 bytes on stream 0
000427 00120:853608 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0039    ======================================= STATISTICS ============================================

000428 00120:853628 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0042                   |   Current Status| Added since last display|  Removed since last display |
000429 00120:853633 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0048    Connected eNBs |          1      |              1              |             0               |
000430 00120:853638 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0054    Attached UEs   |          0      |              0              |             0               |
000431 00120:853643 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0060    Connected UEs  |          0      |              0              |             0               |
000432 00120:853647 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0066    Default Bearers|          0      |              0              |             0               |
000433 00120:853652 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0072    S1-U Bearers   |          0      |              0              |             0               |

000434 00120:853656 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0075    ======================================= STATISTICS ============================================
```

Let the eNB radio start:

```bash
oaici@fit23$ docker logs prod-enb-mono-fdd --follow
...
[LIBCONFIG] MMEs.[0]: 1/1 parameters successfully set, (1 to default value)
[MCE_APP]   Creating MCE_APP eNB Task
[TMR]   Created Posix thread TASK_MCE_APP
[LIBCONFIG] MCEs.[0]: 1/1 parameters successfully set, (1 to default value)
[LIBCONFIG] MCEs.[0]: 1/1 parameters successfully set, (1 to default value)
[ENB_APP]   TYPE <CTRL-C> TO TERMINATE
[ENB_APP]   [MCE 0] MCE_app_register via M3AP for instance 0
[PHY]   RU 0 rf device ready
sleep...
sleep...
sleep...
sleep...
sleep...
sleep...
sleep...
sleep...
sleep...
[RLC]   rlc_tick: discontinuity (expected 0.1, got 0.4)
[MAC]   SCHED_MODE = 0
[PHY]   prach_I0 = 0.1 dB
[PHY]   max_I0 30 (rb 2), min_I0 27 (rb 0), avg I0 27
[PHY]   prach_I0 = 0.1 dB
[PHY]   max_I0 30 (rb 2), min_I0 24 (rb 19), avg I0 27
[PHY]   prach_I0 = 0.1 dB
[PHY]   max_I0 30 (rb 2), min_I0 24 (rb 6), avg I0 27
[PHY]   prach_I0 = 0.1 dB
[PHY]   max_I0 30 (rb 2), min_I0 24 (rb 19), avg I0 27
[PHY]   prach_I0 = 0.1 dB
[PHY]   max_I0 31 (rb 2), min_I0 24 (rb 4), avg I0 27
[PHY]   prach_I0 = 0.1 dB
[PHY]   max_I0 30 (rb 2), min_I0 24 (rb 1), avg I0 27
[PHY]   prach_I0 = 0.1 dB
[PHY]   max_I0 30 (rb 2), min_I0 24 (rb 4), avg I0 27
```
___
# Logs & Testing

## On the MACPHONE2 terminal


```bash
ssh inria_oaici@faraday.inria.fr
$  macphone2
macphone2:~ tester$ phone-status 
phone is turned OFF
macphone2:~ tester$ phone-on 
Turning ON phone : turning off airplane mode
Broadcasting: Intent { act=android.intent.action.AIRPLANE_MODE (has extras) }
Broadcast completed: result=0
```

the UE shall connect quickly:

## MME logs

```bash
000491 00199:803592 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0547    [1][48] Msg of length 152 received from port 36412, on stream 1, PPID 18
000492 00199:803678 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0554    SCTP RETURNING!!
000493 00199:803783 7F81F9FFB700 INFO  S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0093    Received S1AP INITIAL_UE_MESSAGE eNB_UE_S1AP_ID 06692d
000494 00199:803831 7F81F9FFB700 INFO  S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0112    New Initial UE message received with eNB UE S1AP ID: 06692d
000495 00199:803843 7F81F9FFB700 DEBUG S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0116    S1AP_FIND_PROTOCOLIE_BY_ID: /openair-mme/src/s1ap/s1ap_mme_nas_procedures.c 116: Optional ie is NULL
000496 00199:804042 7F81F9FFB700 DEBUG S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0194    S1AP_FIND_PROTOCOLIE_BY_ID: /openair-mme/src/s1ap/s1ap_mme_nas_procedures.c 194: Optional ie is NULL
000497 00199:804058 7F81F9FFB700 DEBUG S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0203    S1AP_FIND_PROTOCOLIE_BY_ID: /openair-mme/src/s1ap/s1ap_mme_nas_procedures.c 203: Optional ie is NULL
000498 00199:804069 7F81F9FFB700 DEBUG S1AP   c/s1ap/s1ap_mme_itti_messaging.c:0132    S1AP:Initial UE Message- Size 93: 
000499 00199:804127 7F81F9704700 TRACE MME-AP mme/src/mme_app/mme_app_bearer.c:0508    Entering mme_app_handle_initial_ue_message()
000500 00199:804157 7F81F9704700 DEBUG MME-AP mme/src/mme_app/mme_app_bearer.c:0515    Received MME_APP_INITIAL_UE_MESSAGE from S1AP
000501 00199:804171 7F81F9704700 DEBUG MME-AP mme/src/mme_app/mme_app_bearer.c:0771    MME_APP_INITIAL_UE_MESSAGE from S1AP,without S-TMSI. 
000502 00199:804183 7F81F9704700 DEBUG MME-AP mme/src/mme_app/mme_app_bearer.c:0789    UE context doesn't exist -> create one 
000503 00199:809811 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0136    Entering get_new_ue_context()
000504 00199:809827 7F81F9704700 INFO  MME-AP me/src/mme_app/mme_app_context.c:0162    Clearing received current ue_context 0x5570b59e3858.
000505 00199:809830 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:4034    Entering clear_ue_context()
000506 00199:809833 7F81F9704700 INFO  MME-AP me/src/mme_app/mme_app_context.c:4114    Clearing UE context of UE ffffffff. 
000507 00199:809835 7F81F9704700 INFO  MME-AP me/src/mme_app/mme_app_context.c:4126    Successfully cleared UE context for UE ffffffff. 
000508 00199:809837 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:4127    Leaving clear_ue_context()
000509 00199:809839 7F81F9704700 DEBUG MME-AP me/src/mme_app/mme_app_context.c:0175    MME_APP_INITIAL_UE_MESSAGE. Allocated new MME UE context and new mme_ue_s1ap_id 1. 
000510 00199:809841 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0650    Entering mme_insert_ue_context()
000511 00199:809844 7F81F9704700 DEBUG MME-AP me/src/mme_app/mme_app_context.c:0677    The received enb_ue_s1ap_id_key is invalid b59e3858. Skipping. 
000512 00199:809848 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0800    Leaving mme_insert_ue_context() (rc=0)
000513 00199:809850 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0179    Leaving get_new_ue_context() (rc=93942571743320)
000514 00199:809852 7F81F9704700 DEBUG MME-AP mme/src/mme_app/mme_app_bearer.c:0811    Created new MME UE context enb_ue_s1ap_id 06692d
000515 00199:809855 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2153    Entering mme_ue_context_update_ue_sig_connection_state()
000516 00199:809857 7F81F9704700 DEBUG MME-AP me/src/mme_app/mme_app_context.c:2209    MME_APP: UE Connection State changed to CONNECTED.enb_ue_s1ap_id = 420141, mme_ue_s1ap_id = 1
000517 00199:809860 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0325    Entering mme_ue_context_update_coll_keys()
000518 00199:809862 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0334    Update ue context.enb_ue_s1ap_id 06692d ue context.mme_ue_s1ap_id 1 ue context.IMSI 0 ue context.GUTI 000.000|0000|00|00000000
000519 00199:809864 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0342    Update ue context 0x5570b59e3858 enb_ue_s1ap_id 06692d mme_ue_s1ap_id 1 IMSI 0 GUTI 000.000|0000|00|00000000
000520 00199:809868 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0605    Leaving mme_ue_context_update_coll_keys()
000521 00199:809870 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0267    Entering get_new_session_pool()
000522 00199:809873 7F81F9704700 INFO  MME-AP me_app/mme_app_session_context.c:0288    Clearing received current sp 0x5570b5af3868.
000523 00199:809875 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0850    Entering clear_session_pool()
000524 00199:809877 7F81F9704700 INFO  MME-AP me_app/mme_app_session_context.c:0856    Clearing UE session pool of UE ffffffff. 
000525 00199:809879 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0899    Clearing bearer context with ebi 5 (0x5570b5af3894) for UE ffffffff. 
000526 00199:809882 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0899    Clearing bearer context with ebi 6 (0x5570b5af393b) for UE ffffffff. 
000527 00199:809884 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0899    Clearing bearer context with ebi 7 (0x5570b5af39e2) for UE ffffffff. 
000528 00199:809886 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0899    Clearing bearer context with ebi 8 (0x5570b5af3a89) for UE ffffffff. 
000529 00199:809888 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0899    Clearing bearer context with ebi 9 (0x5570b5af3b30) for UE ffffffff. 
000530 00199:809890 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0899    Clearing bearer context with ebi 10 (0x5570b5af3bd7) for UE ffffffff. 
000531 00199:809892 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0899    Clearing bearer context with ebi 11 (0x5570b5af3c7e) for UE ffffffff. 
000532 00199:809894 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0899    Clearing bearer context with ebi 12 (0x5570b5af3d25) for UE ffffffff. 
000533 00199:809896 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0899    Clearing bearer context with ebi 13 (0x5570b5af3dcc) for UE ffffffff. 
000534 00199:809898 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0899    Clearing bearer context with ebi 14 (0x5570b5af3e73) for UE ffffffff. 
000535 00199:809899 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0899    Clearing bearer context with ebi 15 (0x5570b5af3f1a) for UE ffffffff. 
000536 00199:809901 7F81F9704700 INFO  MME-AP me_app/mme_app_session_context.c:0924    Successfully cleared UE session pool of UE ffffffff. 
000537 00199:809903 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0925    Leaving clear_session_pool()
000538 00199:809905 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0157    Entering mme_insert_ue_session_pool()
000539 00199:809908 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0212    Leaving mme_insert_ue_session_pool() (rc=0)
000540 00199:809910 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0297    Leaving get_new_session_pool() (rc=93942572857448)
000541 00199:809912 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0071    Entering mme_ue_session_pool_update_coll_keys()
000542 00199:809914 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0077    Update ue_session_pool.mme_ue_s1ap_id 1 teid 0x0. 
000543 00199:809916 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0131    Leaving mme_ue_session_pool_update_coll_keys()
000544 00199:809919 7F81F9704700 TRACE MME-AP mme_app/mme_app_itti_messaging.c:0976    Entering notify_s1ap_new_ue_mme_s1ap_id_association()
000545 00199:809930 7F81F9704700 DEBUG MME-AP mme_app/mme_app_itti_messaging.c:0990     Sent MME_APP_S1AP_MME_UE_ID_NOTIFICATION to S1AP for UE Id 1 and enbUeS1apId 420141
000546 00199:809933 7F81F9704700 TRACE MME-AP mme_app/mme_app_itti_messaging.c:0991    Leaving notify_s1ap_new_ue_mme_s1ap_id_association()
000547 00199:809943 7F81F9704700 TRACE MME-AP mme/src/mme_app/mme_app_bearer.c:0899    Leaving mme_app_handle_initial_ue_message()
000548 00199:809947 7F81F9FFB700 DEBUG S1AP   /openair-mme/src/s1ap/s1ap_mme.c:0718    Associated  sctp_assoc_id 1, enb_ue_s1ap_id 06692d, mme_ue_s1ap_id 1:HASH_TABLE_OK 
000549 00199:809984 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0094    Entering nas_proc_establish_ind()
000550 00199:809994 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
000551 00199:810462 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
000552 00199:810470 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_ESTABLISH_REQ (205)
000553 00199:810474 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0697    Entering _emm_as_establish_req()
000554 00199:810477 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0706    EMMAS-SAP - Received AS connection establish request. 
000555 00199:810481 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context (nil)
000556 00199:810487 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0360    Entering nas_message_decode()
000557 00199:810489 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0374    hex stream Incoming NAS message:  17 38 4d 7d 73 02 07 41 02 0b f6 02 f8 59 00 04 01 00 00 00 03 05 f0 70 c0 40 10 00 27 02 2d d0 11 d1 27 20 80 80 21 10 01 00 00 10 81 06 00 00 00 00 83 06 00 00 00 00 00 0d 00 00 0a 00 00 05 00 00 10 00 52 02 f8 59 00 01 5c 0a 00 31 03 e5 e0 34 90 11 03 57 58 a6 5d 01 00 e0 c1
000558 00199:810524 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0694    Entering nas_message_header_decode()
000559 00199:810528 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0751    Leaving nas_message_header_decode() (rc=6)
000560 00199:810532 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0383    Header seq no of uplink message 2: 
000561 00199:810535 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0386    nas_message_header_decode returned size 6
000562 00199:810539 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0827    Entering _nas_message_protected_decode()
000563 00199:810542 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1049    Entering _nas_message_decrypt()
000564 00199:810550 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1066    No decryption of message length 87 according to security header type 0x01
000565 00199:810554 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1069    Leaving _nas_message_decrypt() (rc=7)
000566 00199:810557 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0776    Entering _nas_message_plain_decode()
000567 00199:810561 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0101    Entering emm_msg_decode()
000568 00199:810564 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0121    EMM-MSG   - Message Type 0x41
000569 00199:810568 7F820083C700 TRACE NAS-EM /src/nas/emm/msg/AttachRequest.c:0036    Entering decode_attach_request()
000570 00199:810576 7F820083C700 TRACE NAS-EM /src/nas/ies/EpsMobileIdentity.c:0124    Entering decode_guti_eps_mobile_identity()
000571 00199:810587 7F820083C700 TRACE NAS-EM /src/nas/ies/EpsMobileIdentity.c:0162    Leaving decode_guti_eps_mobile_identity() (rc=11)
000572 00199:810591 7F820083C700 TRACE NAS-EM rc/nas/ies/UeNetworkCapability.c:0044    decode_ue_network_capability len = 5
000573 00199:810594 7F820083C700 TRACE NAS-EM rc/nas/ies/UeNetworkCapability.c:0063    uenetworkcapability decoded UMTS
000574 00199:810597 7F820083C700 TRACE NAS-EM rc/nas/ies/UeNetworkCapability.c:0074    uenetworkcapability decoded misc flags
000575 00199:810600 7F820083C700 TRACE NAS-EM rc/nas/ies/UeNetworkCapability.c:0079    uenetworkcapability decoded=6
000576 00199:810606 7F820083C700 TRACE NAS-EM rc/nas/ies/UeNetworkCapability.c:0083    uenetworkcapability then decoded=6
000577 00199:810610 7F820083C700 TRACE NAS-ES rc/nas/ies/EsmMessageContainer.c:0037    Entering decode_esm_message_container()
000578 00199:810614 7F820083C700 TRACE NAS-ES rc/nas/ies/EsmMessageContainer.c:0054    Leaving decode_esm_message_container() (rc=41)
000579 00199:810619 7F820083C700 TRACE NAS-EM src/common/3gpp_24.008_gmm_ies.c:0277    decode_ms_network_capability_ie len = 3
000580 00199:810629 7F820083C700 TRACE NAS-EM /src/nas/emm/msg/AttachRequest.c:0328    Leaving decode_attach_request() (rc=85)
000581 00199:810633 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0274    Leaving emm_msg_decode() (rc=87)
000582 00199:810636 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0799    Leaving _nas_message_plain_decode() (rc=87)
000583 00199:810639 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0846    Leaving _nas_message_protected_decode() (rc=87)
000584 00199:810642 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0537    Leaving nas_message_decode() (rc=93)
000585 00199:810716 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:0148    Entering emm_recv_attach_request()
000586 00199:810723 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:0151    EMMAS-SAP - Received Attach Request message
000587 00199:810727 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:0199    Entering emm_proc_attach_request()
000588 00199:810730 7F820083C700 INFO  NAS-EM openair-mme/src/nas/emm/Attach.c:0217    EMM-PROC  ATTACH - EPS attach type = IMSI (1) requested (ue_id=1)
000589 00199:810734 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context (nil)
000590 00199:810738 7F820083C700 WARNI NAS-EM openair-mme/src/nas/emm/Attach.c:0336    EMM-PROC  - No old EMM context exists. Continuing with new EMM context for 1. 
000591 00199:810741 7F820083C700 INFO  NAS-EM openair-mme/src/nas/emm/Attach.c:0344    EMM-PROC  - Continuing for Attach Request for UE_ID 1 after validation of the attach request. 
000592 00199:810744 7F820083C700 INFO  NAS-EM openair-mme/src/nas/emm/Attach.c:0350    EMM-PROC  - No old EMM context was found for UE_ID 1. 
000593 00199:810747 7F820083C700 NOTIC NAS-EM openair-mme/src/nas/emm/Attach.c:0379    EMM-PROC  - Create EMM context ue_id = 1
000594 00199:810751 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1067    UE 1 Init EMM-CTX
000595 00199:810754 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0109    ue_id=1 GUTI cleared
000596 00199:810757 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0137    ue_id=1 old GUTI cleared
000597 00199:810760 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0168    ue_id=1 cleared IMSI
000598 00199:810763 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0210    ue_id=1 IMEI cleared
000599 00199:810766 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0246    ue_id=1 cleared IMEI_SV 
000600 00199:810769 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0277    ue_id=1 cleared last visited registered TAI
000601 00199:810773 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0368    ue_id=1 set security context security type 0
000602 00199:810781 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0377    ue_id=1 set security context eksi 7
000603 00199:810784 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0358    ue_id=1 cleared security context 
000604 00199:810787 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0415    ue_id=1 cleared non current security context 
000605 00199:810790 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0387    ue_id=1 clear security context vector index
000606 00199:810793 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0317    ue_id=1 cleared auth vectors 
000607 00199:810796 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0465    ue_id=1 cleared MS network capability IE
000608 00199:810799 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0428    ue_id=1 cleared UE network capability IE
000609 00199:810802 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0499    ue_id=1 cleared current DRX parameter
000610 00199:810805 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0377    ue_id=1 set security context eksi 0
000611 00199:810809 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1979    EMM-CTX - Add in context 0x7f81680011b0 UE id 1
000612 00199:810813 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0790    New EMM_SPEC_PROC_TYPE_ATTACH
000613 00199:810817 7F820083C700 DEBUG NAS-EM openair-mme/src/nas/emm/Attach.c:1217     CREATED NEW ATTACH PROC 0x7f8168001a90. 
 000614 00199:810820 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1455    Entering _emm_attach_run_procedure()
000615 00199:810823 7F820083C700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:1461    Hit 3GPP TS 24_301R10_5_5_1_2_3__1 : EMM common procedure initiation during attach procedure
000616 00199:810827 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0440    ue_id=1 set UE network capability IE (present)
000617 00199:810830 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0477    ue_id=1 set MS network capability IE (present)
000618 00199:810832 7F820083C700 INFO  NAS-EM openair-mme/src/nas/emm/Attach.c:1522    EMM-PROC  - Received an GUTI 208.95 |0004|01|00000003 in the attach request IE for ue_id=1. Continuing with identification procedure. 
000619 00199:810841 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Identification.c:0132    Entering emm_proc_identification()
000620 00199:810845 7F820083C700 NOTIC NAS    mme/src/nas/emm/Identification.c:0138    Hit 3GPP TS 24_301R10_5_4_4_1 : Identification procedure
000621 00199:810847 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Identification.c:0144    EMM-PROC  - Initiate identification type = IMSI (1), ctx = 0x7f81680011b0
000622 00199:810851 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0912    New EMM_COMM_PROC_IDENT
000623 00199:810855 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Identification.c:0573    Entering _identification_request()
000624 00199:810858 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000625 00199:810862 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0670    Entering emm_as_set_security_data()
000626 00199:810865 7F820083C700 DEBUG NAS-EM air-mme/src/nas/emm/LowerLayer.c:0727    NO Valid Security Context Available
000627 00199:810868 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0734    Leaving emm_as_set_security_data()
000628 00199:810871 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
000629 00199:810874 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
000630 00199:810879 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_SECURITY_REQ (201)
000631 00199:810882 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1095    Entering _emm_as_send()
000632 00199:810887 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1599    Entering _emm_as_security_req()
000633 00199:810890 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1602    EMMAS-SAP - Send AS security request
000634 00199:810893 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0903    Entering _emm_as_set_header()
000635 00199:810897 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0959    Leaving _emm_as_set_header() (rc=140196331095328)
000636 00199:810900 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0942    Entering emm_send_identity_request()
000637 00199:810904 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0945    EMMAS-SAP - Send Identity Request message
000638 00199:810907 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0968    Leaving emm_send_identity_request() (rc=3)
000639 00199:810910 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000640 00199:810913 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0987    Entering _emm_as_encode()
000641 00199:810916 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0561    Entering nas_message_encode()
000642 00199:810919 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0877    Entering _nas_message_header_encode()
000643 00199:810922 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0913    Leaving _nas_message_header_encode() (rc=1)
000644 00199:810925 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0938    Entering _nas_message_plain_encode()
000645 00199:810927 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0295    Entering emm_msg_encode()
000646 00199:810929 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0465    Leaving emm_msg_encode() (rc=3)
000647 00199:810931 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0963    Leaving _nas_message_plain_encode() (rc=3)
000648 00199:810933 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0656    Leaving nas_message_encode() (rc=3)
000649 00199:810935 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1023    Leaving _emm_as_encode() (rc=3)
000650 00199:810937 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0483    Entering emm_msg_free()
000651 00199:810938 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0493    EMM-MSG   - Message Type 0x55
000652 00199:810940 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0592    Leaving emm_msg_free()
000653 00199:810942 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000654 00199:810944 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:1059    Found emm_common_proc UID 0x2
000655 00199:810946 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1704    Leaving _emm_as_security_req() (rc=263)
000656 00199:810948 7F820083C700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1229    EMMAS-SAP - Sending msg with id 0x107, primitive EMMAS_SECURITY_REQ (201) to S1AP layer for transmission
000657 00199:810955 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1236    Leaving _emm_as_send() (rc=0)
000658 00199:810958 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
000659 00199:810960 7F820083C700 NOTIC NAS    mme/src/nas/emm/Identification.c:0610    Hit 3GPP TS 24_301R10_5_4_4_2 : Identification initiation by the network
000660 00199:810960 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0051    Entering mme_app_handle_nas_dl_req()
000661 00199:810967 7F81F9704700 DEBUG MME-AP /src/mme_app/mme_app_transport.c:0064    DOWNLINK NAS TRANSPORT Found enb_ue_s1ap_id 06692d mme_ue_s1ap_id 1
000662 00199:810974 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0095     MME_APP:DOWNLINK NAS TRANSPORT. MME_UE_S1AP_ID 1 and ENB_UE_S1AP_ID 06692d. 
000663 00199:810975 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1339    T3470 started UE 1
000664 00199:810983 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0189    Leaving mme_app_handle_nas_dl_req() (rc=0)
000665 00199:810992 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Identification.c:0620    Leaving _identification_request() (rc=0)
000666 00199:810997 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
000667 00199:811000 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0104    Entering emm_reg_send()
000668 00199:811003 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0274    Entering emm_fsm_process()
000669 00199:811007 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000670 00199:811011 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0282    EMM-FSM   - Received event COMMON_PROC_REQ (1) in state EMM-DEREGISTERED
000671 00199:811015 7F820083C700 TRACE NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0097    Entering EmmDeregistered()
000672 00199:811022 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000673 00199:811025 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0176    Entering emm_fsm_set_state()
000674 00199:811028 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0185    UE 1 EMM-FSM   - Status changed: EMM-DEREGISTERED ===> EMM-COMMON-PROCEDURE-INITIATED
000675 00199:811032 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2251    Entering mme_ue_context_update_ue_emm_state()
000676 00199:811036 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2276    Leaving mme_ue_context_update_ue_emm_state()
000677 00199:811041 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0213    Leaving emm_fsm_set_state() (rc=0)
000678 00199:811045 7F820083C700 TRACE NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0424    Leaving EmmDeregistered() (rc=0)
000679 00199:811048 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0293    Leaving emm_fsm_process() (rc=0)
000680 00199:811051 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0117    Leaving emm_reg_send() (rc=0)
000682 00199:811058 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Identification.c:0195    Leaving emm_proc_identification() (rc=0)
000681 00199:811056 7F81F9FFB700 DEBUG S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0452    SEARCHING UE REFERENCE for SCTP association id 1,  enbUeS1apId 06692d and enbId 3584. 
000683 00199:811062 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1532    Leaving _emm_attach_run_procedure() (rc=0)
000684 00199:811075 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:0609    Leaving emm_proc_attach_request() (rc=0)
000685 00199:811079 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:0364    Leaving emm_recv_attach_request() (rc=0)
000686 00199:811083 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0483    Entering emm_msg_free()
000687 00199:811086 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0493    EMM-MSG   - Message Type 0x41
000688 00199:811089 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0592    Leaving emm_msg_free()
000689 00199:811092 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0865    Leaving _emm_as_establish_req() (rc=0)
000690 00199:811096 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
000691 00199:811100 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0117    Leaving nas_proc_establish_ind() (rc=0)
000692 00199:811103 7F81F9FFB700 NOTIC S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0543    Send S1AP DOWNLINK_NAS_TRANSPORT message ue_id = 1 MME_UE_S1AP_ID = 1 eNB_UE_S1AP_ID = 06692d
000693 00199:811121 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0283    [48][1] Sending buffer 0x7f816400a0e0 of 29 bytes on stream 1 with ppid 18
000694 00199:811183 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0296    Successfully sent 29 bytes on stream 1
000695 00199:831420 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0547    [1][48] Msg of length 65 received from port 36412, on stream 1, PPID 18
000696 00199:831440 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0554    SCTP RETURNING!!
000697 00199:831472 7F81F9FFB700 INFO  S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0295    Received S1AP UPLINK_NAS_TRANSPORT message MME_UE_S1AP_ID 1
000698 00199:831543 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0250    Entering nas_proc_ul_transfer_ind()
000699 00199:831550 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
000700 00199:831553 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
000701 00199:831557 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_DATA_IND (211)
000702 00199:831560 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0557    Entering _emm_as_data_ind()
000703 00199:831562 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0565    EMMAS-SAP - Received AS data transfer indication (ue_id=1, delivered=true, length=17)
000704 00199:831565 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000705 00199:831574 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0260    Entering nas_message_decrypt()
000706 00199:831576 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0694    Entering nas_message_header_decode()
000707 00199:831578 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0751    Leaving nas_message_header_decode() (rc=6)
000708 00199:831580 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1392    Entering _nas_message_get_mac()
000709 00199:831582 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1397    No security context set for integrity protection algorithm
000710 00199:831584 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1398    Leaving _nas_message_get_mac() (rc=0)
000711 00199:831586 7F820083C700 CRITI NAS    rc/nas/api/network/nas_message.c:0311    MAC Failure MSG:88FABE31(2298134065) <> INT ALGO:00000000(0) Type of security context 0
000712 00199:831591 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1049    Entering _nas_message_decrypt()
000713 00199:831593 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1066    No decryption of message length 11 according to security header type 0x01
000714 00199:831595 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1069    Leaving _nas_message_decrypt() (rc=7)
000715 00199:831597 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0335    Leaving nas_message_decrypt() (rc=11)
000716 00199:831599 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0269    Entering _emm_as_recv()
000717 00199:831601 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0285    EMMAS-SAP - Received EMM message (length=11) integrity protected 1 ciphered 0 mac matched 0 security context 0
000718 00199:831604 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000719 00199:831607 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0360    Entering nas_message_decode()
000720 00199:831611 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0374    hex stream Incoming NAS message:  07 56 08 29 80 59 00 00 00 00 40
000721 00199:831620 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0694    Entering nas_message_header_decode()
000722 00199:831624 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0751    Leaving nas_message_header_decode() (rc=1)
000723 00199:831627 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0386    nas_message_header_decode returned size 1
000724 00199:831630 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0776    Entering _nas_message_plain_decode()
000725 00199:831633 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0101    Entering emm_msg_decode()
000726 00199:831636 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0121    EMM-MSG   - Message Type 0x56
000727 00199:831639 7F820083C700 TRACE NAS-EM /common/3gpp_24.008_common_ies.c:0296    Entering decode_imsi_mobile_identity()
000728 00199:831642 7F820083C700 TRACE NAS-EM /common/3gpp_24.008_common_ies.c:0364    Leaving decode_imsi_mobile_identity() (rc=8)
000729 00199:831645 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0274    Leaving emm_msg_decode() (rc=11)
000730 00199:831648 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0799    Leaving _nas_message_plain_decode() (rc=11)
000731 00199:831650 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0539    Leaving nas_message_decode() (rc=11)
000732 00199:831652 7F820083C700 NOTIC NAS    air-mme/src/nas/emm/sap/emm_as.c:0355    Hit 3GPP TS 24_301R10_4_4_4_3__1 : Integrity checking of NAS signalling messages exception in the MME
000733 00199:831654 7F820083C700 NOTIC NAS    air-mme/src/nas/emm/sap/emm_as.c:0358    Hit 3GPP TS 24_301R10_4_4_4_3__2 : Process NAS signalling message in the MME, even if it fails the integrity check or MAC cannot be verified
000734 00199:831656 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:0893    Entering emm_recv_identity_response()
000735 00199:831658 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:0896    EMMAS-SAP - Received Identity Response message
000736 00199:831660 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Identification.c:0224    Entering emm_proc_identification_complete()
000737 00199:831663 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Identification.c:0232    EMM-PROC  - Identification complete (ue_id=1)
000738 00199:831667 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000739 00199:831670 7F820083C700 NOTIC NAS    mme/src/nas/emm/Identification.c:0241    Hit 3GPP TS 24_301R10_5_4_4_4 : Identification completion by the network
000740 00199:831677 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1446    T3470 stopped UE 1
000741 00199:831683 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0197    ue_id=1 set IMSI 208950000000004 (valid)
000742 00199:831686 7F820083C700 TRACE NAS    ir-mme/src/nas/api/mme/mme_api.c:0365    Entering mme_api_notify_imsi()
000743 00199:831690 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0325    Entering mme_ue_context_update_coll_keys()
000744 00199:831696 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0334    Update ue context.enb_ue_s1ap_id 06692d ue context.mme_ue_s1ap_id 1 ue context.IMSI 0 ue context.GUTI 000.000|0000|00|00000000
000745 00199:831700 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0342    Update ue context 0x5570b59e3858 enb_ue_s1ap_id 06692d mme_ue_s1ap_id 1 IMSI 208950000000004 GUTI 000.000|0000|00|00000000
000746 00199:831705 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0605    Leaving mme_ue_context_update_coll_keys()
000747 00199:831709 7F820083C700 DEBUG MME-AP ir-mme/src/nas/api/mme/mme_api.c:0394    MME_APP context for ue_id=1 has a registered valid IMSI 208950000000004 (valid)
000748 00199:831712 7F820083C700 TRACE NAS    ir-mme/src/nas/api/mme/mme_api.c:0395    Leaving mme_api_notify_imsi() (rc=0)
000749 00199:831717 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:2116    EMM-CTX - Upsert in context UE id 1 with IMSI 208950000000004
000750 00199:831721 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000751 00199:831723 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0896    EMM-CTX - get UE id 1 context 0x7f81680011b0 by imsi 208950000000004
000752 00199:831726 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
000753 00199:831729 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0104    Entering emm_reg_send()
000754 00199:831732 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0274    Entering emm_fsm_process()
000755 00199:831735 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000756 00199:831738 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0282    EMM-FSM   - Received event COMMON_PROC_CNF (2) in state EMM-COMMON-PROCEDURE-INITIATED
000757 00199:831741 7F820083C700 TRACE NAS-EM ap/EmmCommonProcedureInitiated.c:0093    Entering EmmCommonProcedureInitiated()
000758 00199:831747 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000759 00199:831750 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0176    Entering emm_fsm_set_state()
000760 00199:831753 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0185    UE 1 EMM-FSM   - Status changed: EMM-COMMON-PROCEDURE-INITIATED ===> EMM-DEREGISTERED
000761 00199:831757 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2251    Entering mme_ue_context_update_ue_emm_state()
000762 00199:831760 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2276    Leaving mme_ue_context_update_ue_emm_state()
000763 00199:831763 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0213    Leaving emm_fsm_set_state() (rc=0)
000764 00199:831767 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1630    Entering _emm_attach_success_identification_cb()
000765 00199:831772 7F820083C700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:1637    Hit 3GPP TS 24_301R10_5_5_1_2_3__1 : EMM common procedure initiation during attach procedure
000766 00199:831775 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1658    Entering _emm_start_attach_proc_authentication()
000767 00199:831779 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0250    Entering emm_proc_authentication()
000768 00199:831783 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0942    New EMM_COMM_PROC_AUTH
000769 00199:831789 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0999    New CN_PROC_AUTH_INFO
000770 00199:831792 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0335    Entering _start_authentication_information_procedure()
000771 00199:831801 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1360    Ts6a_auth_info started UE 1
000772 00199:831805 7F820083C700 TRACE NAS    mme/src/nas/nas_itti_messaging.c:0469    Entering nas_itti_auth_info_req()
000773 00199:831819 7F820083C700 TRACE NAS    mme/src/nas/nas_itti_messaging.c:0502    Leaving nas_itti_auth_info_req()
000774 00199:831822 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0374    Leaving _start_authentication_information_procedure() (rc=0)
000775 00199:831826 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0328    Leaving emm_proc_authentication() (rc=0)
000776 00199:831829 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1666    Leaving _emm_start_attach_proc_authentication() (rc=0)
000777 00199:831832 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1643    Leaving _emm_attach_success_identification_cb() (rc=0)
000778 00199:831835 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000779 00199:831839 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0405    Delete IDENT procedure 2
000780 00199:831845 7F820083C700 TRACE NAS-EM ap/EmmCommonProcedureInitiated.c:0577    Leaving EmmCommonProcedureInitiated() (rc=0)
000781 00199:831848 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0293    Leaving emm_fsm_process() (rc=0)
000782 00199:831851 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0117    Leaving emm_reg_send() (rc=0)
000783 00199:831854 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Identification.c:0439    Leaving emm_proc_identification_complete() (rc=0)
000784 00199:831858 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:0999    Leaving emm_recv_identity_response() (rc=0)
000785 00199:831862 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0483    Entering emm_msg_free()
000786 00199:831866 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0493    EMM-MSG   - Message Type 0x56
000787 00199:831870 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0592    Leaving emm_msg_free()
000788 00199:831875 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0536    Leaving _emm_as_recv() (rc=0)
000789 00199:831878 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0673    Leaving _emm_as_data_ind() (rc=0)
000790 00199:831881 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
000791 00199:831884 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0270    Leaving nas_proc_ul_transfer_ind() (rc=0)
000792 00199:831939 7F81A2FFD700 DEBUG S6A    nair-mme/src/s6a/s6a_auth_info.c:0382    s6a_generate_authentication_info_req plmn: 02F859
000793 00199:831952 7F81A2FFD700 DEBUG S6A    nair-mme/src/s6a/s6a_auth_info.c:0384    s6a_generate_authentication_info_req visited_plmn: 02F859
000794 00199:833784 7F81F17FA700 DEBUG S6A    nair-mme/src/s6a/s6a_auth_info.c:0202    Received S6A Authentication Information Answer (AIA)
000795 00199:833799 7F81F17FA700 DEBUG S6A    nair-mme/src/s6a/s6a_auth_info.c:0234    Received S6A Result code 2001:DIAMETER_SUCCESS
000796 00199:833823 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0275    Entering nas_proc_authentication_info_answer()
000797 00199:833830 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0283    Handling imsi 208950000000004
000798 00199:833837 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000799 00199:833841 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0896    EMM-CTX - get UE id 1 context 0x7f81680011b0 by imsi 208950000000004
000800 00199:833844 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0307    INFORMING NAS ABOUT AUTH RESP SUCCESS got 1 vector(s)
000801 00199:833846 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0335    Entering nas_proc_auth_param_res()
000802 00199:833847 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
000803 00199:833849 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_cn.c:0388    Entering emm_cn_send()
000804 00199:833851 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_cn.c:0390    EMMCN-SAP - Received primitive EMM_CN_AUTHENTICATION_PARAM_RES (401)
000805 00199:833854 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_cn.c:0089    Entering _emm_cn_authentication_res()
000806 00199:833856 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000807 00199:833858 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0399    Entering _auth_info_proc_success_cb()
000808 00199:833860 7F820083C700 NOTIC NAS    mme/src/nas/emm/Authentication.c:0411    Hit 3GPP TS 24_301R10_5_4_2_4__2 : authentication procedure is success, new eKSI for new authentication procedure
000809 00199:833862 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0432    EMM-PROC  - Received Vector 0:
000810 00199:833864 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0435    EMM-PROC  - Received XRES ..: 0d,27,29,ae,7f,6c,8f,d7,00,00,00,00,00,00,00,00
000811 00199:833867 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0438    EMM-PROC  - Received RAND ..: fd,79,d7,04,3d,91,2c,18,87,aa,38,40,fc,07,69,11
000812 00199:833869 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0441    EMM-PROC  - Received AUTN ..: 2e,12,c5,bd,f8,5e,80,00,9f,24,ee,77,19,fd,d3,3c
000813 00199:833872 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0446    EMM-PROC  - Received KASME .: 0a,c7,e4,9d,d5,15,79,55,3d,95,2c,0c,d1,36,23,5d 2f,8a,fd,c5,cd,30,c8,77,a4,84,1d,c8,60,b9,68,e9
000814 00199:833875 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
000815 00199:833877 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0104    Entering emm_reg_send()
000816 00199:833879 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0274    Entering emm_fsm_process()
000817 00199:833881 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000818 00199:833883 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0282    EMM-FSM   - Received event COMMON_PROC_ABORT (4) in state EMM-DEREGISTERED
000819 00199:833885 7F820083C700 TRACE NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0097    Entering EmmDeregistered()
000820 00199:833889 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000821 00199:833892 7F820083C700 WARNI NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0149    EMM-FSM state EMM_DEREGISTERED - Primitive _EMMREG_COMMON_PROC_ABORT is not valid
000822 00199:833895 7F820083C700 TRACE NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0424    Leaving EmmDeregistered() (rc=-1)
000823 00199:833898 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0293    Leaving emm_fsm_process() (rc=-1)
000824 00199:833901 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0117    Leaving emm_reg_send() (rc=-1)
000825 00199:833903 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0167    Entering emm_proc_authentication_ksi()
000826 00199:833906 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0176    ue_id=1 EMM-PROC  - Initiate authentication KSI = 1
000827 00199:833910 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:1082    Entering _authentication_request()
000828 00199:833914 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000829 00199:833917 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0670    Entering emm_as_set_security_data()
000830 00199:833920 7F820083C700 DEBUG NAS-EM air-mme/src/nas/emm/LowerLayer.c:0727    NO Valid Security Context Available
000831 00199:833923 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0734    Leaving emm_as_set_security_data()
000832 00199:833925 7F820083C700 NOTIC NAS    mme/src/nas/emm/Authentication.c:1119    Hit 3GPP TS 24_301R10_5_4_2_2 : Authentication initiation by the network
000833 00199:833927 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
000834 00199:833929 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
000835 00199:833931 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_SECURITY_REQ (201)
000836 00199:833933 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1095    Entering _emm_as_send()
000837 00199:833936 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1599    Entering _emm_as_security_req()
000838 00199:833938 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1602    EMMAS-SAP - Send AS security request
000839 00199:833941 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0903    Entering _emm_as_set_header()
000840 00199:833942 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0959    Leaving _emm_as_set_header() (rc=140196331099824)
000841 00199:833945 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0990    Entering emm_send_authentication_request()
000842 00199:833946 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0993    EMMAS-SAP - Send Authentication Request message
000843 00199:833948 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_send.c:1022    Leaving emm_send_authentication_request() (rc=38)
000844 00199:833950 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000845 00199:833952 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0987    Entering _emm_as_encode()
000846 00199:833955 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0561    Entering nas_message_encode()
000847 00199:833957 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0877    Entering _nas_message_header_encode()
000848 00199:833958 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0913    Leaving _nas_message_header_encode() (rc=1)
000849 00199:833960 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0938    Entering _nas_message_plain_encode()
000850 00199:833963 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0295    Entering emm_msg_encode()
000851 00199:833966 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0465    Leaving emm_msg_encode() (rc=36)
000852 00199:833970 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0963    Leaving _nas_message_plain_encode() (rc=36)
000853 00199:833972 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0656    Leaving nas_message_encode() (rc=36)
000854 00199:833974 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1023    Leaving _emm_as_encode() (rc=36)
000855 00199:833976 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0483    Entering emm_msg_free()
000856 00199:833977 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0493    EMM-MSG   - Message Type 0x52
000857 00199:833979 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0592    Leaving emm_msg_free()
000858 00199:833981 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000859 00199:833984 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:1059    Found emm_common_proc UID 0x3
000860 00199:833989 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1704    Leaving _emm_as_security_req() (rc=263)
000861 00199:833992 7F820083C700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1229    EMMAS-SAP - Sending msg with id 0x107, primitive EMMAS_SECURITY_REQ (201) to S1AP layer for transmission
000862 00199:834003 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1236    Leaving _emm_as_send() (rc=0)
000863 00199:834007 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
000864 00199:834017 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1321    T3460 started UE 1
000865 00199:834020 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:1144    Leaving _authentication_request() (rc=0)
000866 00199:834023 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
000867 00199:834029 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0104    Entering emm_reg_send()
000868 00199:834032 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0274    Entering emm_fsm_process()
000869 00199:834035 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000870 00199:834038 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0282    EMM-FSM   - Received event COMMON_PROC_REQ (1) in state EMM-DEREGISTERED
000871 00199:834042 7F820083C700 TRACE NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0097    Entering EmmDeregistered()
000872 00199:834045 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000873 00199:834048 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0176    Entering emm_fsm_set_state()
000874 00199:834051 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0185    UE 1 EMM-FSM   - Status changed: EMM-DEREGISTERED ===> EMM-COMMON-PROCEDURE-INITIATED
000875 00199:834055 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2251    Entering mme_ue_context_update_ue_emm_state()
000876 00199:834059 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2276    Leaving mme_ue_context_update_ue_emm_state()
000877 00199:834064 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0213    Leaving emm_fsm_set_state() (rc=0)
000878 00199:834068 7F820083C700 TRACE NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0424    Leaving EmmDeregistered() (rc=0)
000879 00199:834073 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0293    Leaving emm_fsm_process() (rc=0)
000880 00199:834077 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0117    Leaving emm_reg_send() (rc=0)
000881 00199:834080 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0243    Leaving emm_proc_authentication_ksi() (rc=0)
000882 00199:834084 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0614    UE 1 Delete AUTH INFO procedure
000883 00199:834091 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1460    Ts6a_auth_info stopped UE 1
000884 00199:834095 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0684    UE 1 Delete CN procedure 0x7f8168001e90
000885 00199:834099 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0525    Leaving _auth_info_proc_success_cb() (rc=0)
000886 00199:834103 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_cn.c:0116    Leaving _emm_cn_authentication_res() (rc=0)
000887 00199:834106 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_cn.c:0438    Leaving emm_cn_send() (rc=0)
000888 00199:834109 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0352    Leaving nas_proc_auth_param_res() (rc=0)
000889 00199:834112 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0329    Leaving nas_proc_authentication_info_answer() (rc=0)
000890 00199:834122 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0051    Entering mme_app_handle_nas_dl_req()
000891 00199:834129 7F81F9704700 DEBUG MME-AP /src/mme_app/mme_app_transport.c:0064    DOWNLINK NAS TRANSPORT Found enb_ue_s1ap_id 06692d mme_ue_s1ap_id 1
000892 00199:834136 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0095     MME_APP:DOWNLINK NAS TRANSPORT. MME_UE_S1AP_ID 1 and ENB_UE_S1AP_ID 06692d. 
000893 00199:834141 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0189    Leaving mme_app_handle_nas_dl_req() (rc=0)
000894 00199:834151 7F81F9FFB700 DEBUG S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0452    SEARCHING UE REFERENCE for SCTP association id 1,  enbUeS1apId 06692d and enbId 3584. 
000895 00199:834180 7F81F9FFB700 NOTIC S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0543    Send S1AP DOWNLINK_NAS_TRANSPORT message ue_id = 1 MME_UE_S1AP_ID = 1 eNB_UE_S1AP_ID = 06692d
000896 00199:834199 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0283    [48][1] Sending buffer 0x7f8168003cf0 of 62 bytes on stream 1 with ppid 18
000897 00199:834244 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0296    Successfully sent 62 bytes on stream 1
000898 00199:927465 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0547    [1][48] Msg of length 73 received from port 36412, on stream 1, PPID 18
000899 00199:927502 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0554    SCTP RETURNING!!
000900 00199:927565 7F81F9FFB700 INFO  S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0295    Received S1AP UPLINK_NAS_TRANSPORT message MME_UE_S1AP_ID 1
000901 00199:927697 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0250    Entering nas_proc_ul_transfer_ind()
000902 00199:927711 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
000903 00199:927716 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
000904 00199:927720 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_DATA_IND (211)
000905 00199:927724 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0557    Entering _emm_as_data_ind()
000906 00199:927727 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0565    EMMAS-SAP - Received AS data transfer indication (ue_id=1, delivered=true, length=25)
000907 00199:927732 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000908 00199:927736 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0260    Entering nas_message_decrypt()
000909 00199:927740 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0694    Entering nas_message_header_decode()
000910 00199:927743 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0751    Leaving nas_message_header_decode() (rc=6)
000911 00199:927747 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1392    Entering _nas_message_get_mac()
000912 00199:927751 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1397    No security context set for integrity protection algorithm
000913 00199:927754 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1398    Leaving _nas_message_get_mac() (rc=0)
000914 00199:927757 7F820083C700 CRITI NAS    rc/nas/api/network/nas_message.c:0311    MAC Failure MSG:E67DF12E(3867013422) <> INT ALGO:00000000(0) Type of security context 0
000915 00199:927761 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1049    Entering _nas_message_decrypt()
000916 00199:927764 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1066    No decryption of message length 19 according to security header type 0x01
000917 00199:927768 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1069    Leaving _nas_message_decrypt() (rc=7)
000918 00199:927771 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0335    Leaving nas_message_decrypt() (rc=19)
000919 00199:927776 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0269    Entering _emm_as_recv()
000920 00199:927783 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0285    EMMAS-SAP - Received EMM message (length=19) integrity protected 1 ciphered 0 mac matched 0 security context 0
000921 00199:927787 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000922 00199:927790 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0360    Entering nas_message_decode()
000923 00199:927793 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0374    hex stream Incoming NAS message:  07 5c 15 30 0e ba 78 3b e6 96 6f 74 c7 50 ff c4 39 18 fb
000924 00199:927805 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0694    Entering nas_message_header_decode()
000925 00199:927808 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0751    Leaving nas_message_header_decode() (rc=1)
000926 00199:927812 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0386    nas_message_header_decode returned size 1
000927 00199:927815 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0776    Entering _nas_message_plain_decode()
000928 00199:927818 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0101    Entering emm_msg_decode()
000929 00199:927821 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0121    EMM-MSG   - Message Type 0x5c
000930 00199:927825 7F820083C700 TRACE NAS    /src/common/3gpp_24.008_mm_ies.c:0243    Entering decode_authentication_failure_parameter_ie()
000931 00199:927829 7F820083C700 TRACE NAS    /src/common/3gpp_24.008_mm_ies.c:0268    Leaving decode_authentication_failure_parameter_ie() (rc=16)
000932 00199:927832 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0274    Leaving emm_msg_decode() (rc=19)
000933 00199:927836 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0799    Leaving _nas_message_plain_decode() (rc=19)
000934 00199:927839 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0539    Leaving nas_message_decode() (rc=19)
000935 00199:927842 7F820083C700 NOTIC NAS    air-mme/src/nas/emm/sap/emm_as.c:0377    Hit 3GPP TS 24_301R10_4_4_4_3__1 : Integrity checking of NAS signalling messages exception in the MME
000936 00199:927845 7F820083C700 NOTIC NAS    air-mme/src/nas/emm/sap/emm_as.c:0380    Hit 3GPP TS 24_301R10_4_4_4_3__2 : Process NAS signalling message in the MME, even if it fails the integrity check or MAC cannot be verified
000937 00199:927849 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:1076    Entering emm_recv_authentication_failure()
000938 00199:927852 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:1080    EMMAS-SAP - Received Authentication Failure message
000939 00199:927858 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0579    Entering emm_proc_authentication_failure()
000940 00199:927863 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000941 00199:927869 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0597    EMM-PROC  - Authentication failure (ue_id=1, cause=21)
000942 00199:927874 7F820083C700 NOTIC NAS    mme/src/nas/emm/Authentication.c:0603    Hit 3GPP TS 24_301R10_5_4_2_4__3 : AUTHENTICATION FAILURE received with EMM cause sync failure, renegociate with HSS.
000943 00199:927885 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1433    T3460 stopped UE 1
000944 00199:927891 7F820083C700 NOTIC NAS    mme/src/nas/emm/Authentication.c:0613    Hit 3GPP TS 24_301R10_5_4_2_4__3 : AUTHENTICATION FAILURE received with EMM cause sync failure, renegociate with HSS.
000945 00199:927896 7F820083C700 DEBUG NAS-EM mme/src/nas/emm/Authentication.c:0622    EMM-PROC  - USIM has detected a mismatch in SQN Ask for new vector(s)
000946 00199:927901 7F820083C700 NOTIC NAS    mme/src/nas/emm/Authentication.c:0624    Hit 3GPP TS 24_301R10_5_4_2_7_e__3 : Re-synchronisation, new vectors
000947 00199:927906 7F820083C700 NOTIC NAS    mme/src/nas/emm/Authentication.c:0626    Hit 3GPP TS 24_301R10_5_4_2_7_e__2 : Re-synchronise with AUTS parameter
000948 00199:927912 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0381    Entering _start_authentication_information_procedure_synch()
000949 00199:927919 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0999    New CN_PROC_AUTH_INFO
000950 00199:927924 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0335    Entering _start_authentication_information_procedure()
000951 00199:927937 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1360    Ts6a_auth_info started UE 1
000952 00199:927950 7F820083C700 TRACE NAS    mme/src/nas/nas_itti_messaging.c:0469    Entering nas_itti_auth_info_req()
000953 00199:927967 7F820083C700 TRACE NAS    mme/src/nas/nas_itti_messaging.c:0502    Leaving nas_itti_auth_info_req()
000954 00199:927972 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0374    Leaving _start_authentication_information_procedure() (rc=0)
000955 00199:927977 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0392    Leaving _start_authentication_information_procedure_synch() (rc=0)
000956 00199:927982 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0387    ue_id=1 clear security context vector index
000957 00199:927987 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0317    ue_id=1 cleared auth vectors 
000958 00199:927992 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0648    Leaving emm_proc_authentication_failure() (rc=0)
000959 00199:927997 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:1112    Leaving emm_recv_authentication_failure() (rc=0)
000960 00199:928002 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0483    Entering emm_msg_free()
000961 00199:928007 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0493    EMM-MSG   - Message Type 0x5c
000962 00199:928012 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0592    Leaving emm_msg_free()
000963 00199:928017 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0536    Leaving _emm_as_recv() (rc=0)
000964 00199:928023 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0673    Leaving _emm_as_data_ind() (rc=0)
000966 00199:928028 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
000965 00199:928023 7F81A2FFD700 DEBUG S6A    nair-mme/src/s6a/s6a_auth_info.c:0382    s6a_generate_authentication_info_req plmn: 02F859
000967 00199:928033 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0270    Leaving nas_proc_ul_transfer_ind() (rc=0)
000968 00199:928053 7F81A2FFD700 DEBUG S6A    nair-mme/src/s6a/s6a_auth_info.c:0384    s6a_generate_authentication_info_req visited_plmn: 02F859
000969 00199:928073 7F81A2FFD700 DEBUG S6A    nair-mme/src/s6a/s6a_auth_info.c:0417    Added Re-Synchronistaion for UE 
000970 00199:931362 7F81F17FA700 DEBUG S6A    nair-mme/src/s6a/s6a_auth_info.c:0202    Received S6A Authentication Information Answer (AIA)
000971 00199:931388 7F81F17FA700 DEBUG S6A    nair-mme/src/s6a/s6a_auth_info.c:0234    Received S6A Result code 2001:DIAMETER_SUCCESS
000972 00199:931443 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0275    Entering nas_proc_authentication_info_answer()
000973 00199:931468 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0283    Handling imsi 208950000000004
000974 00199:931484 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000975 00199:931494 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0896    EMM-CTX - get UE id 1 context 0x7f81680011b0 by imsi 208950000000004
000976 00199:931508 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0307    INFORMING NAS ABOUT AUTH RESP SUCCESS got 1 vector(s)
000977 00199:931518 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0335    Entering nas_proc_auth_param_res()
000978 00199:931527 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
000979 00199:931535 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_cn.c:0388    Entering emm_cn_send()
000980 00199:931549 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_cn.c:0390    EMMCN-SAP - Received primitive EMM_CN_AUTHENTICATION_PARAM_RES (401)
000981 00199:931558 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_cn.c:0089    Entering _emm_cn_authentication_res()
000982 00199:931566 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000983 00199:931574 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0399    Entering _auth_info_proc_success_cb()
000984 00199:931583 7F820083C700 NOTIC NAS    mme/src/nas/emm/Authentication.c:0411    Hit 3GPP TS 24_301R10_5_4_2_4__2 : authentication procedure is success, new eKSI for new authentication procedure
000985 00199:931591 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0432    EMM-PROC  - Received Vector 0:
000986 00199:931600 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0435    EMM-PROC  - Received XRES ..: 06,3c,b8,c1,68,93,3a,60,00,00,00,00,00,00,00,00
000987 00199:931612 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0438    EMM-PROC  - Received RAND ..: 80,8c,95,7c,c0,69,7e,5a,4d,e9,8f,74,e9,d7,a0,50
000988 00199:931619 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0441    EMM-PROC  - Received AUTN ..: a6,86,81,cf,05,b4,80,00,d2,f6,bf,99,fb,fe,1c,44
000989 00199:931626 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0446    EMM-PROC  - Received KASME .: 16,78,a1,64,c3,af,15,be,a3,da,48,6a,7e,8e,e5,0e 7a,95,bc,95,08,78,d3,dc,f6,64,6b,95,06,6e,23,ce
000990 00199:931638 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
000991 00199:931645 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0104    Entering emm_reg_send()
000992 00199:931651 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0274    Entering emm_fsm_process()
000993 00199:931656 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000994 00199:931661 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0282    EMM-FSM   - Received event COMMON_PROC_ABORT (4) in state EMM-COMMON-PROCEDURE-INITIATED
000995 00199:931667 7F820083C700 TRACE NAS-EM ap/EmmCommonProcedureInitiated.c:0093    Entering EmmCommonProcedureInitiated()
000996 00199:931672 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
000997 00199:931677 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:1266    Entering _authentication_abort()
000998 00199:931682 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:1274    EMM-PROC  - Abort authentication procedure (ue_id=1)
000999 00199:931687 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:1283    Leaving _authentication_abort() (rc=-1)
001000 00199:931694 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001001 00199:931702 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0176    Entering emm_fsm_set_state()
001002 00199:931709 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0185    UE 1 EMM-FSM   - Status changed: EMM-COMMON-PROCEDURE-INITIATED ===> EMM-DEREGISTERED
001003 00199:931718 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2251    Entering mme_ue_context_update_ue_emm_state()
001004 00199:931728 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2276    Leaving mme_ue_context_update_ue_emm_state()
001005 00199:931735 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0213    Leaving emm_fsm_set_state() (rc=0)
001006 00199:931744 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001007 00199:931752 7F820083C700 TRACE NAS-EM ap/EmmCommonProcedureInitiated.c:0577    Leaving EmmCommonProcedureInitiated() (rc=0)
001008 00199:931760 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0293    Leaving emm_fsm_process() (rc=0)
001009 00199:931768 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0117    Leaving emm_reg_send() (rc=0)
001010 00199:931776 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0167    Entering emm_proc_authentication_ksi()
001011 00199:931783 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0176    ue_id=1 EMM-PROC  - Initiate authentication KSI = 2
001012 00199:931792 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:1082    Entering _authentication_request()
001013 00199:931800 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001014 00199:931807 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0670    Entering emm_as_set_security_data()
001015 00199:931815 7F820083C700 DEBUG NAS-EM air-mme/src/nas/emm/LowerLayer.c:0727    NO Valid Security Context Available
001016 00199:931821 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0734    Leaving emm_as_set_security_data()
001017 00199:931829 7F820083C700 NOTIC NAS    mme/src/nas/emm/Authentication.c:1119    Hit 3GPP TS 24_301R10_5_4_2_2 : Authentication initiation by the network
001018 00199:931837 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001019 00199:931844 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
001020 00199:931852 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_SECURITY_REQ (201)
001021 00199:931860 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1095    Entering _emm_as_send()
001022 00199:931869 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1599    Entering _emm_as_security_req()
001023 00199:931876 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1602    EMMAS-SAP - Send AS security request
001024 00199:931884 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0903    Entering _emm_as_set_header()
001025 00199:931892 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0959    Leaving _emm_as_set_header() (rc=140196331099824)
001026 00199:931901 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0990    Entering emm_send_authentication_request()
001027 00199:931908 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0993    EMMAS-SAP - Send Authentication Request message
001028 00199:931917 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_send.c:1022    Leaving emm_send_authentication_request() (rc=38)
001029 00199:931925 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001030 00199:931933 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0987    Entering _emm_as_encode()
001031 00199:931941 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0561    Entering nas_message_encode()
001032 00199:931949 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0877    Entering _nas_message_header_encode()
001033 00199:931957 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0913    Leaving _nas_message_header_encode() (rc=1)
001034 00199:931965 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0938    Entering _nas_message_plain_encode()
001035 00199:931972 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0295    Entering emm_msg_encode()
001036 00199:931979 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0465    Leaving emm_msg_encode() (rc=36)
001037 00199:931984 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0963    Leaving _nas_message_plain_encode() (rc=36)
001038 00199:931990 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0656    Leaving nas_message_encode() (rc=36)
001039 00199:931997 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1023    Leaving _emm_as_encode() (rc=36)
001040 00199:932005 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0483    Entering emm_msg_free()
001041 00199:932013 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0493    EMM-MSG   - Message Type 0x52
001042 00199:932021 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0592    Leaving emm_msg_free()
001043 00199:932028 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001044 00199:932034 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:1059    Found emm_common_proc UID 0x3
001045 00199:932039 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1704    Leaving _emm_as_security_req() (rc=263)
001046 00199:932044 7F820083C700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1229    EMMAS-SAP - Sending msg with id 0x107, primitive EMMAS_SECURITY_REQ (201) to S1AP layer for transmission
001047 00199:932060 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1236    Leaving _emm_as_send() (rc=0)
001048 00199:932068 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
001049 00199:932077 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0051    Entering mme_app_handle_nas_dl_req()
001050 00199:932087 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1321    T3460 started UE 1
001051 00199:932091 7F81F9704700 DEBUG MME-AP /src/mme_app/mme_app_transport.c:0064    DOWNLINK NAS TRANSPORT Found enb_ue_s1ap_id 06692d mme_ue_s1ap_id 1
001052 00199:932096 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:1144    Leaving _authentication_request() (rc=0)
001053 00199:932105 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001054 00199:932106 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0095     MME_APP:DOWNLINK NAS TRANSPORT. MME_UE_S1AP_ID 1 and ENB_UE_S1AP_ID 06692d. 
001055 00199:932113 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0104    Entering emm_reg_send()
001056 00199:932116 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0189    Leaving mme_app_handle_nas_dl_req() (rc=0)
001057 00199:932126 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0274    Entering emm_fsm_process()
001058 00199:932133 7F81F9FFB700 DEBUG S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0452    SEARCHING UE REFERENCE for SCTP association id 1,  enbUeS1apId 06692d and enbId 3584. 
001059 00199:932141 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001060 00199:932163 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0282    EMM-FSM   - Received event COMMON_PROC_REQ (1) in state EMM-DEREGISTERED
001061 00199:932176 7F820083C700 TRACE NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0097    Entering EmmDeregistered()
001062 00199:932182 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001063 00199:932184 7F81F9FFB700 NOTIC S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0543    Send S1AP DOWNLINK_NAS_TRANSPORT message ue_id = 1 MME_UE_S1AP_ID = 1 eNB_UE_S1AP_ID = 06692d
001064 00199:932189 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0176    Entering emm_fsm_set_state()
001065 00199:932197 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0185    UE 1 EMM-FSM   - Status changed: EMM-DEREGISTERED ===> EMM-COMMON-PROCEDURE-INITIATED
001066 00199:932205 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2251    Entering mme_ue_context_update_ue_emm_state()
001067 00199:932214 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2276    Leaving mme_ue_context_update_ue_emm_state()
001069 00199:932222 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0213    Leaving emm_fsm_set_state() (rc=0)
001068 00199:932220 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0283    [48][1] Sending buffer 0x7f81640099b0 of 62 bytes on stream 1 with ppid 18
001070 00199:932230 7F820083C700 TRACE NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0424    Leaving EmmDeregistered() (rc=0)
001071 00199:932250 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0293    Leaving emm_fsm_process() (rc=0)
001072 00199:932256 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0117    Leaving emm_reg_send() (rc=0)
001073 00199:932261 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0243    Leaving emm_proc_authentication_ksi() (rc=0)
001074 00199:932266 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0614    UE 1 Delete AUTH INFO procedure
001075 00199:932297 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0296    Successfully sent 62 bytes on stream 1
001076 00199:932323 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1460    Ts6a_auth_info stopped UE 1
001077 00199:932332 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0684    UE 1 Delete CN procedure 0x7f8168002120
001078 00199:932341 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0525    Leaving _auth_info_proc_success_cb() (rc=0)
001079 00199:932350 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_cn.c:0116    Leaving _emm_cn_authentication_res() (rc=0)
001080 00199:932359 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_cn.c:0438    Leaving emm_cn_send() (rc=0)
001081 00199:932368 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0352    Leaving nas_proc_auth_param_res() (rc=0)
001082 00199:932376 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0329    Leaving nas_proc_authentication_info_answer() (rc=0)
001083 00200:077398 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0547    [1][48] Msg of length 65 received from port 36412, on stream 1, PPID 18
001084 00200:077429 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0554    SCTP RETURNING!!
001085 00200:077477 7F81F9FFB700 INFO  S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0295    Received S1AP UPLINK_NAS_TRANSPORT message MME_UE_S1AP_ID 1
001086 00200:077643 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0250    Entering nas_proc_ul_transfer_ind()
001087 00200:077655 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001088 00200:077661 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
001089 00200:077666 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_DATA_IND (211)
001090 00200:077671 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0557    Entering _emm_as_data_ind()
001091 00200:077676 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0565    EMMAS-SAP - Received AS data transfer indication (ue_id=1, delivered=true, length=17)
001092 00200:077683 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001093 00200:077688 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0260    Entering nas_message_decrypt()
001094 00200:077696 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0694    Entering nas_message_header_decode()
001095 00200:077704 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0751    Leaving nas_message_header_decode() (rc=6)
001096 00200:077711 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1392    Entering _nas_message_get_mac()
001097 00200:077716 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1397    No security context set for integrity protection algorithm
001098 00200:077724 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1398    Leaving _nas_message_get_mac() (rc=0)
001099 00200:077732 7F820083C700 CRITI NAS    rc/nas/api/network/nas_message.c:0311    MAC Failure MSG:7AFF8449(2063565897) <> INT ALGO:00000000(0) Type of security context 0
001100 00200:077742 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1049    Entering _nas_message_decrypt()
001101 00200:077749 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1066    No decryption of message length 11 according to security header type 0x01
001102 00200:077757 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1069    Leaving _nas_message_decrypt() (rc=7)
001103 00200:077765 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0335    Leaving nas_message_decrypt() (rc=11)
001104 00200:077774 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0269    Entering _emm_as_recv()
001105 00200:077781 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0285    EMMAS-SAP - Received EMM message (length=11) integrity protected 1 ciphered 0 mac matched 0 security context 0
001106 00200:077790 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001107 00200:077799 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0360    Entering nas_message_decode()
001108 00200:077806 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0374    hex stream Incoming NAS message:  07 53 08 06 3c b8 c1 68 93 3a 60
001109 00200:077858 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0694    Entering nas_message_header_decode()
001110 00200:077869 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0751    Leaving nas_message_header_decode() (rc=1)
001111 00200:077879 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0386    nas_message_header_decode returned size 1
001112 00200:077891 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0776    Entering _nas_message_plain_decode()
001113 00200:077901 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0101    Entering emm_msg_decode()
001114 00200:077912 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0121    EMM-MSG   - Message Type 0x53
001115 00200:077923 7F820083C700 TRACE NAS    /src/common/3gpp_24.008_mm_ies.c:0177    Entering decode_authentication_response_parameter_ie()
001116 00200:077935 7F820083C700 TRACE NAS    /src/common/3gpp_24.008_mm_ies.c:0202    Leaving decode_authentication_response_parameter_ie() (rc=9)
001117 00200:077946 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0274    Leaving emm_msg_decode() (rc=11)
001118 00200:077957 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0799    Leaving _nas_message_plain_decode() (rc=11)
001119 00200:077968 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0539    Leaving nas_message_decode() (rc=11)
001120 00200:077979 7F820083C700 NOTIC NAS    air-mme/src/nas/emm/sap/emm_as.c:0366    Hit 3GPP TS 24_301R10_4_4_4_3__1 : Integrity checking of NAS signalling messages exception in the MME
001121 00200:077989 7F820083C700 NOTIC NAS    air-mme/src/nas/emm/sap/emm_as.c:0369    Hit 3GPP TS 24_301R10_4_4_4_3__2 : Process NAS signalling message in the MME, even if it fails the integrity check or MAC cannot be verified
001122 00200:078000 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:1020    Entering emm_recv_authentication_response()
001123 00200:078010 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:1024    EMMAS-SAP - Received Authentication Response message
001124 00200:078021 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0821    Entering emm_proc_authentication_complete()
001125 00200:078054 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0826    EMM-PROC  - Authentication complete (ue_id=1)
001126 00200:078065 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001127 00200:078076 7F820083C700 INFO  NAS-EM mme/src/nas/emm/Authentication.c:0840    EMM-PROC  - Authentication complete (ue_id=1, cause=-1)
001128 00200:078087 7F820083C700 NOTIC NAS    mme/src/nas/emm/Authentication.c:0846    Hit 3GPP TS 24_301R10_5_4_2_4__1 : AUTHENTICATION RESPONSE received, stop T3460, check RES
001129 00200:078105 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1433    T3460 stopped UE 1
001130 00200:078120 7F820083C700 NOTIC NAS    mme/src/nas/emm/Authentication.c:0854    Hit 3GPP TS 24_301R10_5_4_2_4__2 : authentication procedure is success, new eKSI for new authentication procedure
001131 00200:078130 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0377    ue_id=1 set security context eksi 2
001132 00200:078141 7F820083C700 DEBUG NAS-EM mme/src/nas/emm/Authentication.c:0858    EMM-PROC  - Success to authentify the UE  RESP XRES == XRES UE CONTEXT
001133 00200:078152 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001134 00200:078162 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0104    Entering emm_reg_send()
001135 00200:078180 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0274    Entering emm_fsm_process()
001136 00200:078190 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001137 00200:078200 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0282    EMM-FSM   - Received event COMMON_PROC_CNF (2) in state EMM-COMMON-PROCEDURE-INITIATED
001138 00200:078211 7F820083C700 TRACE NAS-EM ap/EmmCommonProcedureInitiated.c:0093    Entering EmmCommonProcedureInitiated()
001139 00200:078221 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001140 00200:078232 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0176    Entering emm_fsm_set_state()
001141 00200:078241 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0185    UE 1 EMM-FSM   - Status changed: EMM-COMMON-PROCEDURE-INITIATED ===> EMM-DEREGISTERED
001142 00200:078252 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2251    Entering mme_ue_context_update_ue_emm_state()
001143 00200:078263 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2276    Leaving mme_ue_context_update_ue_emm_state()
001144 00200:078281 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0213    Leaving emm_fsm_set_state() (rc=0)
001145 00200:078292 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1672    Entering _emm_attach_success_authentication_cb()
001146 00200:078303 7F820083C700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:1686    Hit 3GPP TS 24_301R10_5_5_1_2_3__1 : EMM common procedure initiation during attach procedure
001147 00200:078322 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1722    Entering _emm_start_attach_proc_security()
001148 00200:078332 7F820083C700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:1726    Hit 3GPP TS 24_301R10_5_5_1_2_3__1 : EMM common procedure initiation during attach procedure
001149 00200:078343 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0368    ue_id=1 set security context security type 0
001150 00200:078360 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0377    ue_id=1 set security context eksi 7
001151 00200:078370 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0358    ue_id=1 cleared security context 
001152 00200:078381 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0377    ue_id=1 set security context eksi 2
001153 00200:078421 7F820083C700 TRACE NAS-EM rc/nas/emm/SecurityModeControl.c:0165    Entering emm_proc_security_mode_control()
001154 00200:078434 7F820083C700 INFO  NAS-EM rc/nas/emm/SecurityModeControl.c:0177    EMM-PROC  - Initiate security mode control procedure KSI = 2
001155 00200:078447 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0972    New EMM_COMM_PROC_SMC
001156 00200:078457 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0377    ue_id=1 set security context eksi 2
001157 00200:078467 7F820083C700 NOTIC NAS    rc/nas/emm/SecurityModeControl.c:0216    Hit 3GPP TS 24_301R10_5_4_3_2__2 : SMC initiation, reset DL NAS count, use SC
001158 00200:078476 7F820083C700 TRACE NAS-EM rc/nas/emm/SecurityModeControl.c:0858    Entering _security_select_algorithms()
001159 00200:078486 7F820083C700 DEBUG NAS-EM rc/nas/emm/SecurityModeControl.c:0872    Selected  NAS_SECURITY_ALGORITHMS_EIA2 (choice num 0)
001160 00200:078496 7F820083C700 DEBUG NAS-EM rc/nas/emm/SecurityModeControl.c:0886    Selected  NAS_SECURITY_ALGORITHMS_EEA0 (choice num 0)
001161 00200:078506 7F820083C700 TRACE NAS-EM rc/nas/emm/SecurityModeControl.c:0892    Leaving _security_select_algorithms() (rc=0)
001162 00200:078517 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0368    ue_id=1 set security context security type 2
001163 00200:078561 7F820083C700 INFO  NAS-EM rc/nas/emm/SecurityModeControl.c:0322    EMM-PROC  - SMC gprs_present 1 gea bits 70
001164 00200:078574 7F820083C700 TRACE NAS-EM rc/nas/emm/SecurityModeControl.c:0690    Entering _security_request()
001165 00200:078584 7F820083C700 NOTIC NAS    rc/nas/emm/SecurityModeControl.c:0700    Hit 3GPP TS 24_301R10_5_4_3_2__14 : SMC initiation, include replayed security capabilities, eKSI, algos
001166 00200:078595 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001167 00200:078606 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0670    Entering emm_as_set_security_data()
001168 00200:078616 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/LowerLayer.c:0688    EPS security context exists is new 1 KSI 2 SQN 0 count 0
001169 00200:078627 7F820083C700 DEBUG NAS-EM air-mme/src/nas/emm/LowerLayer.c:0690    hex stream knas_int: 3d 40 c1 8e 32 36 d6 3a a0 21 09 07 3a dd 31 2f
001170 00200:078655 7F820083C700 DEBUG NAS-EM air-mme/src/nas/emm/LowerLayer.c:0692    hex stream knas_enc: 63 ea 72 08 d9 f2 18 14 72 e7 bc 9d cd e2 23 4c
001171 00200:078689 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0734    Leaving emm_as_set_security_data()
001172 00200:078700 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001173 00200:078711 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
001174 00200:078721 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_SECURITY_REQ (201)
001175 00200:078732 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1095    Entering _emm_as_send()
001176 00200:078744 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1599    Entering _emm_as_security_req()
001177 00200:078754 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1602    EMMAS-SAP - Send AS security request
001178 00200:078765 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0903    Entering _emm_as_set_header()
001179 00200:078775 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0929    Leaving _emm_as_set_header() (rc=140196331095536)
001180 00200:078786 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_send.c:1074    Entering emm_send_security_mode_command()
001181 00200:078796 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:1077    EMMAS-SAP - Send Security Mode Command message
001182 00200:078806 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:1114    imeisvrequest                               1
001183 00200:078816 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:1117    replayeduesecuritycapabilities.gprs_present 1
001184 00200:078826 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:1119    replayeduesecuritycapabilities.gea          112
001185 00200:078836 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_send.c:1121    Leaving emm_send_security_mode_command() (rc=13)
001186 00200:078847 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001187 00200:078858 7F820083C700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1689    Set nas_msg.header.sequence_number -> 0
001188 00200:078868 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0987    Entering _emm_as_encode()
001189 00200:078879 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0561    Entering nas_message_encode()
001190 00200:078889 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0877    Entering _nas_message_header_encode()
001191 00200:078899 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0913    Leaving _nas_message_header_encode() (rc=6)
001192 00200:078926 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0987    Entering _nas_message_protected_encode()
001193 00200:078937 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0938    Entering _nas_message_plain_encode()
001194 00200:078948 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0295    Entering emm_msg_encode()
001195 00200:078961 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0465    Leaving emm_msg_encode() (rc=11)
001196 00200:078972 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0963    Leaving _nas_message_plain_encode() (rc=11)
001197 00200:078983 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1241    Entering _nas_message_encrypt()
001198 00200:078993 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1258    No encryption of message according to security header type 0x03
001199 00200:079004 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1260    Leaving _nas_message_encrypt() (rc=11)
001200 00200:079015 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1016    Leaving _nas_message_protected_encode() (rc=11)
001201 00200:079026 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0596    offset 5 = 6 - 1, hdr encode = 6, length = 19 bytes = 11
001202 00200:079038 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1392    Entering _nas_message_get_mac()
001203 00200:079049 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1469    NAS_SECURITY_ALGORITHMS_EIA2 dir DOWNLINK count.seq_num 0 count 0
001204 00200:079076 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0076    Byte length: 20, Zero bits: 0:
001205 00200:079098 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0077    hex stream m: 00 00 00 00 04 00 00 00 00 07 5d 02 02 05 f0 70 c0 40 70 c1
001206 00200:079130 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0079    hex stream Key: 3d 40 c1 8e 32 36 d6 3a a0 21 09 07 3a dd 31 2f
001207 00200:079156 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0081    hex stream Message: 00 07 5d 02 02 05 f0 70 c0 40 70 c1
001208 00200:079240 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0089    hex stream Out: fd f2 c3 eb 1f cc a9 47 e1 2c ad 27 8f f8 8d 9b
001209 00200:079277 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1485    NAS_SECURITY_ALGORITHMS_EIA2 returned MAC fd.f2.c3.eb(3955487485) for length 12 direction 1, count 0
001210 00200:079292 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1487    Leaving _nas_message_get_mac() (rc=4260545515)
001211 00200:079302 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0627    Incremented emm_security_context.dl_count.seq_num -> 1
001212 00200:079312 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0653    Leaving nas_message_encode() (rc=17)
001213 00200:079323 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1023    Leaving _emm_as_encode() (rc=17)
001214 00200:079334 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0483    Entering emm_msg_free()
001215 00200:079344 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0493    EMM-MSG   - Message Type 0x5d
001216 00200:079354 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0592    Leaving emm_msg_free()
001217 00200:079365 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001218 00200:079376 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:1059    Found emm_common_proc UID 0x6
001219 00200:079401 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1704    Leaving _emm_as_security_req() (rc=263)
001220 00200:079412 7F820083C700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1229    EMMAS-SAP - Sending msg with id 0x107, primitive EMMAS_SECURITY_REQ (201) to S1AP layer for transmission
001221 00200:079439 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1236    Leaving _emm_as_send() (rc=0)
001222 00200:079455 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
001224 00200:079466 7F820083C700 NOTIC NAS    rc/nas/emm/SecurityModeControl.c:0740    Hit 3GPP TS 24_301R10_5_4_3_2__1 : SMC initiation, start T3460
001223 00200:079463 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0051    Entering mme_app_handle_nas_dl_req()
001226 00200:079488 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1321    T3460 started UE 1
001225 00200:079487 7F81F9704700 DEBUG MME-AP /src/mme_app/mme_app_transport.c:0064    DOWNLINK NAS TRANSPORT Found enb_ue_s1ap_id 06692d mme_ue_s1ap_id 1
001227 00200:079514 7F820083C700 TRACE NAS-EM rc/nas/emm/SecurityModeControl.c:0752    Leaving _security_request() (rc=0)
001228 00200:079559 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001229 00200:079562 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0095     MME_APP:DOWNLINK NAS TRANSPORT. MME_UE_S1AP_ID 1 and ENB_UE_S1AP_ID 06692d. 
001230 00200:079571 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0104    Entering emm_reg_send()
001231 00200:079577 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0189    Leaving mme_app_handle_nas_dl_req() (rc=0)
001232 00200:079582 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0274    Entering emm_fsm_process()
001233 00200:079604 7F81F9FFB700 DEBUG S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0452    SEARCHING UE REFERENCE for SCTP association id 1,  enbUeS1apId 06692d and enbId 3584. 
001234 00200:079607 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001235 00200:079653 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0282    EMM-FSM   - Received event COMMON_PROC_REQ (1) in state EMM-DEREGISTERED
001236 00200:079667 7F820083C700 TRACE NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0097    Entering EmmDeregistered()
001237 00200:079675 7F81F9FFB700 NOTIC S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0543    Send S1AP DOWNLINK_NAS_TRANSPORT message ue_id = 1 MME_UE_S1AP_ID = 1 eNB_UE_S1AP_ID = 06692d
001238 00200:079679 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001239 00200:079733 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0283    [48][1] Sending buffer 0x7f8168002200 of 43 bytes on stream 1 with ppid 18
001240 00200:079738 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0176    Entering emm_fsm_set_state()
001241 00200:079785 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0185    UE 1 EMM-FSM   - Status changed: EMM-DEREGISTERED ===> EMM-COMMON-PROCEDURE-INITIATED
001242 00200:079798 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2251    Entering mme_ue_context_update_ue_emm_state()
001243 00200:079809 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2276    Leaving mme_ue_context_update_ue_emm_state()
001244 00200:079820 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0213    Leaving emm_fsm_set_state() (rc=0)
001245 00200:079831 7F820083C700 TRACE NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0424    Leaving EmmDeregistered() (rc=0)
001246 00200:079834 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0296    Successfully sent 43 bytes on stream 1
001247 00200:079843 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0293    Leaving emm_fsm_process() (rc=0)
001248 00200:079868 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0117    Leaving emm_reg_send() (rc=0)
001249 00200:079885 7F820083C700 TRACE NAS-EM rc/nas/emm/SecurityModeControl.c:0363    Leaving emm_proc_security_mode_control() (rc=0)
001250 00200:079896 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1761    Leaving _emm_start_attach_proc_security() (rc=0)
001251 00200:079907 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1689    Leaving _emm_attach_success_authentication_cb() (rc=0)
001252 00200:079918 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001253 00200:079929 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0393    UE 1 Delete AUTH procedure
001254 00200:079940 7F820083C700 TRACE NAS-EM ap/EmmCommonProcedureInitiated.c:0577    Leaving EmmCommonProcedureInitiated() (rc=0)
001255 00200:079951 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0293    Leaving emm_fsm_process() (rc=0)
001256 00200:079962 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0117    Leaving emm_reg_send() (rc=0)
001257 00200:079973 7F820083C700 TRACE NAS-EM mme/src/nas/emm/Authentication.c:0873    Leaving emm_proc_authentication_complete() (rc=0)
001258 00200:079994 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:1054    Leaving emm_recv_authentication_response() (rc=0)
001259 00200:080007 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0483    Entering emm_msg_free()
001260 00200:080018 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0493    EMM-MSG   - Message Type 0x53
001261 00200:080029 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0592    Leaving emm_msg_free()
001262 00200:080040 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0536    Leaving _emm_as_recv() (rc=0)
001263 00200:080051 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0673    Leaving _emm_as_data_ind() (rc=0)
001264 00200:080062 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
001265 00200:080073 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0270    Leaving nas_proc_ul_transfer_ind() (rc=0)
001266 00200:104394 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0547    [1][48] Msg of length 67 received from port 36412, on stream 1, PPID 18
001267 00200:104426 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0554    SCTP RETURNING!!
001268 00200:104515 7F81F9FFB700 INFO  S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0295    Received S1AP UPLINK_NAS_TRANSPORT message MME_UE_S1AP_ID 1
001269 00200:104729 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0250    Entering nas_proc_ul_transfer_ind()
001270 00200:104749 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001271 00200:104758 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
001272 00200:104764 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_DATA_IND (211)
001273 00200:104771 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0557    Entering _emm_as_data_ind()
001274 00200:104779 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0565    EMMAS-SAP - Received AS data transfer indication (ue_id=1, delivered=true, length=19)
001275 00200:104791 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001276 00200:104807 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0260    Entering nas_message_decrypt()
001277 00200:104817 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0694    Entering nas_message_header_decode()
001278 00200:104828 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0751    Leaving nas_message_header_decode() (rc=6)
001279 00200:104839 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1392    Entering _nas_message_get_mac()
001280 00200:104849 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1469    NAS_SECURITY_ALGORITHMS_EIA2 dir UPLINK count.seq_num 0 count 0
001281 00200:104861 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0076    Byte length: 22, Zero bits: 0:
001282 00200:104873 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0077    hex stream m: 00 00 00 00 00 00 00 00 00 07 5e 23 09 33 35 33 09 46 96 46 17 f0
001283 00200:104913 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0079    hex stream Key: 3d 40 c1 8e 32 36 d6 3a a0 21 09 07 3a dd 31 2f
001284 00200:104940 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0081    hex stream Message: 00 07 5e 23 09 33 35 33 09 46 96 46 17 f0
001285 00200:104978 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0089    hex stream Out: af 82 fb 80 1d 4b 63 05 1f d1 28 59 0c c9 5a 95
001286 00200:105007 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1485    NAS_SECURITY_ALGORITHMS_EIA2 returned MAC af.82.fb.80(2163966639) for length 14 direction 0, count 0
001287 00200:105022 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1487    Leaving _nas_message_get_mac() (rc=2944596864)
001288 00200:105033 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0303    Integrity: MAC Success
001289 00200:105044 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1049    Entering _nas_message_decrypt()
001290 00200:105054 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1175    NAS_SECURITY_ALGORITHMS_EEA0 dir 0 ul_count.seq_num 0 dl_count.seq_num 1
001291 00200:105065 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1183    Leaving _nas_message_decrypt() (rc=7)
001292 00200:105076 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0335    Leaving nas_message_decrypt() (rc=13)
001293 00200:105087 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0269    Entering _emm_as_recv()
001294 00200:105097 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0285    EMMAS-SAP - Received EMM message (length=13) integrity protected 1 ciphered 1 mac matched 1 security context 1
001295 00200:105110 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001296 00200:105121 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0360    Entering nas_message_decode()
001297 00200:105130 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0374    hex stream Incoming NAS message:  07 5e 23 09 33 35 33 09 46 96 46 17 f0
001298 00200:105165 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0694    Entering nas_message_header_decode()
001299 00200:105175 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0751    Leaving nas_message_header_decode() (rc=1)
001300 00200:105186 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0386    nas_message_header_decode returned size 1
001301 00200:105196 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0776    Entering _nas_message_plain_decode()
001302 00200:105206 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0101    Entering emm_msg_decode()
001303 00200:105217 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0121    EMM-MSG   - Message Type 0x5e
001304 00200:105229 7F820083C700 TRACE NAS-EM /common/3gpp_24.008_common_ies.c:0421    Entering decode_imeisv_mobile_identity()
001305 00200:105240 7F820083C700 TRACE NAS-EM /common/3gpp_24.008_common_ies.c:0471    Leaving decode_imeisv_mobile_identity() (rc=9)
001306 00200:105251 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0274    Leaving emm_msg_decode() (rc=13)
001307 00200:105262 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0799    Leaving _nas_message_plain_decode() (rc=13)
001308 00200:105273 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0539    Leaving nas_message_decode() (rc=13)
001309 00200:105284 7F820083C700 NOTIC NAS    air-mme/src/nas/emm/sap/emm_as.c:0387    Hit 3GPP TS 24_301R10_4_4_4_3__1 : Integrity checking of NAS signalling messages exception in the MME
001310 00200:105294 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:1134    Entering emm_recv_security_mode_complete()
001311 00200:105305 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:1138    EMMAS-SAP - Received Security Mode Complete message
001312 00200:105315 7F820083C700 TRACE NAS-EM rc/nas/emm/SecurityModeControl.c:0390    Entering emm_proc_security_mode_complete()
001313 00200:105325 7F820083C700 INFO  NAS-EM rc/nas/emm/SecurityModeControl.c:0398    EMM-PROC  - Security mode complete (ue_id=1)
001314 00200:105336 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001315 00200:105347 7F820083C700 NOTIC NAS    rc/nas/emm/SecurityModeControl.c:0414    Hit 3GPP TS 24_301R10_5_4_3_4__1 : SMC completion, stop T3460, 
001316 00200:105363 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1433    T3460 stopped UE 1
001317 00200:105391 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0266    ue_id=1 set IMEI_SV (valid)
001318 00200:105403 7F820083C700 NOTIC NAS    rc/nas/emm/SecurityModeControl.c:0464    Hit 3GPP TS 24_301R10_5_4_3_4__2 : SMC completion, integ. cipher. all messages
001319 00200:105414 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001320 00200:105425 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0104    Entering emm_reg_send()
001321 00200:105435 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0274    Entering emm_fsm_process()
001322 00200:105446 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001323 00200:105456 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0282    EMM-FSM   - Received event COMMON_PROC_CNF (2) in state EMM-COMMON-PROCEDURE-INITIATED
001324 00200:105468 7F820083C700 TRACE NAS-EM ap/EmmCommonProcedureInitiated.c:0093    Entering EmmCommonProcedureInitiated()
001325 00200:105478 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001326 00200:105489 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0176    Entering emm_fsm_set_state()
001327 00200:105499 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0185    UE 1 EMM-FSM   - Status changed: EMM-COMMON-PROCEDURE-INITIATED ===> EMM-DEREGISTERED
001328 00200:105511 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2251    Entering mme_ue_context_update_ue_emm_state()
001329 00200:105523 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2276    Leaving mme_ue_context_update_ue_emm_state()
001330 00200:105533 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0213    Leaving emm_fsm_set_state() (rc=0)
001331 00200:105544 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1767    Entering _emm_attach_success_security_cb()
001332 00200:105572 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1779    Leaving _emm_attach_success_security_cb() (rc=0)
001333 00200:105582 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001334 00200:105594 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0400    Delete SMC procedure 6
001335 00200:105604 7F820083C700 TRACE NAS-EM ap/EmmCommonProcedureInitiated.c:0577    Leaving EmmCommonProcedureInitiated() (rc=0)
001336 00200:105615 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0293    Leaving emm_fsm_process() (rc=0)
001337 00200:105625 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0117    Leaving emm_reg_send() (rc=0)
001338 00200:105634 7F820083C700 TRACE NAS-EM rc/nas/emm/SecurityModeControl.c:0469    Leaving emm_proc_security_mode_complete() (rc=0)
001339 00200:105645 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:1150    Leaving emm_recv_security_mode_complete() (rc=0)
001341 00200:105656 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0483    Entering emm_msg_free()
001340 00200:105652 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/nas_esm_proc.c:0159    Entering nas_esm_proc_data_ind()
001342 00200:105666 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0493    EMM-MSG   - Message Type 0x5e
001343 00200:105680 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0592    Leaving emm_msg_free()
001344 00200:105683 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0573    Entering _esm_sap_recv()
001345 00200:105690 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0536    Leaving _emm_as_recv() (rc=0)
001346 00200:105701 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0117    Entering esm_msg_decode()
001347 00200:105702 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0673    Leaving _emm_as_data_ind() (rc=0)
001348 00200:105738 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0261    Leaving esm_msg_decode() (rc=39)
001349 00200:105756 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
001350 00200:105764 7F81FBFFF700 DEBUG NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0661    ESM-SAP   - PDN_CONNECTIVITY_REQUEST pti 45 ebi 0
001351 00200:105769 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0270    Leaving nas_proc_ul_transfer_ind() (rc=0)
001352 00200:105787 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/sap/esm_recv.c:0156    Entering esm_recv_pdn_connectivity_request()
001353 00200:105807 7F81FBFFF700 INFO  NAS-ES r-mme/src/nas/esm/sap/esm_recv.c:0163    ESM-SAP   - Received PDN Connectivity Request message (ue_id=1, pti=45, ebi=0)
001354 00200:105826 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0216    Entering mme_app_nas_esm_get_pdn_connectivity_procedure()
001355 00200:105842 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0238    Leaving mme_app_nas_esm_get_pdn_connectivity_procedure() (rc=0)
001356 00200:105854 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0300    Entering mme_app_nas_esm_get_bearer_context_procedure()
001357 00200:105865 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0325    Leaving mme_app_nas_esm_get_bearer_context_procedure() (rc=0)
001358 00200:105876 7F81FBFFF700 TRACE MME-AP /mme_app/mme_app_apn_selection.c:0051    Entering mme_app_select_apn()
001359 00200:105892 7F81FBFFF700 INFO  MME-AP /mme_app/mme_app_apn_selection.c:0061    No subscription data is received for IMSI 208950000000004. 
001360 00200:105907 7F81FBFFF700 TRACE MME-AP /mme_app/mme_app_apn_selection.c:0062    Leaving mme_app_select_apn() (rc=0)
001361 00200:105918 7F81FBFFF700 DEBUG NAS-ES r-mme/src/nas/esm/sap/esm_recv.c:0345    ESM-SAP   - No ESM procedure for UE 1 exists. Proceeding with handling the new ESM request (pti=45) for PDN connectivity.
001362 00200:105929 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0081    Entering mme_app_nas_esm_create_pdn_connectivity_procedure()
001363 00200:105940 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0130    Leaving mme_app_nas_esm_create_pdn_connectivity_procedure() (rc=140193571016096)
001364 00200:105947 7F81FBFFF700 TRACE NAS-ES me/src/nas/esm/esm_information.c:0105    Entering esm_proc_esm_information_request()
001365 00200:105955 7F81FBFFF700 TRACE NAS-ES me/src/nas/esm/esm_information.c:0082    Entering esm_send_esm_information_request()
001366 00200:105965 7F81FBFFF700 NOTIC NAS-ES me/src/nas/esm/esm_information.c:0097    ESM-SAP   - Send ESM_INFORMATION_REQUEST message (pti=45, ebi=0)
001367 00200:105976 7F81FBFFF700 TRACE NAS-ES me/src/nas/esm/esm_information.c:0098    Leaving esm_send_esm_information_request()
001368 00200:105987 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/esm/nas_esm_proc.c:0084    ESM_TIMER stopped UE 1
001369 00200:106007 7F81FBFFF700 TRACE NAS-ES me/src/nas/esm/esm_information.c:0127    Leaving esm_proc_esm_information_request()
001370 00200:106028 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/sap/esm_recv.c:0379    Leaving esm_recv_pdn_connectivity_request() (rc=-1)
001371 00200:106041 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0282    Entering esm_msg_encode()
001372 00200:106050 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0301    ESM-MSG   - Encoded ESM message header (3)
001373 00200:106062 7F81FBFFF700 TRACE NAS-ES /esm/msg/EsmInformationRequest.c:0052    Entering encode_esm_information_request()
001374 00200:106072 7F81FBFFF700 TRACE NAS-ES /esm/msg/EsmInformationRequest.c:0060    Leaving encode_esm_information_request() (rc=0)
001375 00200:106082 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0429    Leaving esm_msg_encode() (rc=3)
001376 00200:106093 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0447    Entering esm_msg_free()
001377 00200:106104 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0592    Leaving esm_msg_free()
001378 00200:106113 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0447    Entering esm_msg_free()
001379 00200:106123 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0592    Leaving esm_msg_free()
001380 00200:106133 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0949    Leaving _esm_sap_recv()
001381 00200:106143 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0335    Entering lowerlayer_data_req()
001382 00200:106154 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001383 00200:106166 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0670    Entering emm_as_set_security_data()
001384 00200:106175 7F81FBFFF700 INFO  NAS-EM air-mme/src/nas/emm/LowerLayer.c:0688    EPS security context exists is new 0 KSI 2 SQN 0 count 0
001385 00200:106186 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/LowerLayer.c:0690    hex stream knas_int: 3d 40 c1 8e 32 36 d6 3a a0 21 09 07 3a dd 31 2f
001386 00200:106216 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/LowerLayer.c:0692    hex stream knas_enc: 63 ea 72 08 d9 f2 18 14 72 e7 bc 9d cd e2 23 4c
001387 00200:106237 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/LowerLayer.c:0722    EPS security context exists knas_enc
001388 00200:106247 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0734    Leaving emm_as_set_security_data()
001389 00200:106257 7F81FBFFF700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001390 00200:106267 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
001391 00200:106277 7F81FBFFF700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_DATA_REQ (210)
001392 00200:106288 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1095    Entering _emm_as_send()
001393 00200:106297 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1339    Entering _emm_as_data_req()
001394 00200:106306 7F81FBFFF700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1343    EMMAS-SAP - Send AS data transfer request
001395 00200:106317 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0903    Entering _emm_as_set_header()
001396 00200:106327 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0946    Leaving _emm_as_set_header() (rc=140196255358624)
001397 00200:106337 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001398 00200:106348 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1407    Set nas_msg.header.sequence_number -> 1
001399 00200:106358 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1046    Entering _emm_as_encrypt()
001400 00200:106368 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:0138    Entering nas_message_encrypt()
001401 00200:106379 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:0877    Entering _nas_message_header_encode()
001402 00200:106389 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:0913    Leaving _nas_message_header_encode() (rc=6)
001403 00200:106437 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:1241    Entering _nas_message_encrypt()
001404 00200:106449 7F81FBFFF700 DEBUG NAS    rc/nas/api/network/nas_message.c:1341    NAS_SECURITY_ALGORITHMS_EEA0 dir 1 ul_count.seq_num 0 dl_count.seq_num 1
001405 00200:106461 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:1343    Leaving _nas_message_encrypt() (rc=3)
001406 00200:106472 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:1392    Entering _nas_message_get_mac()
001407 00200:106483 7F81FBFFF700 DEBUG NAS    rc/nas/api/network/nas_message.c:1469    NAS_SECURITY_ALGORITHMS_EIA2 dir DOWNLINK count.seq_num 1 count 1
001408 00200:106496 7F81FBFFF700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0076    Byte length: 12, Zero bits: 0:
001409 00200:106506 7F81FBFFF700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0077    hex stream m: 00 00 00 01 04 00 00 00 01 02 2d d9
001410 00200:106538 7F81FBFFF700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0079    hex stream Key: 3d 40 c1 8e 32 36 d6 3a a0 21 09 07 3a dd 31 2f
001411 00200:106570 7F81FBFFF700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0081    hex stream Message: 01 02 2d d9
001412 00200:106595 7F81FBFFF700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0089    hex stream Out: 7a e7 bf 1a d4 96 2d 0b 16 df 4f 98 d4 51 8d 5b
001413 00200:106629 7F81FBFFF700 DEBUG NAS    rc/nas/api/network/nas_message.c:1485    NAS_SECURITY_ALGORITHMS_EIA2 returned MAC 7a.e7.bf.1a(448784250) for length 4 direction 1, count 1
001414 00200:106645 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:1487    Leaving _nas_message_get_mac() (rc=2062008090)
001415 00200:106664 7F81FBFFF700 DEBUG NAS    rc/nas/api/network/nas_message.c:0210    Incremented emm_security_context.dl_count.seq_num -> 2
001416 00200:106675 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:0229    Leaving nas_message_encrypt() (rc=9)
001417 00200:106687 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1075    Leaving _emm_as_encrypt() (rc=9)
001418 00200:106697 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0483    Entering emm_msg_free()
001419 00200:106708 7F81FBFFF700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0493    EMM-MSG   - Message Type 0x00
001420 00200:106719 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0592    Leaving emm_msg_free()
001421 00200:106731 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1451    Leaving _emm_as_data_req() (rc=263)
001422 00200:106742 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1229    EMMAS-SAP - Sending msg with id 0x107, primitive EMMAS_DATA_REQ (210) to S1AP layer for transmission
001423 00200:106768 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1236    Leaving _emm_as_send() (rc=0)
001424 00200:106775 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
001425 00200:106783 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0361    Leaving lowerlayer_data_req() (rc=0)
001426 00200:106790 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/nas_esm_proc.c:0178    Leaving nas_esm_proc_data_ind() (rc=0)
001427 00200:106794 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0051    Entering mme_app_handle_nas_dl_req()
001428 00200:106817 7F81F9704700 DEBUG MME-AP /src/mme_app/mme_app_transport.c:0064    DOWNLINK NAS TRANSPORT Found enb_ue_s1ap_id 06692d mme_ue_s1ap_id 1
001429 00200:106850 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0095     MME_APP:DOWNLINK NAS TRANSPORT. MME_UE_S1AP_ID 1 and ENB_UE_S1AP_ID 06692d. 
001430 00200:106866 7F81F9704700 TRACE MME-AP /src/mme_app/mme_app_transport.c:0189    Leaving mme_app_handle_nas_dl_req() (rc=0)
001431 00200:106870 7F81F9FFB700 DEBUG S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0452    SEARCHING UE REFERENCE for SCTP association id 1,  enbUeS1apId 06692d and enbId 3584. 
001432 00200:106929 7F81F9FFB700 NOTIC S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0543    Send S1AP DOWNLINK_NAS_TRANSPORT message ue_id = 1 MME_UE_S1AP_ID = 1 eNB_UE_S1AP_ID = 06692d
001433 00200:106981 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0283    [48][1] Sending buffer 0x7f81680026f0 of 35 bytes on stream 1 with ppid 18
001434 00200:107078 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0296    Successfully sent 35 bytes on stream 1
001435 00200:127350 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0547    [1][48] Msg of length 68 received from port 36412, on stream 1, PPID 18
001436 00200:127384 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0554    SCTP RETURNING!!
001437 00200:127432 7F81F9FFB700 INFO  S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0295    Received S1AP UPLINK_NAS_TRANSPORT message MME_UE_S1AP_ID 1
001438 00200:127617 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0250    Entering nas_proc_ul_transfer_ind()
001439 00200:127641 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001440 00200:127652 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
001441 00200:127661 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_DATA_IND (211)
001442 00200:127671 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0557    Entering _emm_as_data_ind()
001443 00200:127680 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0565    EMMAS-SAP - Received AS data transfer indication (ue_id=1, delivered=true, length=20)
001444 00200:127700 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001445 00200:127712 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0260    Entering nas_message_decrypt()
001446 00200:127722 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0694    Entering nas_message_header_decode()
001447 00200:127733 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0751    Leaving nas_message_header_decode() (rc=6)
001448 00200:127739 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1392    Entering _nas_message_get_mac()
001449 00200:127746 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1469    NAS_SECURITY_ALGORITHMS_EIA2 dir UPLINK count.seq_num 1 count 1
001450 00200:127758 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0076    Byte length: 23, Zero bits: 0:
001451 00200:127767 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0077    hex stream m: 00 00 00 01 00 00 00 00 01 02 2d da 28 09 03 6f 61 69 04 69 70 76 34
001452 00200:127788 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0079    hex stream Key: 3d 40 c1 8e 32 36 d6 3a a0 21 09 07 3a dd 31 2f
001453 00200:127801 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0081    hex stream Message: 01 02 2d da 28 09 03 6f 61 69 04 69 70 76 34
001454 00200:127819 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0089    hex stream Out: f1 52 b4 e6 e4 86 38 18 20 1d d1 a5 6e 70 55 41
001455 00200:127843 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1485    NAS_SECURITY_ALGORITHMS_EIA2 returned MAC f1.52.b4.e6(3870577393) for length 15 direction 0, count 1
001456 00200:127856 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1487    Leaving _nas_message_get_mac() (rc=4048729318)
001457 00200:127866 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0303    Integrity: MAC Success
001458 00200:127874 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1049    Entering _nas_message_decrypt()
001459 00200:127879 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1175    NAS_SECURITY_ALGORITHMS_EEA0 dir 0 ul_count.seq_num 1 dl_count.seq_num 2
001460 00200:127885 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1183    Leaving _nas_message_decrypt() (rc=2)
001461 00200:127891 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0335    Leaving nas_message_decrypt() (rc=14)
001462 00200:127914 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0673    Leaving _emm_as_data_ind() (rc=0)
001463 00200:127925 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
001464 00200:127935 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0270    Leaving nas_proc_ul_transfer_ind() (rc=0)
001465 00200:127938 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/nas_esm_proc.c:0159    Entering nas_esm_proc_data_ind()
001466 00200:127968 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0573    Entering _esm_sap_recv()
001467 00200:127981 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0117    Entering esm_msg_decode()
001468 00200:127992 7F81FBFFF700 TRACE NAS-ES esm/msg/EsmInformationResponse.c:0036    Entering decode_esm_information_response()
001469 00200:128005 7F81FBFFF700 TRACE NAS-ES esm/msg/EsmInformationResponse.c:0094    Leaving decode_esm_information_response() (rc=11)
001470 00200:128022 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0261    Leaving esm_msg_decode() (rc=14)
001471 00200:128032 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/sap/esm_recv.c:0519    Entering esm_recv_information_response()
001472 00200:128042 7F81FBFFF700 INFO  NAS-ES r-mme/src/nas/esm/sap/esm_recv.c:0524    ESM-SAP   - Received ESM Information response message (ue_id=1, pti=45, ebi=0)
001473 00200:128054 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0216    Entering mme_app_nas_esm_get_pdn_connectivity_procedure()
001474 00200:128065 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0234    Leaving mme_app_nas_esm_get_pdn_connectivity_procedure() (rc=140193571016096)
001475 00200:128075 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0300    Entering mme_app_nas_esm_get_bearer_context_procedure()
001476 00200:128085 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0325    Leaving mme_app_nas_esm_get_bearer_context_procedure() (rc=0)
001477 00200:128095 7F81FBFFF700 DEBUG NAS-ES r-mme/src/nas/esm/sap/esm_recv.c:0601    ESM-SAP   - Found a valid ESM procedure for UE 1. Proceeding with handling the new ESM request (pti=45) for PDN connectivity.
001478 00200:128106 7F81FBFFF700 TRACE NAS-ES me/src/nas/esm/esm_information.c:0135    Entering esm_proc_esm_information_response()
001479 00200:128121 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/esm/nas_esm_proc.c:0084    ESM_TIMER stopped UE 1
001480 00200:128132 7F81FBFFF700 TRACE NAS-ES me/src/nas/esm/esm_information.c:0182    Leaving esm_proc_esm_information_response()
001481 00200:128142 7F81FBFFF700 TRACE MME-AP /mme_app/mme_app_apn_selection.c:0051    Entering mme_app_select_apn()
001482 00200:128152 7F81FBFFF700 INFO  MME-AP /mme_app/mme_app_apn_selection.c:0061    No subscription data is received for IMSI 208950000000004. 
001483 00200:128161 7F81FBFFF700 TRACE MME-AP /mme_app/mme_app_apn_selection.c:0062    Leaving mme_app_select_apn() (rc=0)
001484 00200:128170 7F81FBFFF700 INFO  NAS-ES r-mme/src/nas/esm/sap/esm_recv.c:0629    ESM-SAP   - Getting subscription profile for IMSI 208950000000004. (ue_id=1, pti=45)
001485 00200:128182 7F81FBFFF700 TRACE NAS    mme/src/nas/nas_itti_messaging.c:0356    Entering nas_itti_pdn_config_req()
001486 00200:128214 7F81FBFFF700 TRACE MME-AP mme/src/nas/nas_itti_messaging.c:0383    Leaving nas_itti_pdn_config_req() (rc=0)
001487 00200:128224 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/sap/esm_recv.c:0637    Leaving esm_recv_information_response() (rc=-1)
001488 00200:128235 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0447    Entering esm_msg_free()
001489 00200:128245 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0592    Leaving esm_msg_free()
001490 00200:128254 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0447    Entering esm_msg_free()
001491 00200:128263 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0592    Leaving esm_msg_free()
001492 00200:128272 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0949    Leaving _esm_sap_recv()
001493 00200:128338 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/nas_esm_proc.c:0178    Leaving nas_esm_proc_data_ind() (rc=0)
001494 00200:128407 7F81A2FFD700 DEBUG S6A    openair-mme/src/s6a/s6a_up_loc.c:0310    Sending s6a ulr for imsi=208950000000004
001495 00200:134096 7F81F0FF9700 DEBUG S6A    openair-mme/src/s6a/s6a_up_loc.c:0059    Received s6a ula for imsi=208950000000004
001496 00200:134165 7F81F0FF9700 DEBUG S6A    /src/s6a/s6a_subscription_data.c:0469    AVP code 1446 Regional-Subscription-Zone=Code not processed
001497 00200:134176 7F81F0FF9700 DEBUG S6A    /src/s6a/s6a_subscription_data.c:0469    AVP code 1446 Regional-Subscription-Zone=Code not processed
001498 00200:134184 7F81F0FF9700 DEBUG S6A    /src/s6a/s6a_subscription_data.c:0469    AVP code 1446 Regional-Subscription-Zone=Code not processed
001499 00200:134191 7F81F0FF9700 DEBUG S6A    /src/s6a/s6a_subscription_data.c:0469    AVP code 1446 Regional-Subscription-Zone=Code not processed
001500 00200:134198 7F81F0FF9700 DEBUG S6A    /src/s6a/s6a_subscription_data.c:0469    AVP code 1446 Regional-Subscription-Zone=Code not processed
001501 00200:134205 7F81F0FF9700 DEBUG S6A    /src/s6a/s6a_subscription_data.c:0469    AVP code 1446 Regional-Subscription-Zone=Code not processed
001502 00200:134212 7F81F0FF9700 DEBUG S6A    /src/s6a/s6a_subscription_data.c:0469    AVP code 1446 Regional-Subscription-Zone=Code not processed
001503 00200:134218 7F81F0FF9700 DEBUG S6A    /src/s6a/s6a_subscription_data.c:0469    AVP code 1446 Regional-Subscription-Zone=Code not processed
001504 00200:134225 7F81F0FF9700 DEBUG S6A    /src/s6a/s6a_subscription_data.c:0469    AVP code 1446 Regional-Subscription-Zone=Code not processed
001505 00200:134232 7F81F0FF9700 DEBUG S6A    /src/s6a/s6a_subscription_data.c:0469    AVP code 1446 Regional-Subscription-Zone=Code not processed
001506 00200:134303 7F81F0FF9700 DEBUG S6A    openair-mme/src/s6a/s6a_up_loc.c:0178    Sending S6A_UPDATE_LOCATION_ANS to task MME_APP
001507 00200:134332 7F81F9704700 TRACE MME-AP e/src/mme_app/mme_app_location.c:0049    Entering mme_app_handle_s6a_update_location_ans()
001508 00200:134356 7F81F9704700 DEBUG MME-AP e/src/mme_app/mme_app_location.c:0060    mme_app_handle_s6a_update_location_ans Handling imsi 208950000000004
001509 00200:134373 7F81F9704700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001510 00200:134386 7F81F9704700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0896    EMM-CTX - get UE id 1 context 0x7f81680011b0 by imsi 208950000000004
001511 00200:134414 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0975    Entering mme_remove_subscription_profile()
001512 00200:134429 7F81F9704700 WARNI MME-AP me/src/mme_app/mme_app_context.c:0983    No subscription data was found for IMSI 208950000000004 in the subscription profile cache.001513 00200:134437 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0984    Leaving mme_remove_subscription_profile() (rc=0)
001514 00200:134445 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0932    Entering mme_insert_subscription_profile()
001515 00200:134466 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0958    Leaving mme_insert_subscription_profile() (rc=0)
001516 00200:134477 7F81F9704700 INFO  MME-AP e/src/mme_app/mme_app_location.c:0096    Updated the subscription profile for IMSI 208950000000004 in the cache. 
001517 00200:134485 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0997    Entering mme_app_update_ue_subscription()
001518 00200:134495 7F81F9704700 TRACE MME-AP me/src/mme_app/mme_app_context.c:1062    Leaving mme_app_update_ue_subscription() (rc=0)
001519 00200:134517 7F81F9704700 TRACE MME-AP e/src/mme_app/mme_app_location.c:0147    Leaving mme_app_handle_s6a_update_location_ans() (rc=0)
001520 00200:134538 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/nas_esm_proc.c:0205    Entering nas_esm_proc_pdn_config_res()
001521 00200:134561 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0137    Entering esm_sap_signal()
001522 00200:134571 7F81FBFFF700 INFO  NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0152    ESM-SAP   - Received primitive ESM_PDN_CONFIG_RES (1)
001523 00200:134580 7F81FBFFF700 TRACE NAS-ES me/src/nas/esm/PdnConnectivity.c:0557    Entering esm_proc_pdn_config_res()
001524 00200:134588 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0216    Entering mme_app_nas_esm_get_pdn_connectivity_procedure()
001525 00200:134598 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0234    Leaving mme_app_nas_esm_get_pdn_connectivity_procedure() (rc=140193571016096)
001526 00200:134607 7F81FBFFF700 TRACE MME-AP /mme_app/mme_app_apn_selection.c:0051    Entering mme_app_select_apn()
001527 00200:134617 7F81FBFFF700 DEBUG MME-AP /mme_app/mme_app_apn_selection.c:0101    Selected APN oai.ipv4 for UE 208950000000004
001528 00200:134636 7F81FBFFF700 TRACE MME-AP /mme_app/mme_app_apn_selection.c:0104    Leaving mme_app_select_apn() (rc=0)
001529 00200:134645 7F81FBFFF700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0062    Entering mme_app_get_pdn_context()
001530 00200:134654 7F81FBFFF700 WARNI MME-AP rc/mme_app/mme_app_pdn_context.c:0100    No PDN context for (ebi=0,cid=100,apn="oai.ipv4") was found for UE: 1. 
001531 00200:134666 7F81FBFFF700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0101    Leaving mme_app_get_pdn_context()
001532 00200:134674 7F81FBFFF700 TRACE NAS-ES me/src/nas/esm/PdnConnectivity.c:0213    Entering esm_proc_pdn_connectivity_request()
001533 00200:134682 7F81FBFFF700 INFO  NAS-ES me/src/nas/esm/PdnConnectivity.c:0221    ESM-PROC  - PDN connectivity requested by the UE (ue_id=1, pti=45) PDN type = (1), APN = oai.ipv4 
001534 00200:134694 7F81FBFFF700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0110    Entering mme_app_esm_create_pdn_context()
001535 00200:134702 7F81FBFFF700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0062    Entering mme_app_get_pdn_context()
001536 00200:134712 7F81FBFFF700 WARNI MME-AP rc/mme_app/mme_app_pdn_context.c:0100    No PDN context for (ebi=0,cid=0,apn="oai.ipv4") was found for UE: 1. 
001537 00200:134721 7F81FBFFF700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0101    Leaving mme_app_get_pdn_context()
001538 00200:134729 7F81FBFFF700 INFO  MME-AP rc/mme_app/mme_app_pdn_context.c:0217    Received first default bearer context 0x5570b5af3894 with ebi 5 for apn "oai.ipv4" of UE: 1. 
001539 00200:134745 7F81FBFFF700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0308    Leaving mme_app_esm_create_pdn_context() (rc=0)
001540 00200:134754 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_itti_messaging.c:0237    Entering mme_app_send_s11_create_session_req()
001541 00200:134763 7F81FBFFF700 DEBUG MME-AP mme_app/mme_app_itti_messaging.c:0274    Sending CSR for imsi 208950000000004
001542 00200:134790 7F81FBFFF700 DEBUG MME-AP /mme_app/mme_app_wrr_selection.c:0095    Service lookup tac-lb01.tac-hb00.tac.epc.mnc095.mcc208.3gppnetwork.org returned 192.168.61.196
001543 00200:134803 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_bearer_context.c:0143    Entering mme_app_get_bearer_contexts_to_be_created()
001544 00200:134822 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_bearer_context.c:0220    Leaving mme_app_get_bearer_contexts_to_be_created()
001545 00200:134830 7F81FBFFF700 DEBUG MME-AP mme_app/mme_app_itti_messaging.c:0443    Sending CSR for imsi (2) 208950000000004
001546 00200:134852 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_itti_messaging.c:0445    Leaving mme_app_send_s11_create_session_req() (rc=0)
001547 00200:134861 7F81FBFFF700 TRACE NAS-ES me/src/nas/esm/PdnConnectivity.c:0269    Leaving esm_proc_pdn_connectivity_request() (rc=-1)
001548 00200:134869 7F81FBFFF700 TRACE NAS-EM me/src/nas/esm/PdnConnectivity.c:0709    Leaving esm_proc_pdn_config_res() (rc=-1)
001549 00200:134878 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0447    Entering esm_msg_free()
001550 00200:134886 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0592    Leaving esm_msg_free()
001551 00200:134894 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0534    Leaving esm_sap_signal()
001552 00200:134901 7F81FBFFF700 WARNI MME-AP r-mme/src/nas/esm/nas_esm_proc.c:0233    No ESM data received and no attach/tau signaled for UE 1.
001553 00200:134909 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/nas_esm_proc.c:0237    Leaving nas_esm_proc_pdn_config_res() (rc=0)
001554 00200:134915 7F81FA7FC700 TRACE S11    rc/s11/s11_mme_session_manager.c:0060    Entering s11_mme_create_session_request()
001555 00200:134941 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0079    ALLOCATED NEW MESSAGE 0x7f8160000d50!
001556 00200:134958 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0092    Created message 0x7f8160000d50!
001557 00200:134979 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2028    Entering nwGtpv2cProcessUlpReq()
001558 00200:134988 7F81FA7FC700 DEBUG GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2032    Received initial request from ulp
001559 00200:134996 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:0691    Entering nwGtpv2cHandleUlpInitialReq()
001560 00200:135004 7F81FA7FC700 DEBUG GTPv2- nwgtpv2c-0.11/src/NwGtpv2cTrxn.c:0248    Created not trx without seqNum as transaction 0x7f81600041c0. Head (nil), Next 0x5570b568c7a2
001561 00200:135022 7F81FA7FC700 DEBUG GTPv2- nwgtpv2c-0.11/src/NwGtpv2cTrxn.c:0264    Created transaction 0x7f81600041c0
001562 00200:135030 7F81FA7FC700 WARNI GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:0714    Request message received on non-existent teid 0x1000000 received! Creating new tunnel.
001563 00200:135049 7F81FA7FC700 DEBUG GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:0606    Creating local tunnel with teid '0x1' and peer IPv4 192.168.61.196
001564 00200:135057 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:0615    Entering nwGtpv2cCreateLocalTunnel()
001565 00200:135067 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:0637    Leaving nwGtpv2cCreateLocalTunnel() (rc=0)
001566 00200:135090 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2229    Entering nwGtpv2cStartTimer()
001568 00200:135110 7F81FA7FC700 DEBUG GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2294    Started timer 0x7f81600041a0 for info 0x0x7f81600042e0!
001569 00200:135125 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2300    Leaving nwGtpv2cStartTimer() (rc=0)
001567 00200:135107 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0077    Looking for task 9
001570 00200:135135 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:0770    Leaving nwGtpv2cHandleUlpInitialReq() (rc=0)
001571 00200:135141 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0093    Found matching port with high port 46468. 
001572 00200:135144 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2074    Leaving nwGtpv2cProcessUlpReq() (rc=0)
001573 00200:135151 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0446    [39] Sending message of size 162 to 192.168.61.196 and port 2123
001574 00200:135156 7F81FA7FC700 TRACE S11    rc/s11/s11_mme_session_manager.c:0175    Leaving s11_mme_create_session_request() (rc=0)
001575 00200:135319 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0122    Received 1 events
001576 00200:137371 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0122    Received 1 events
001577 00200:137378 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0108    Looking for sd 39
001578 00200:137382 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0147    Inserting new descriptor for task 9, sd 39
001579 00200:137395 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0192    Msg of length 97 received from 192.168.61.196:2123
001580 00200:137409 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:1874    Entering nwGtpv2cProcessUdpReq()
001581 00200:137415 7F81FA7FC700 DEBUG GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:1468    RECEIVED GTPV2c  response message of type 33, length 97 and seqNum 8690.
001582 00200:137418 7F81FA7FC700 DEBUG GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:1492    Not removing the initial request transaction for message type 33, seqNo 8690 (altough remove flag set). 
001583 00200:137423 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0132    Created message 0x7f81600043a0!
001584 00200:137430 7F81FA7FC700 DEBUG GTPv2- .11/src/NwGtpv2cMsgIeParseInfo.c:1314    Received IE 2 with instance 0 of length 2 in msg-type 33!
001585 00200:137433 7F81FA7FC700 DEBUG GTPv2- .11/src/NwGtpv2cMsgIeParseInfo.c:1314    Received IE 87 with instance 0 of length 9 in msg-type 33!
001586 00200:137436 7F81FA7FC700 DEBUG GTPv2- .11/src/NwGtpv2cMsgIeParseInfo.c:1314    Received IE 79 with instance 0 of length 5 in msg-type 33!
001587 00200:137441 7F81FA7FC700 DEBUG GTPv2- .11/src/NwGtpv2cMsgIeParseInfo.c:1314    Received IE 72 with instance 0 of length 8 in msg-type 33!
001588 00200:137444 7F81FA7FC700 WARNI GTPv2- .11/src/NwGtpv2cMsgIeParseInfo.c:1389    Unexpected IE 72 with instance 0 of length 8 received in msg 33!
001589 00200:137448 7F81FA7FC700 DEBUG GTPv2- .11/src/NwGtpv2cMsgIeParseInfo.c:1314    Received IE 78 with instance 0 of length 13 in msg-type 33!
001590 00200:137451 7F81FA7FC700 DEBUG GTPv2- .11/src/NwGtpv2cMsgIeParseInfo.c:1314    Received IE 93 with instance 0 of length 24 in msg-type 33!
001591 00200:137455 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:1140    Entering nwGtpv2cSendTriggeredRspIndToUlp()
001592 00200:137480 7F81FA7FC700 DEBUG GTPv2- v2c-0.11/src/NwGtpv2cMsgParser.c:0211    Received IE 2 of length 2!
001593 00200:137488 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0153    	- Cause value 16
001594 00200:137491 7F81FA7FC700 DEBUG GTPv2- v2c-0.11/src/NwGtpv2cMsgParser.c:0211    Received IE 87 of length 9!
001595 00200:137495 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0232    	- F-TEID type 11
001596 00200:137498 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0237    	- TEID/GRE    00000001
001597 00200:137501 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0249    	- IPv4 addr   192.168.61.196
001598 00200:137506 7F81FA7FC700 DEBUG GTPv2- v2c-0.11/src/NwGtpv2cMsgParser.c:0211    Received IE 79 of length 5!
001599 00200:137509 7F81FA7FC700 DEBUG S11    matter/src/gtpv2c_ie_formatter.c:0276    	- PAA type  1
001600 00200:137513 7F81FA7FC700 DEBUG S11    matter/src/gtpv2c_ie_formatter.c:0309    	- IPv4 addr 12.1.1.2
001601 00200:137516 7F81FA7FC700 DEBUG GTPv2- v2c-0.11/src/NwGtpv2cMsgParser.c:0211    Received IE 72 of length 8!
001602 00200:137519 7F81FA7FC700 DEBUG S11    matter/src/gtpv2c_ie_formatter.c:0416    	- AMBR UL 50000000
001603 00200:137522 7F81FA7FC700 DEBUG S11    matter/src/gtpv2c_ie_formatter.c:0417    	- AMBR DL 100000000
001604 00200:137525 7F81FA7FC700 DEBUG GTPv2- v2c-0.11/src/NwGtpv2cMsgParser.c:0211    Received IE 78 of length 13!
001605 00200:137529 7F81FA7FC700 DEBUG GTPv2- v2c-0.11/src/NwGtpv2cMsgParser.c:0211    Received IE 93 of length 24!
001606 00200:137533 7F81FA7FC700 DEBUG S11    matter/src/gtpv2c_ie_formatter.c:0374    	- EBI 5
001607 00200:137536 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0153    	- Cause value 16
001608 00200:137543 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0232    	- F-TEID type 1
001609 00200:137546 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0237    	- TEID/GRE    00000001
001610 00200:137549 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0249    	- IPv4 addr   192.168.61.197
001611 00200:137554 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0144    Purging message 0x7f81600043a0!
001612 00200:137557 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0149    Message pool 7f81600043a0! Next element 0! 
001613 00200:137565 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:1154    Leaving nwGtpv2cSendTriggeredRspIndToUlp() (rc=0)
001614 00200:137570 7F81FA7FC700 WARNI GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:1535    Removing the initial request transaction for message type 33, seqNo 8690 in conclusion (not late response). 
001615 00200:137575 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2392    Entering nwGtpv2cStopTimer()
001616 00200:137580 7F81FA7FC700 DEBUG GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2406    Stopping active timer 0x7f81600041a0 for info 0x0x7f81600042e0!
001617 00200:137587 7F81FA7FC700 INFO  GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2418    Stopped active timer 0x7f81600041a0 for info 0x0x7f81600042e0!
001618 00200:137591 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2445    Leaving nwGtpv2cStopTimer() (rc=0)
001619 00200:137595 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0144    Purging message 0x7f8160000d50!
001620 00200:137598 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0149    Message pool 7f8160000d50! Next element 7f81600043a0! 
001621 00200:137601 7F81FA7FC700 DEBUG GTPv2- nwgtpv2c-0.11/src/NwGtpv2cTrxn.c:0422    Purging  transaction 0x7f81600041c0 with seqNum 34448. (before) Head (nil), Next (nil). 
001622 00200:137605 7F81FA7FC700 DEBUG GTPv2- nwgtpv2c-0.11/src/NwGtpv2cTrxn.c:0429    After purging  transaction 0x7f81600041c0, Head 0x7f81600041c0, Next (nil)
001623 00200:137609 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2014    Leaving nwGtpv2cProcessUdpReq() (rc=0)
001624 00200:137628 7F81F9704700 TRACE MME-AP mme/src/mme_app/mme_app_bearer.c:1783    Entering mme_app_handle_create_sess_resp()
001625 00200:137637 7F81F9704700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001626 00200:137641 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0374    Entering mme_app_pdn_process_session_creation()
001627 00200:137649 7F81F9704700 DEBUG MME-AP me_app/mme_app_session_context.c:0638    Received new valid APN_AMBR for APN "oai.ipv4" (ctx_id=0) for UE 1. Updating APN ambr. 
001628 00200:137654 7F81F9704700 INFO  MME-AP me_app/mme_app_session_context.c:0736    Processed all 1 bearer contexts for APN "oai.ipv4" for ue_id 1. 
001629 00200:137659 7F81F9704700 TRACE MME-AP me_app/mme_app_session_context.c:0737    Leaving mme_app_pdn_process_session_creation() (rc=0)
001630 00200:137664 7F81F9704700 TRACE MME-AP mme_app/mme_app_itti_messaging.c:1264    Entering mme_app_itti_nas_pdn_connectivity_response()
001631 00200:137668 7F81F9704700 INFO  MME-AP mme_app/mme_app_itti_messaging.c:1271    Informing the NAS layer about the received CREATE_SESSION_RESPONSE for UE 1. 
001632 00200:137676 7F81F9704700 TRACE MME-AP mme_app/mme_app_itti_messaging.c:1288    Leaving mme_app_itti_nas_pdn_connectivity_response()
001633 00200:137680 7F81F9704700 TRACE MME-AP mme/src/mme_app/mme_app_bearer.c:1867    Leaving mme_app_handle_create_sess_resp() (rc=0)
001634 00200:137690 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/nas_esm_proc.c:0278    Entering nas_esm_proc_pdn_connectivity_res()
001635 00200:137695 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0137    Entering esm_sap_signal()
001636 00200:137699 7F81FBFFF700 INFO  NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0152    ESM-SAP   - Received primitive ESM_PDN_CONNECTIVITY_CNF (3)
001637 00200:137705 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0216    Entering mme_app_nas_esm_get_pdn_connectivity_procedure()
001638 00200:137708 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0234    Leaving mme_app_nas_esm_get_pdn_connectivity_procedure() (rc=140193571016096)
001639 00200:137712 7F81FBFFF700 TRACE NAS-ES me/src/nas/esm/PdnConnectivity.c:0392    Entering esm_proc_pdn_connectivity_res()
001640 00200:137715 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_bearer_context.c:0385    Entering mme_app_esm_update_ebr_state()
001641 00200:137719 7F81FBFFF700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0062    Entering mme_app_get_pdn_context()
001642 00200:137723 7F81FBFFF700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0082    Leaving mme_app_get_pdn_context()
001643 00200:137728 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_bearer_context.c:0414    Leaving mme_app_esm_update_ebr_state() (rc=0)
001644 00200:137732 7F81FBFFF700 TRACE NAS-ES me/src/nas/esm/PdnConnectivity.c:0422    Leaving esm_proc_pdn_connectivity_res() (rc=-1)
001645 00200:137736 7F81FBFFF700 TRACE NAS-ES aultEpsBearerContextActivation.c:0238    Entering esm_proc_default_eps_bearer_context()
001646 00200:137739 7F81FBFFF700 INFO  NAS-ES aultEpsBearerContextActivation.c:0245    ESM-PROC  - Default EPS bearer context activation (ue_id=1, context_identifier=0, bc_status 0)
001647 00200:137743 7F81FBFFF700 NOTIC NAS    aultEpsBearerContextActivation.c:0246    Hit 3GPP TS 24_301R10_6_4_1_2 : 
001648 00200:137748 7F81FBFFF700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0062    Entering mme_app_get_pdn_context()
001649 00200:137752 7F81FBFFF700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0082    Leaving mme_app_get_pdn_context()
001650 00200:137755 7F81FBFFF700 TRACE NAS-ES aultEpsBearerContextActivation.c:0130    Entering esm_send_activate_default_eps_bearer_context_request()
001651 00200:137759 7F81FBFFF700 INFO  NAS-ES aultEpsBearerContextActivation.c:0160    ESM-SAP   - pdn_type is 1
001652 00200:137765 7F81FBFFF700 INFO  NAS-ES aultEpsBearerContextActivation.c:0207    ESM-SAP   - Send Activate Default EPS Bearer Context Request message (pti=45, ebi=5)
001653 00200:137769 7F81FBFFF700 TRACE NAS-ES aultEpsBearerContextActivation.c:0208    Leaving esm_send_activate_default_eps_bearer_context_request()
001654 00200:137773 7F81FBFFF700 TRACE NAS-ES aultEpsBearerContextActivation.c:0290    Leaving esm_proc_default_eps_bearer_context()
001655 00200:137779 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0282    Entering esm_msg_encode()
001656 00200:137782 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0301    ESM-MSG   - Encoded ESM message header (3)
001657 00200:137798 7F81FBFFF700 INFO  NAS-ES DefaultEpsBearerContextRequest.c:0357    ESM  ENCODED activate_default_eps_bearer_context_request
001658 00200:137803 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0429    Leaving esm_msg_encode() (rc=42)
001659 00200:137806 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0447    Entering esm_msg_free()
001660 00200:137810 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0592    Leaving esm_msg_free()
001661 00200:137813 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0534    Leaving esm_sap_signal()
001662 00200:137817 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_cn.c:0301    Entering _emm_wrapper_esm_accept()
001663 00200:137822 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001664 00200:137825 7F81FBFFF700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1922    Entering _emm_wrapper_attach_accept()
001665 00200:137830 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001666 00200:137833 7F81FBFFF700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:2028    Entering _emm_send_attach_accept()
001667 00200:137838 7F81FBFFF700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:2692    Entering _emm_attach_update()
001668 00200:137841 7F81FBFFF700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:2712    Hit 3GPP TS 24_301R10_5_5_1_2_4__4 : Attach accepted by the network, store UE network capability IE or the MS network capability IE or both.
001669 00200:137846 7F81FBFFF700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0452    ue_id=1 set UE network capability IE (valid)
001670 00200:137849 7F81FBFFF700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0489    ue_id=1 set MS network capability IE (valid)
001671 00200:137854 7F81FBFFF700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:2750    Hit 3GPP TS 24_301R10_5_5_1_2_4__5 : Attach accepted by the network, use DRX parameter for the downlink transfer of signalling and user data
001672 00200:137857 7F81FBFFF700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0510    ue_id=1 set current DRX parameter (present)
001673 00200:137862 7F81FBFFF700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0521    ue_id=1 set current DRX parameter (valid)
001674 00200:137865 7F81FBFFF700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:2754    Leaving _emm_attach_update() (rc=0)
001675 00200:137869 7F81FBFFF700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:2060    #NOT IMPLEMENTED 3GPP TS 24_301R10_5_5_1_2_4__3 : Attach accepted by the network, delete the stored UE radio capability information.
001676 00200:137874 7F81FBFFF700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:2065    Hit 3GPP TS 24_301R10_5_5_1_2_4__9 : 
001677 00200:137877 7F81FBFFF700 TRACE NAS    ir-mme/src/nas/api/mme/mme_api.c:0454    Entering mme_api_new_guti()
001678 00200:137881 7F81FBFFF700 TRACE NAS    ir-mme/src/nas/api/mme/mme_api.c:0416    Entering mme_api_notify_new_guti()
001679 00200:137886 7F81FBFFF700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0325    Entering mme_ue_context_update_coll_keys()
001680 00200:137890 7F81FBFFF700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0334    Update ue context.enb_ue_s1ap_id 06692d ue context.mme_ue_s1ap_id 1 ue context.IMSI 208950000000004 ue context.GUTI 000.000|0000|00|00000000
001681 00200:137896 7F81FBFFF700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0342    Update ue context 0x5570b59e3858 enb_ue_s1ap_id 06692d mme_ue_s1ap_id 1 IMSI 208950000000004 GUTI 208.95 |8000|03|00000001
001682 00200:137904 7F81FBFFF700 TRACE MME-AP me/src/mme_app/mme_app_context.c:0605    Leaving mme_ue_context_update_coll_keys()
001683 00200:137908 7F81FBFFF700 TRACE NAS    ir-mme/src/nas/api/mme/mme_api.c:0428    Leaving mme_api_notify_new_guti() (rc=0)
001684 00200:137911 7F81FBFFF700 INFO  NAS    ir-mme/src/nas/api/mme/mme_api.c:0495    UE 1  with GUTI 208.95 |8000|03|00000001 will only receive its TAC 0x1 in the TAI list to enforce TAU.
001685 00200:137916 7F81FBFFF700 TRACE NAS    ir-mme/src/nas/api/mme/mme_api.c:0520    Leaving mme_api_new_guti() (rc=0)
001686 00200:137920 7F81FBFFF700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0118    ue_id=1 set GUTI 208.95 |8000|03|00000001 (present)
001687 00200:137925 7F81FBFFF700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:2085    Hit 3GPP TS 24_301R10_5_5_1_2_4__6 : 
001688 00200:137927 7F81FBFFF700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:2086    Hit 3GPP TS 24_301R10_5_5_1_2_4__10 : 
001689 00200:137932 7F81FBFFF700 INFO  NAS-EM openair-mme/src/nas/emm/Attach.c:2122    ue_id=1 EMM-PROC  - Include the new assigned GUTI in the Attach Accept message
001690 00200:137936 7F81FBFFF700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:2128    Hit 3GPP TS 24_301R10_5_5_1_2_4__14 : 
001691 00200:137939 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0670    Entering emm_as_set_security_data()
001692 00200:137945 7F81FBFFF700 INFO  NAS-EM air-mme/src/nas/emm/LowerLayer.c:0688    EPS security context exists is new 0 KSI 2 SQN 1 count 16777216
001693 00200:137949 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/LowerLayer.c:0690    hex stream knas_int: 3d 40 c1 8e 32 36 d6 3a a0 21 09 07 3a dd 31 2f
001694 00200:137959 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/LowerLayer.c:0692    hex stream knas_enc: 63 ea 72 08 d9 f2 18 14 72 e7 bc 9d cd e2 23 4c
001695 00200:137968 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/LowerLayer.c:0722    EPS security context exists knas_enc
001696 00200:137971 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/LowerLayer.c:0734    Leaving emm_as_set_security_data()
001697 00200:137975 7F81FBFFF700 DEBUG NAS-EM openair-mme/src/nas/emm/Attach.c:2153    ue_id=1 EMM-PROC  - encryption = 0x0 (0x0)
001698 00200:137978 7F81FBFFF700 DEBUG NAS-EM openair-mme/src/nas/emm/Attach.c:2158    ue_id=1 EMM-PROC  - integrity  = 0x2 (0x2)
001699 00200:137983 7F81FBFFF700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:2169    ue_id=1 EMM-PROC  - nas_msg  src size = 42 nas_msg  dst size = 42 
001700 00200:137986 7F81FBFFF700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:2177    Hit 3GPP TS 24_301R10_5_5_1_2_4__2 : 
001701 00200:137990 7F81FBFFF700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001702 00200:137993 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
001703 00200:137998 7F81FBFFF700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_ESTABLISH_CNF (206)
001704 00200:138001 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1095    Entering _emm_as_send()
001705 00200:138006 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:2074    Entering _emm_as_establish_cnf()
001706 00200:138009 7F81FBFFF700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:2076    EMMAS-SAP - Send AS connection establish confirmation
001707 00200:138012 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001708 00200:138015 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:2110    Set nas_msg.selected_encryption_algorithm -> NBO: 0x0000 (0)
001709 00200:138018 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:2115    Set nas_msg.selected_integrity_algorithm -> NBO: 0x0040 (2)
001710 00200:138022 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:2123    EMMAS-SAP - NAS UL COUNT        0
001711 00200:138027 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0903    Entering _emm_as_set_header()
001712 00200:138030 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0946    Leaving _emm_as_set_header() (rc=140196255356480)
001713 00200:138034 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:2135    EMMAS-SAP - emm_as_establish.nasMSG.length=42
001714 00200:138038 7F81FBFFF700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0227    Entering emm_send_attach_accept()
001715 00200:138042 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001716 00200:138046 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0236    EMMAS-SAP - Send Attach Accept message
001717 00200:138050 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0238    EMMAS-SAP - size = EMM_HEADER_MAXIMUM_LENGTH(2)
001718 00200:138053 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0250    EMMAS-SAP - size += EPS_ATTACH_RESULT_MAXIMUM_LENGTH(1)  (3)
001719 00200:138058 7F81FBFFF700 DEBUG NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0253    EMMAS-SAP - Combined EPS/IMSI attach
001720 00200:138061 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0304    EMMAS-SAP - size += GPRS_TIMER_IE_MAX_LENGTH(2)  (5)
001721 00200:138065 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0315    EMMAS-SAP - size += TRACKING_AREA_IDENTITY_LIST_LENGTH(8*1)  (13)
001722 00200:138069 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0345    EMMAS-SAP - size += ESM_MESSAGE_CONTAINER_MINIMUM_LENGTH(2)  (57)
001723 00200:138073 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0367    EMMAS-SAP - size += EPS_MOBILE_IDENTITY_MAXIMUM_LENGTH(13)  (70)
001724 00200:138077 7F81FBFFF700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_send.c:0386    Leaving emm_send_attach_accept() (rc=70)
001725 00200:138080 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:2177    Set nas_msg.header.sequence_number -> 2
001726 00200:138083 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0987    Entering _emm_as_encode()
001727 00200:138087 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:0561    Entering nas_message_encode()
001728 00200:138090 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:0877    Entering _nas_message_header_encode()
001729 00200:138093 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:0913    Leaving _nas_message_header_encode() (rc=6)
001730 00200:138098 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:0987    Entering _nas_message_protected_encode()
001731 00200:138102 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:0938    Entering _nas_message_plain_encode()
001732 00200:138105 7F81FBFFF700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0295    Entering emm_msg_encode()
001733 00200:138108 7F81FBFFF700 TRACE NAS-EM e/src/nas/emm/msg/AttachAccept.c:0239    Entering encode_attach_accept()
001734 00200:138114 7F81FBFFF700 TRACE NAS-EM e/src/nas/emm/msg/AttachAccept.c:0402    Leaving encode_attach_accept() (rc=66)
001735 00200:138118 7F81FBFFF700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0465    Leaving emm_msg_encode() (rc=68)
001736 00200:138121 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:0963    Leaving _nas_message_plain_encode() (rc=68)
001737 00200:138125 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:1241    Entering _nas_message_encrypt()
001738 00200:138128 7F81FBFFF700 DEBUG NAS    rc/nas/api/network/nas_message.c:1341    NAS_SECURITY_ALGORITHMS_EEA0 dir 1 ul_count.seq_num 1 dl_count.seq_num 2
001739 00200:138131 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:1343    Leaving _nas_message_encrypt() (rc=68)
001740 00200:138135 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:1016    Leaving _nas_message_protected_encode() (rc=68)
001741 00200:138140 7F81FBFFF700 DEBUG NAS    rc/nas/api/network/nas_message.c:0596    offset 5 = 6 - 1, hdr encode = 6, length = 76 bytes = 68
001742 00200:138143 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:1392    Entering _nas_message_get_mac()
001743 00200:138147 7F81FBFFF700 DEBUG NAS    rc/nas/api/network/nas_message.c:1469    NAS_SECURITY_ALGORITHMS_EIA2 dir DOWNLINK count.seq_num 2 count 2
001744 00200:138151 7F81FBFFF700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0076    Byte length: 77, Zero bits: 0:
001745 00200:138156 7F81FBFFF700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0077    hex stream m: 00 00 00 02 04 00 00 00 02 07 42 02 21 06 20 02 f8 59 00 01 00 2a 52 2d c1 01 09 09 03 6f 61 69 04 69 70 76 34 05 01 0c 01 01 02 5e 04 fe fe 9e 6c 27 0d 80 00 0d 04 c1 33 c4 8a 00 10 02 05 4e 50 0b f6 02 f8 59 80 00 03 00 00 00 01
001746 00200:138187 7F81FBFFF700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0079    hex stream Key: 3d 40 c1 8e 32 36 d6 3a a0 21 09 07 3a dd 31 2f
001747 00200:138195 7F81FBFFF700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0081    hex stream Message: 02 07 42 02 21 06 20 02 f8 59 00 01 00 2a 52 2d c1 01 09 09 03 6f 61 69 04 69 70 76 34 05 01 0c 01 01 02 5e 04 fe fe 9e 6c 27 0d 80 00 0d 04 c1 33 c4 8a 00 10 02 05 4e 50 0b f6 02 f8 59 80 00 03 00 00 00 01
001748 00200:138227 7F81FBFFF700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0089    hex stream Out: 5b cd a7 b5 24 c1 80 cf eb 4f 74 78 d8 9b 17 62
001749 00200:138235 7F81FBFFF700 DEBUG NAS    rc/nas/api/network/nas_message.c:1485    NAS_SECURITY_ALGORITHMS_EIA2 returned MAC 5b.cd.a7.b5(3047673179) for length 69 direction 1, count 2
001750 00200:138239 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:1487    Leaving _nas_message_get_mac() (rc=1540204469)
001751 00200:138243 7F81FBFFF700 DEBUG NAS    rc/nas/api/network/nas_message.c:0627    Incremented emm_security_context.dl_count.seq_num -> 3
001752 00200:138246 7F81FBFFF700 TRACE NAS    rc/nas/api/network/nas_message.c:0653    Leaving nas_message_encode() (rc=74)
001753 00200:138249 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1023    Leaving _emm_as_encode() (rc=74)
001754 00200:138252 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0483    Entering emm_msg_free()
001755 00200:138255 7F81FBFFF700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0493    EMM-MSG   - Message Type 0x42
001756 00200:138258 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0592    Leaving emm_msg_free()
001757 00200:138261 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:2196    Leaving _emm_as_establish_cnf() (rc=2052)
001758 00200:138265 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1229    EMMAS-SAP - Sending msg with id 0x804, primitive EMMAS_ESTABLISH_CNF (206) to S1AP layer for transmission
001759 00200:138271 7F81FBFFF700 DEBUG NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1291    EMMAS-SAP - Sending nas_itti_establish_cnf to S1AP UE ID 0x1 sea 0x0000 sia 0x0040, uplink count 0
001760 00200:138274 7F81FBFFF700 TRACE NAS    mme/src/nas/nas_itti_messaging.c:0571    Entering nas_itti_establish_cnf()
001761 00200:138277 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001762 00200:138281 7F81FBFFF700 DEBUG NAS-EM mme/src/nas/nas_itti_messaging.c:0616    EMM-PROC  - KeNB with UL Count 0 for UE 1. 
001763 00200:138291 7F81FBFFF700 DEBUG NAS    mme/src/nas/nas_itti_messaging.c:0627    hex stream KENB:  d4 18 fa 6d 1e 24 c7 fa 32 a5 72 98 bd 83 fa a8 84 53 e6 bc 61 03 6b 6f b7 0b e0 5f 05 a4 76 07
001764 00200:138304 7F81FBFFF700 DEBUG NAS-EM mme/src/nas/nas_itti_messaging.c:0636    EMM-PROC  - NH value is 0 as expected. Setting kEnb as NH0  
001765 00200:138307 7F81FBFFF700 DEBUG NAS    mme/src/nas/nas_itti_messaging.c:0647    hex stream New NH_CONJ of emmCtx:  d4 18 fa 6d 1e 24 c7 fa 32 a5 72 98 bd 83 fa a8 84 53 e6 bc 61 03 6b 6f b7 0b e0 5f 05 a4 76 07
001766 00200:138325 7F81FBFFF700 TRACE NAS    mme/src/nas/nas_itti_messaging.c:0672    Leaving nas_itti_establish_cnf()
001767 00200:138328 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:1302    Leaving _emm_as_send() (rc=0)
001768 00200:138331 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
001769 00200:138335 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001770 00200:138343 7F81FBFFF700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1303    T3450 started UE 1
001771 00200:138347 7F81FBFFF700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001772 00200:138350 7F81FBFFF700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0104    Entering emm_reg_send()
001773 00200:138353 7F81FBFFF700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0274    Entering emm_fsm_process()
001774 00200:138356 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001775 00200:138359 7F81FBFFF700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0282    EMM-FSM   - Received event COMMON_PROC_REQ (1) in state EMM-DEREGISTERED
001776 00200:138363 7F81FBFFF700 TRACE NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0097    Entering EmmDeregistered()
001777 00200:138366 7F81FBFFF700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001778 00200:138369 7F81FBFFF700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0176    Entering emm_fsm_set_state()
001779 00200:138372 7F81FBFFF700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0185    UE 1 EMM-FSM   - Status changed: EMM-DEREGISTERED ===> EMM-COMMON-PROCEDURE-INITIATED
001780 00200:138375 7F81FBFFF700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2251    Entering mme_ue_context_update_ue_emm_state()
001781 00200:138378 7F81FBFFF700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2276    Leaving mme_ue_context_update_ue_emm_state()
001782 00200:138381 7F81FBFFF700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0213    Leaving emm_fsm_set_state() (rc=0)
001783 00200:138384 7F81FBFFF700 TRACE NAS-EM rc/nas/emm/sap/EmmDeregistered.c:0424    Leaving EmmDeregistered() (rc=0)
001784 00200:138387 7F81FBFFF700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0293    Leaving emm_fsm_process() (rc=0)
001785 00200:138390 7F81FBFFF700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0117    Leaving emm_reg_send() (rc=0)
001786 00200:138402 7F81FBFFF700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:2226    Leaving _emm_send_attach_accept() (rc=0)
001787 00200:138405 7F81FBFFF700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:1972    Leaving _emm_wrapper_attach_accept() (rc=0)
001788 00200:138408 7F81FBFFF700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_cn.c:0319    Leaving _emm_wrapper_esm_accept() (rc=0)
001789 00200:138411 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/nas_esm_proc.c:0316    Leaving nas_esm_proc_pdn_connectivity_res() (rc=0)
001790 00200:138424 7F81F9704700 TRACE MME-AP mme/src/mme_app/mme_app_bearer.c:0265    Entering mme_app_handle_conn_est_cnf()
001791 00200:138427 7F81F9704700 DEBUG MME-AP mme/src/mme_app/mme_app_bearer.c:0272    Received NAS_CONNECTION_ESTABLISHMENT_CNF from NAS
001792 00200:138431 7F81F9704700 DEBUG MME-AP mme/src/mme_app/mme_app_bearer.c:0320    security_capabilities_encryption_algorithms 0x00E0
001793 00200:138434 7F81F9704700 DEBUG MME-AP mme/src/mme_app/mme_app_bearer.c:0323    security_capabilities_integrity_algorithms  0x00E0
001794 00200:138445 7F81F9704700 DEBUG MME-AP mme/src/mme_app/mme_app_bearer.c:0499    MME APP : Sent Initial context Setup Request and Started guard timer for UE id  1 
001795 00200:138449 7F81F9704700 TRACE MME-AP mme/src/mme_app/mme_app_bearer.c:0501    Leaving mme_app_handle_conn_est_cnf()
001796 00200:138517 7F81F9FFB700 DEBUG S1AP   c/s1ap/s1ap_mme_nas_procedures.c:1360    security_capabilities_encryption_algorithms 0x00E0
001797 00200:138523 7F81F9FFB700 DEBUG S1AP   c/s1ap/s1ap_mme_nas_procedures.c:1371    security_capabilities_integrity_algorithms 0x00E0
001798 00200:138567 7F81F9FFB700 NOTIC S1AP   c/s1ap/s1ap_mme_nas_procedures.c:1435    Send S1AP_INITIAL_CONTEXT_SETUP_REQUEST message MME_UE_S1AP_ID = 1 eNB_UE_S1AP_ID = 06692d
001799 00200:138586 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0283    [48][1] Sending buffer 0x7f8170000b80 of 179 bytes on stream 1 with ppid 18
001800 00200:138624 7F81FB7FE700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0296    Successfully sent 179 bytes on stream 1
001801 00200:177439 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0547    [1][48] Msg of length 75 received from port 36412, on stream 1, PPID 18
001802 00200:177461 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0554    SCTP RETURNING!!
001803 00200:177597 7F81F9704700 TRACE MME-AP c/mme_app/mme_app_capabilities.c:0043    Entering mme_app_handle_s1ap_ue_capabilities_ind()
001804 00200:177611 7F81F9704700 DEBUG MME-AP c/mme_app/mme_app_capabilities.c:0069    UE radio capabilities of length 49 found and cached
001805 00200:177616 7F81F9704700 TRACE MME-AP c/mme_app/mme_app_capabilities.c:0072    Leaving mme_app_handle_s1ap_ue_capabilities_ind() (rc=0)
001806 00200:378786 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0547    [1][48] Msg of length 40 received from port 36412, on stream 1, PPID 18
001807 00200:378811 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0554    SCTP RETURNING!!
001808 00200:378825 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0547    [1][48] Msg of length 61 received from port 36412, on stream 1, PPID 18
001809 00200:378837 7F81A17FA700 DEBUG SCTP   rc/sctp/sctp_primitives_server.c:0554    SCTP RETURNING!!
001810 00200:378974 7F81F9FFB700 DEBUG S1AP   mme/src/s1ap/s1ap_mme_handlers.c:0871    S1AP_FIND_PROTOCOLIE_BY_ID: /openair-mme/src/s1ap/s1ap_mme_handlers.c 871: Optional ie is NULL
001811 00200:379028 7F81F9704700 TRACE MME-AP mme/src/mme_app/mme_app_bearer.c:2634    Entering mme_app_handle_initial_context_setup_rsp()
001812 00200:379044 7F81F9FFB700 INFO  S1AP   c/s1ap/s1ap_mme_nas_procedures.c:0295    Received S1AP UPLINK_NAS_TRANSPORT message MME_UE_S1AP_ID 1
001813 00200:379054 7F81F9704700 DEBUG MME-AP mme/src/mme_app/mme_app_bearer.c:2640    Received MME_APP_INITIAL_CONTEXT_SETUP_RSP from S1AP
001814 00200:379067 7F81F9704700 TRACE MME-AP mme_app/mme_app_bearer_context.c:0555    Entering mme_app_release_bearers()
001815 00200:379077 7F81F9704700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0300    Entering mme_app_nas_esm_get_bearer_context_procedure()
001816 00200:379084 7F81F9704700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0325    Leaving mme_app_nas_esm_get_bearer_context_procedure() (rc=0)
001817 00200:379089 7F81F9704700 INFO  MME-AP mme_app/mme_app_bearer_context.c:0658    Returning 0 bearer ready to be released for ue_id 1. 
001818 00200:379097 7F81F9704700 TRACE MME-AP mme_app/mme_app_bearer_context.c:0659    Leaving mme_app_release_bearers()
001819 00200:379105 7F81F9704700 TRACE MME-AP mme_app/mme_app_bearer_context.c:0422    Entering mme_app_modify_bearers()
001820 00200:379114 7F81F9704700 TRACE MME-AP mme_app/mme_app_bearer_context.c:0486    Leaving mme_app_modify_bearers() (rc=0)
001821 00200:379138 7F81F9704700 TRACE MME-AP mme_app/mme_app_itti_messaging.c:0452    Entering mme_app_send_s11_modify_bearer_req()
001822 00200:379147 7F81F9704700 DEBUG MME-AP mme_app/mme_app_itti_messaging.c:0511    Adding EBI 5 as bearer context to be modified for UE 1. 
001823 00200:379166 7F81F9704700 TRACE MME-AP mme_app/mme_app_itti_messaging.c:0598    Leaving mme_app_send_s11_modify_bearer_req()
001824 00200:379189 7F81F9704700 TRACE MME-AP mme/src/mme_app/mme_app_bearer.c:2741    Leaving mme_app_handle_initial_context_setup_rsp()
001825 00200:379201 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0092    Created message 0x7f8160000d50!
001826 00200:379237 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2028    Entering nwGtpv2cProcessUlpReq()
001827 00200:379251 7F81FA7FC700 DEBUG GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2032    Received initial request from ulp
001828 00200:379257 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:0691    Entering nwGtpv2cHandleUlpInitialReq()
001829 00200:379262 7F81FA7FC700 DEBUG GTPv2- nwgtpv2c-0.11/src/NwGtpv2cTrxn.c:0248    Created not trx without seqNum as transaction 0x7f81600041c0. Head (nil), Next 0x5570b568c7a2
001830 00200:379268 7F81FA7FC700 DEBUG GTPv2- nwgtpv2c-0.11/src/NwGtpv2cTrxn.c:0264    Created transaction 0x7f81600041c0
001831 00200:379281 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2229    Entering nwGtpv2cStartTimer()
001832 00200:379292 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0250    Entering nas_proc_ul_transfer_ind()
001833 00200:379301 7F81FA7FC700 DEBUG GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2294    Started timer 0x7f81600041a0 for info 0x0x7f81600042e0!
001836 00200:379340 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2300    Leaving nwGtpv2cStartTimer() (rc=0)
001837 00200:379355 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:0770    Leaving nwGtpv2cHandleUlpInitialReq() (rc=0)
001838 00200:379361 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2074    Leaving nwGtpv2cProcessUlpReq() (rc=0)
001834 00200:379301 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0077    Looking for task 9
001839 00200:379395 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0093    Found matching port with high port 46468. 
001840 00200:379408 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0446    [39] Sending message of size 47 to 192.168.61.196 and port 2123
001835 00200:379319 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001841 00200:379465 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0122    Received 1 events
001842 00200:379475 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0190    Entering emm_as_send()
001843 00200:379484 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0197    EMMAS-SAP - Received primitive EMMAS_DATA_IND (211)
001844 00200:379492 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0557    Entering _emm_as_data_ind()
001845 00200:379537 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0565    EMMAS-SAP - Received AS data transfer indication (ue_id=1, delivered=true, length=13)
001846 00200:379548 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001847 00200:379557 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0260    Entering nas_message_decrypt()
001848 00200:379565 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0694    Entering nas_message_header_decode()
001849 00200:379580 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0751    Leaving nas_message_header_decode() (rc=6)
001850 00200:379585 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1392    Entering _nas_message_get_mac()
001851 00200:379590 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1469    NAS_SECURITY_ALGORITHMS_EIA2 dir UPLINK count.seq_num 2 count 2
001852 00200:379599 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0076    Byte length: 16, Zero bits: 0:
001853 00200:379651 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0077    hex stream m: 00 00 00 02 00 00 00 00 02 07 43 00 03 52 00 c2
001854 00200:379682 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0079    hex stream Key: 3d 40 c1 8e 32 36 d6 3a a0 21 09 07 3a dd 31 2f
001855 00200:379705 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0081    hex stream Message: 02 07 43 00 03 52 00 c2
001856 00200:379727 7F820083C700 TRACE NAS    r-mme/src/secu/nas_stream_eia2.c:0089    hex stream Out: 1b e6 d5 cf e7 85 7f 24 a9 6b 7b d5 d9 39 48 42
001857 00200:379746 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1485    NAS_SECURITY_ALGORITHMS_EIA2 returned MAC 1b.e6.d5.cf(3486901787) for length 8 direction 0, count 2
001858 00200:379756 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1487    Leaving _nas_message_get_mac() (rc=468112847)
001859 00200:379764 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0303    Integrity: MAC Success
001860 00200:379772 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1049    Entering _nas_message_decrypt()
001861 00200:379780 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:1175    NAS_SECURITY_ALGORITHMS_EEA0 dir 0 ul_count.seq_num 2 dl_count.seq_num 3
001862 00200:379788 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:1183    Leaving _nas_message_decrypt() (rc=7)
001863 00200:379796 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0335    Leaving nas_message_decrypt() (rc=7)
001864 00200:379804 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0269    Entering _emm_as_recv()
001865 00200:379812 7F820083C700 INFO  NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0285    EMMAS-SAP - Received EMM message (length=7) integrity protected 1 ciphered 1 mac matched 1 security context 1
001866 00200:379822 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001867 00200:379839 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0360    Entering nas_message_decode()
001868 00200:379846 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0374    hex stream Incoming NAS message:  07 43 00 03 52 00 c2
001869 00200:379866 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0694    Entering nas_message_header_decode()
001870 00200:379875 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0751    Leaving nas_message_header_decode() (rc=1)
001871 00200:379905 7F820083C700 DEBUG NAS    rc/nas/api/network/nas_message.c:0386    nas_message_header_decode returned size 1
001872 00200:379919 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0776    Entering _nas_message_plain_decode()
001873 00200:379928 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0101    Entering emm_msg_decode()
001874 00200:379937 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0121    EMM-MSG   - Message Type 0x43
001875 00200:379945 7F820083C700 TRACE NAS-ES rc/nas/ies/EsmMessageContainer.c:0037    Entering decode_esm_message_container()
001876 00200:379954 7F820083C700 TRACE NAS-ES rc/nas/ies/EsmMessageContainer.c:0054    Leaving decode_esm_message_container() (rc=5)
001877 00200:379962 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0274    Leaving emm_msg_decode() (rc=7)
001878 00200:379970 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0799    Leaving _nas_message_plain_decode() (rc=7)
001879 00200:379979 7F820083C700 TRACE NAS    rc/nas/api/network/nas_message.c:0539    Leaving nas_message_decode() (rc=7)
001880 00200:379988 7F820083C700 NOTIC NAS    air-mme/src/nas/emm/sap/emm_as.c:0414    Hit 3GPP TS 24_301R10_4_4_4_3__1 : Integrity checking of NAS signalling messages exception in the MME
001881 00200:380005 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:0415    Entering emm_recv_attach_complete()
001882 00200:380014 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:0418    EMMAS-SAP - Received Attach Complete message
001883 00200:380047 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:0696    Entering emm_proc_attach_complete()
001884 00200:380060 7F820083C700 INFO  NAS-EM openair-mme/src/nas/emm/Attach.c:0705    EMM-PROC  - EPS attach complete (ue_id=1)
001885 00200:380069 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001886 00200:380078 7F820083C700 NOTIC NAS    openair-mme/src/nas/emm/Attach.c:0722    Hit 3GPP TS 24_301R10_5_5_1_2_4__20 : Attach accepted by the network, ATTACH COMPLETE received, enter state EMM-REGISTERED
001887 00200:380090 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:2042    EMM-CTX - Add in context UE id 1 with GUTI 208.95 |8000|03|00000001
001888 00200:380104 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0137    ue_id=1 old GUTI cleared
001889 00200:380113 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_sap.c:0109    Entering emm_sap_send()
001890 00200:380121 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0104    Entering emm_reg_send()
001891 00200:380129 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0274    Entering emm_fsm_process()
001892 00200:380138 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001893 00200:380152 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0282    EMM-FSM   - Received event ATTACH_CNF (5) in state EMM-COMMON-PROCEDURE-INITIATED
001894 00200:380162 7F820083C700 TRACE NAS-EM ap/EmmCommonProcedureInitiated.c:0093    Entering EmmCommonProcedureInitiated()
001895 00200:380176 7F820083C700 INFO  NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:0872    EMM-CTX - get UE id 1 context 0x7f81680011b0
001896 00200:380185 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0176    Entering emm_fsm_set_state()
001897 00200:380193 7F820083C700 INFO  NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0185    UE 1 EMM-FSM   - Status changed: EMM-COMMON-PROCEDURE-INITIATED ===> EMM-REGISTERED
001898 00200:380202 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2251    Entering mme_ue_context_update_ue_emm_state()
001899 00200:380212 7F820083C700 TRACE MME-AP me/src/mme_app/mme_app_context.c:2279    Leaving mme_ue_context_update_ue_emm_state()
001900 00200:380221 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0213    Leaving emm_fsm_set_state() (rc=0)
001901 00200:380230 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0516    UE 1 Delete ATTACH procedure
001902 00200:380244 7F820083C700 DEBUG NAS-EM r-mme/src/nas/emm/emm_data_ctx.c:1420    T3450 stopped UE 1
001903 00200:380438 7F820083C700 DEBUG NAS-EM src/nas/emm/nas_emm_procedures.c:0534    EMM-PROC (NASx)  -  * * * * * (2) ueREF 0x7f8164009a00 has mmeId 1, enbId 06692d state 2 and eNB_ref 0x7f8164000d50. 
001904 00200:380459 7F820083C700 TRACE NAS-EM src/nas/emm/nas_emm_procedures.c:0543    UE 1 stopped the retry timer for attach procedure
001905 00200:380468 7F820083C700 DEBUG NAS-EM src/nas/emm/nas_emm_procedures.c:0550    EMM-PROC (NASx)  -  * * * * * (2.5) ueREF 0x7f8164009a00 has mmeId 1, enbId 06692d state 2 and eNB_ref 0x7f8164000d50 
001906 00200:380479 7F820083C700 TRACE NAS-EM ap/EmmCommonProcedureInitiated.c:0577    Leaving EmmCommonProcedureInitiated() (rc=0)
001907 00200:380488 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_fsm.c:0293    Leaving emm_fsm_process() (rc=0)
001908 00200:380497 7F820083C700 TRACE NAS-EM ir-mme/src/nas/emm/sap/emm_reg.c:0117    Leaving emm_reg_send() (rc=0)
001909 00200:380505 7F820083C700 TRACE NAS-EM openair-mme/src/nas/emm/Attach.c:0784    Leaving emm_proc_attach_complete() (rc=0)
001910 00200:380526 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/sap/emm_recv.c:0426    Leaving emm_recv_attach_complete() (rc=0)
001911 00200:380539 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0483    Entering emm_msg_free()
001913 00200:380549 7F820083C700 DEBUG NAS-EM ir-mme/src/nas/emm/msg/emm_msg.c:0493    EMM-MSG   - Message Type 0x43
001912 00200:380545 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/nas_esm_proc.c:0159    Entering nas_esm_proc_data_ind()
001914 00200:380557 7F820083C700 TRACE NAS-ES ir-mme/src/nas/emm/msg/emm_msg.c:0592    Leaving emm_msg_free()
001916 00200:380584 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0573    Entering _esm_sap_recv()
001917 00200:380602 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0536    Leaving _emm_as_recv() (rc=0)
001918 00200:380612 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0673    Leaving _emm_as_data_ind() (rc=0)
001915 00200:380579 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0122    Received 1 events
001920 00200:380621 7F820083C700 TRACE NAS-EM air-mme/src/nas/emm/sap/emm_as.c:0234    Leaving emm_as_send() (rc=0)
001919 00200:380621 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0117    Entering esm_msg_decode()
001921 00200:380631 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0108    Looking for sd 39
001923 00200:380646 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0147    Inserting new descriptor for task 9, sd 39
001922 00200:380632 7F820083C700 TRACE NAS-EM r-mme/src/nas/emm/nas_emm_proc.c:0270    Leaving nas_proc_ul_transfer_ind() (rc=0)
001924 00200:380654 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0261    Leaving esm_msg_decode() (rc=3)
001925 00200:380712 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/sap/esm_recv.c:0865    Entering esm_recv_activate_default_eps_bearer_context_accept()
001926 00200:380723 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0216    Entering mme_app_nas_esm_get_pdn_connectivity_procedure()
001928 00200:380732 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_esm_procedures.c:0234    Leaving mme_app_nas_esm_get_pdn_connectivity_procedure() (rc=140193571016096)
001927 00200:380729 7F81FAFFD700 DEBUG UDP    /src/udp/udp_primitives_server.c:0192    Msg of length 46 received from 192.168.61.196:2123
001929 00200:380748 7F81FBFFF700 TRACE NAS-ES aultEpsBearerContextActivation.c:0318    Entering esm_proc_default_eps_bearer_context_accept()
001930 00200:380778 7F81FBFFF700 INFO  NAS-ES aultEpsBearerContextActivation.c:0323    ESM-PROC  - Default EPS bearer context activation accepted by the UE (ue_id=1, ebi=5)
001931 00200:380789 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:1874    Entering nwGtpv2cProcessUdpReq()
001932 00200:380793 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_bearer_context.c:0385    Entering mme_app_esm_update_ebr_state()
001933 00200:380810 7F81FA7FC700 DEBUG GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:1468    RECEIVED GTPV2c  response message of type 35, length 46 and seqNum 8691.
001934 00200:380825 7F81FBFFF700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0062    Entering mme_app_get_pdn_context()
001935 00200:380826 7F81FA7FC700 DEBUG GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:1492    Not removing the initial request transaction for message type 35, seqNo 8691 (altough remove flag set). 
001936 00200:380842 7F81FBFFF700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0082    Leaving mme_app_get_pdn_context()
001937 00200:380848 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0132    Created message 0x7f81600043a0!
001938 00200:380852 7F81FBFFF700 TRACE MME-AP mme_app/mme_app_bearer_context.c:0414    Leaving mme_app_esm_update_ebr_state() (rc=0)
001939 00200:380857 7F81FA7FC700 DEBUG GTPv2- .11/src/NwGtpv2cMsgIeParseInfo.c:1314    Received IE 2 with instance 0 of length 2 in msg-type 35!
001940 00200:380862 7F81FBFFF700 TRACE NAS-ES aultEpsBearerContextActivation.c:0346    Leaving esm_proc_default_eps_bearer_context_accept()
001941 00200:380867 7F81FA7FC700 DEBUG GTPv2- .11/src/NwGtpv2cMsgIeParseInfo.c:1314    Received IE 93 with instance 0 of length 24 in msg-type 35!
001942 00200:380872 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/sap/esm_recv.c:0924    Leaving esm_recv_activate_default_eps_bearer_context_accept() (rc=-1)
001943 00200:380877 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:1140    Entering nwGtpv2cSendTriggeredRspIndToUlp()
001944 00200:380882 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0447    Entering esm_msg_free()
001945 00200:380896 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0592    Leaving esm_msg_free()
001946 00200:380904 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0447    Entering esm_msg_free()
001947 00200:380909 7F81FA7FC700 DEBUG GTPv2- v2c-0.11/src/NwGtpv2cMsgParser.c:0211    Received IE 2 of length 2!
001949 00200:380928 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0153    	- Cause value 16
001948 00200:380912 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/msg/esm_msg.c:0592    Leaving esm_msg_free()
001950 00200:380935 7F81FA7FC700 DEBUG GTPv2- v2c-0.11/src/NwGtpv2cMsgParser.c:0211    Received IE 93 of length 24!
001951 00200:380942 7F81FBFFF700 TRACE NAS-ES ir-mme/src/nas/esm/sap/esm_sap.c:0949    Leaving _esm_sap_recv()
001952 00200:380942 7F81FA7FC700 DEBUG S11    matter/src/gtpv2c_ie_formatter.c:0374    	- EBI 5
001953 00200:380956 7F81FBFFF700 TRACE NAS-ES r-mme/src/nas/esm/nas_esm_proc.c:0178    Leaving nas_esm_proc_data_ind() (rc=0)
001954 00200:380962 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0153    	- Cause value 16
001955 00200:380967 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0232    	- F-TEID type 1
001956 00200:380972 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0237    	- TEID/GRE    00000001
001957 00200:380979 7F81FA7FC700 DEBUG GTPv2- matter/src/gtpv2c_ie_formatter.c:0249    	- IPv4 addr   192.168.61.197
001958 00200:380989 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0144    Purging message 0x7f81600043a0!
001959 00200:380994 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0149    Message pool 7f81600043a0! Next element 0! 
001960 00200:381027 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:1154    Leaving nwGtpv2cSendTriggeredRspIndToUlp() (rc=0)
001961 00200:381036 7F81FA7FC700 WARNI GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:1535    Removing the initial request transaction for message type 35, seqNo 8691 in conclusion (not late response). 
001962 00200:381043 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2392    Entering nwGtpv2cStopTimer()
001963 00200:381044 7F81F9704700 TRACE MME-AP mme/src/mme_app/mme_app_bearer.c:2008    Entering mme_app_handle_modify_bearer_resp()
001964 00200:381048 7F81FA7FC700 DEBUG GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2406    Stopping active timer 0x7f81600041a0 for info 0x0x7f81600042e0!
001965 00200:381063 7F81F9704700 DEBUG MME-AP mme/src/mme_app/mme_app_bearer.c:2011    Received S11_MODIFY_BEARER_RESPONSE from S+P-GW
001967 00200:381074 7F81FA7FC700 INFO  GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2418    Stopped active timer 0x7f81600041a0 for info 0x0x7f81600042e0!
001966 00200:381074 7F81F9704700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0062    Entering mme_app_get_pdn_context()
001968 00200:381093 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2445    Leaving nwGtpv2cStopTimer() (rc=0)
001969 00200:381108 7F81F9704700 TRACE MME-AP rc/mme_app/mme_app_pdn_context.c:0082    Leaving mme_app_get_pdn_context()
001970 00200:381111 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0144    Purging message 0x7f8160000d50!
001971 00200:381122 7F81F9704700 INFO  MME-AP mme/src/mme_app/mme_app_bearer.c:2329    No pending removal of bearers for ueId: 1. Checking any pending bearer requests. 
001972 00200:381123 7F81FA7FC700 DEBUG GTPv2- /nwgtpv2c-0.11/src/NwGtpv2cMsg.c:0149    Message pool 7f8160000d50! Next element 7f81600043a0! 
001973 00200:381137 7F81F9704700 TRACE MME-AP mme/src/mme_app/mme_app_bearer.c:0904    Entering mme_app_handle_bearer_ctx_retry()
001974 00200:381143 7F81FA7FC700 DEBUG GTPv2- nwgtpv2c-0.11/src/NwGtpv2cTrxn.c:0422    Purging  transaction 0x7f81600041c0 with seqNum 34449. (before) Head (nil), Next (nil). 
001975 00200:381147 7F81F9704700 INFO  MME-AP mme/src/mme_app/mme_app_bearer.c:1135    No S11 procedure could be found for UE 1. 
001976 00200:381154 7F81FA7FC700 DEBUG GTPv2- nwgtpv2c-0.11/src/NwGtpv2cTrxn.c:0429    After purging  transaction 0x7f81600041c0, Head 0x7f81600041c0, Next (nil)
001977 00200:381156 7F81F9704700 TRACE MME-AP mme/src/mme_app/mme_app_bearer.c:1136    Leaving mme_app_handle_bearer_ctx_retry()
001978 00200:381162 7F81FA7FC700 TRACE GTPv2- 2-c/nwgtpv2c-0.11/src/NwGtpv2c.c:2014    Leaving nwGtpv2cProcessUdpReq() (rc=0)
001979 00200:381167 7F81F9704700 TRACE MME-AP mme/src/mme_app/mme_app_bearer.c:2331    Leaving mme_app_handle_modify_bearer_resp() (rc=0)
001980 00200:853706 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0039    ======================================= STATISTICS ============================================

001981 00200:853730 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0042                   |   Current Status| Added since last display|  Removed since last display |
001982 00200:853738 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0048    Connected eNBs |          1      |              0              |             0               |
001983 00200:853744 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0054    Attached UEs   |          1      |              1              |             0               |
001984 00200:853752 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0060    Connected UEs  |          1      |              1              |             0               |
001985 00200:853757 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0066    Default Bearers|          0      |              0              |             0               |
001986 00200:853765 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0072    S1-U Bearers   |          0      |              0              |             0               |

001987 00200:853772 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0075    ======================================= STATISTICS ============================================

001988 00210:853698 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0039    ======================================= STATISTICS ============================================

001989 00210:853722 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0042                   |   Current Status| Added since last display|  Removed since last display |
001990 00210:853730 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0048    Connected eNBs |          1      |              0              |             0               |
001991 00210:853736 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0054    Attached UEs   |          1      |              0              |             0               |
001992 00210:853743 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0060    Connected UEs  |          1      |              0              |             0               |
001993 00210:853749 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0066    Default Bearers|          0      |              0              |             0               |
001994 00210:853756 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0072    S1-U Bearers   |          0      |              0              |             0               |

001995 00210:853762 7F81F9704700 DEBUG MME-AP src/mme_app/mme_app_statistics.c:0075    ======================================= STATISTICS ============================================
```


## eNB logs:

```bash
[RRC]   [FRAME 00128][eNB][MOD 00][RNTI 18b8] Decoding UL CCCH 5c.6b.5b.b2.95.56 (0x55bb9587ab03)
[RRC]   [FRAME 00128][eNB][MOD 00][RNTI 18b8] Accept new connection from UE random UE identity (0x5529bbb5c6000000) MME code 0 TMSI 0 cause 3
[MAC]   UE 0 RNTI 18b8 adding LC 1 idx 0 to scheduling control (total 1)
[MAC]   UE 0 RNTI 18b8 adding LC 2 idx 1 to scheduling control (total 2)
[MAC]   Added physicalConfigDedicated 0x7f9e1c1ca6b0 for 0.0
[RRC]   [FRAME 00128][eNB][MOD 00][RNTI 18b8]CALLING RLC CONFIG SRB1 (rbid 1)
add new uid is 0 18b8

[PDCP]   [FRAME 00128][eNB][MOD 00][RNTI 18b8][SRB 01]  Action ADD  LCID 1 (SRB id 1) configured with SN size 5 bits and RLC AM
[MAC]   generate_Msg4 ra->Msg4_frame SFN/SF: 128.4,  frameP SFN/SF: 128.4 FOR eNB_Mod: 0 
[MAC]   [eNB 0][RAPROC] CC_id 0 Frame 128, subframeP 4: Generating Msg4 with RRC Piggyback (RNTI 18b8)
[RRC]   [FRAME 00000][eNB][MOD 00][RNTI 18b8] [RAPROC] Logical Channel UL-DCCH, processing LTE_RRCConnectionSetupComplete from UE (SRB1 Active)
[NAS]    AttachRequest.c:40  EMM  - attach_request len = 85
[NAS]    UeNetworkCapability.c:46  decode_ue_network_capability len = 5
[NAS]    UeNetworkCapability.c:63  uenetworkcapability decoded UMTS

[NAS]    UeNetworkCapability.c:74  uenetworkcapability decoded GPRS

[NAS]    UeNetworkCapability.c:82  uenetworkcapability decoded=6

[NAS]    UeNetworkCapability.c:86  uenetworkcapability then decoded=6

[S1AP]   [eNB 0] Build S1AP_NAS_FIRST_REQ adding in s_TMSI: GUMMEI mme_code 1 mme_group_id 4 ue 18b8
[RRC]   [FRAME 00000][eNB][MOD 00][RNTI 18b8] UE State = RRC_CONNECTED 
[S1AP]   [eNB 0] Chose MME '(null)' (assoc_id 1) through selected PLMN Identity index 0 MCC 208 MNC 95
[S1AP]   Found usable eNB_ue_s1ap_id: 0x06692d 420141(10)
[S1AP]   GUMMEI_ID_PRESENT
[SCTP]   Successfully sent 152 bytes on stream 1 for assoc_id 1
[SCTP]   Found data for descriptor 95
[SCTP]   [1][95] Msg of length 29 received from port 36412, on stream 1, PPID 18
[RRC]   [eNB 0] Received S1AP_DOWNLINK_NAS: ue_initial_id 1, eNB_ue_s1ap_id 420141
[RRC]   sent RRC_DCCH_DATA_REQ to TASK_PDCP_ENB
[SCTP]   Successfully sent 65 bytes on stream 1 for assoc_id 1
[SCTP]   Found data for descriptor 95
[SCTP]   [1][95] Msg of length 62 received from port 36412, on stream 1, PPID 18
[RRC]   [eNB 0] Received S1AP_DOWNLINK_NAS: ue_initial_id 1, eNB_ue_s1ap_id 420141
[RRC]   sent RRC_DCCH_DATA_REQ to TASK_PDCP_ENB
[SCTP]   Successfully sent 73 bytes on stream 1 for assoc_id 1
[SCTP]   Found data for descriptor 95
[SCTP]   [1][95] Msg of length 62 received from port 36412, on stream 1, PPID 18
[RRC]   [eNB 0] Received S1AP_DOWNLINK_NAS: ue_initial_id 1, eNB_ue_s1ap_id 420141
[RRC]   sent RRC_DCCH_DATA_REQ to TASK_PDCP_ENB
[SCTP]   Successfully sent 65 bytes on stream 1 for assoc_id 1
[SCTP]   Found data for descriptor 95
[SCTP]   [1][95] Msg of length 43 received from port 36412, on stream 1, PPID 18
[RRC]   [eNB 0] Received S1AP_DOWNLINK_NAS: ue_initial_id 1, eNB_ue_s1ap_id 420141
[RRC]   sent RRC_DCCH_DATA_REQ to TASK_PDCP_ENB
[SCTP]   Successfully sent 67 bytes on stream 1 for assoc_id 1
[SCTP]   Found data for descriptor 95
[SCTP]   [1][95] Msg of length 35 received from port 36412, on stream 1, PPID 18
[RRC]   [eNB 0] Received S1AP_DOWNLINK_NAS: ue_initial_id 1, eNB_ue_s1ap_id 420141
[RRC]   sent RRC_DCCH_DATA_REQ to TASK_PDCP_ENB
[SCTP]   Successfully sent 68 bytes on stream 1 for assoc_id 1
[SCTP]   Found data for descriptor 95
[SCTP]   [1][95] Msg of length 179 received from port 36412, on stream 1, PPID 18
[S1AP]   Received NAS message with the E_RAB setup procedure
[RRC]   [eNB 0] Received S1AP_INITIAL_CONTEXT_SETUP_REQ: ue_initial_id 1, eNB_ue_s1ap_id 420141, nb_of_e_rabs 1
[GTPV1U]   Configured GTPu address : 1e3da8c0
[GTPV1U]   Copied to create_tunnel_resp tunnel: index 0 target gNB ip 192.168.61.30 length 4 gtp teid 3396329693
[RRC]   [FRAME 00000][eNB][MOD 00][RNTI 18b8] rrc_eNB_process_GTPV1U_CREATE_TUNNEL_RESP tunnel (3396329693, 3396329693) bearer UE context index 0, msg index 0, id 5, gtp addr len 4 
[RRC]   [eNB 0][UE 18b8] Selected security algorithms (0x7f9e34005e50): 0, 2, changed
[RRC]   [eNB 0][UE 18b8] Saved security key D418FA6D1E24C7FA32A57298BD83FAA88453E6BC61036B6FB70BE05F05A47607
[RRC]   
KeNB:d4 18 fa 6d 1e 24 c7 fa 32 a5 72 98 bd 83 fa a8 84 53 e6 bc 61 03 6b 6f b7 0b e0 5f 05 a4 76 07 
[RRC]   
KRRCenc:8e a8 01 00 44 4a dd 08 03 8c e5 f7 6e 42 14 68 8a 06 73 56 5e f4 79 8d f0 81 08 29 29 b6 b4 79 
[RRC]   
KRRCint:8e 8c 7d 76 61 99 e4 da 35 62 96 69 e7 a7 42 8f a5 f7 79 c5 76 24 ec 64 84 78 e6 5b d7 a6 78 db 
[RRC]   [FRAME 00000][eNB][MOD 00][RNTI 18b8] Logical Channel DL-DCCH, Generate SecurityModeCommand (bytes 3)
[RRC]   calling rrc_data_req :securityModeCommand
[RRC]   sent RRC_DCCH_DATA_REQ to TASK_PDCP_ENB
[RRC]   [FRAME 00000][eNB][MOD 00][RNTI 18b8] received securityModeComplete on UL-DCCH 1 from UE
<FreqBandList>
        <bandInformationEUTRA>
            <bandEUTRA>7</bandEUTRA>
        </bandInformationEUTRA>
    
        <bandInformationNR>
            <bandNR>78</bandNR>
        </bandInformationNR>
    
</FreqBandList>
[RRC]   [FRAME 00000][eNB][MOD 00][RNTI 18b8] Logical Channel DL-DCCH, Generate UECapabilityEnquiry (bytes 10)
[RRC]   sent RRC_DCCH_DATA_REQ to TASK_PDCP_ENB
[RRC]   [FRAME 00000][eNB][MOD 00][RNTI 18b8] received ueCapabilityInformation on UL-DCCH 1 from UE
[RRC]   got UE capabilities for UE 18b8
[RRC]   drx_Configuration parameter is NULL, cannot configure local UE parameters or CDRX is deactivated
[RRC]   [eNB 0] frame 0: requesting A2, A3, A4, and A5 event reporting
[RRC]   RRCConnectionReconfiguration Encoded 946 bits (119 bytes)
[RRC]   [eNB 0] Frame 0, Logical Channel DL-DCCH, Generate LTE_RRCConnectionReconfiguration (bytes 119, UE id 18b8)
[RRC]   sent RRC_DCCH_DATA_REQ to TASK_PDCP_ENB
[PDCP]   [FRAME 00000][eNB][MOD 00][RNTI 18b8][SRB 02]  Action ADD  LCID 2 (SRB id 2) configured with SN size 5 bits and RLC AM
[SCTP]   Successfully sent 75 bytes on stream 1 for assoc_id 1
[PDCP]   [FRAME 00000][eNB][MOD 00][RNTI 18b8][DRB 01]  Action ADD  LCID 3 (DRB id 1) configured with SN size 12 bits and RLC AM
[RRC]   [FRAME 00000][eNB][MOD 00][RNTI 18b8] UE State = RRC_RECONFIGURED (default DRB, xid 0)
[PDCP]   [FRAME 00000][eNB][MOD 00][RNTI 18b8][SRB 02]  Action MODIFY LCID 2 RB id 2 reconfigured with SN size 5 and RLC AM 
[PDCP]   [FRAME 00000][eNB][MOD 00][RNTI 18b8][DRB 01]  Action MODIFY LCID 3 RB id 1 reconfigured with SN size 1 and RLC AM 
[RRC]   [eNB 0] Frame  0 CC 0 : SRB2 is now active
[RRC]   [eNB 0] Frame  0 : Logical Channel UL-DCCH, Received LTE_RRCConnectionReconfigurationComplete from UE rnti 18b8, reconfiguring DRB 1/LCID 3
[RRC]   [eNB 0] Frame  0 : Logical Channel UL-DCCH, Received LTE_RRCConnectionReconfigurationComplete from UE 0, reconfiguring DRB 1/LCID 3
[MAC]   UE 0 RNTI 18b8 adding LC 3 idx 2 to scheduling control (total 3)
[MAC]   Added physicalConfigDedicated 0x7f9e1c1ca6b0 for 0.0
[S1AP]   initial_ctxt_resp_p: e_rab ID 5, enb_addr 192.168.61.30, SIZE 4 
[SCTP]   Successfully sent 40 bytes on stream 1 for assoc_id 1
[SCTP]   Successfully sent 61 bytes on stream 1 for assoc_id 1
```

## Test traffic

```bash
$ macphone2
macphone2:~ tester$ adb devices
List of devices attached
TA3640BB09	device

macphone2:~ tester$ adb shell
shell@surnia_uds:/ $ ping -c 3 www.lemonde.fr
PING s2.shared.global.fastly.net (151.101.122.217) 56(84) bytes of data.
64 bytes from 151.101.122.217: icmp_seq=1 ttl=53 time=40.2 ms
64 bytes from 151.101.122.217: icmp_seq=2 ttl=53 time=35.1 ms
64 bytes from 151.101.122.217: icmp_seq=3 ttl=53 time=47.5 ms

--- s2.shared.global.fastly.net ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2000ms
rtt min/avg/max/mdev = 35.178/41.006/47.583/5.097 ms
```

___
# Properly disconnect

```bash
$ macphone2
macphone2:~ tester$ phone-off
Turning OFF phone : turning on airplane mode
Broadcasting: Intent { act=android.intent.action.AIRPLANE_MODE (has extras) }
Broadcast completed: result=0
```

```bash
oaici@fit23:~/openairinterface5g/ci-scripts/yaml_files/inria_enb_mono_fdd$ docker-compose down
Stopping prod-enb-mono-fdd ... done
Removing prod-enb-mono-fdd ... done
Removing network prod-oai-public-net
```

```bash
oaici@fit17:~/openair-epc-fed/docker-compose/inria-oai-mme$ docker-compose down
Stopping prod-oai-spgwu-tiny ... done
Stopping prod-oai-spgwc      ... done
Stopping prod-oai-mme        ... done
Stopping prod-oai-hss        ... done
Stopping prod-trf-gen        ... done
Stopping prod-cassandra      ... done
Removing prod-oai-spgwu-tiny ... done
Removing prod-oai-spgwc      ... done
Removing prod-oai-mme        ... done
Removing prod-oai-hss        ... done
Removing prod-trf-gen        ... done
Removing prod-cassandra      ... done
Removing network prod-oai-private-net
Removing network prod-oai-public-net
```
___
# New 4G/5G devices Quectel RM500Q-GL

We have recently added new 4G/5G UEs on R2lab, more precisely some Quectel RM500Q-GL devices. Check the [map of nodes](https://r2lab.inria.fr/hardware.md) to have an up-to-date view of devices attached on each node in R2lab. 

To use one such a UE, you should first load the **quectel** image on the node the Quectel device is attached to, and of course, run 

Then, you need to run the Quectel Connection Manager on this node using another terminal:

```bash
root@fit32: start-quectelCM
```

After that, launch a new terminal on the node, wait about 20s and run the following detach command (if the enB is not yet started, just to ensure it will not disturb its init phase).

```bash
root@fit32: quectel-detach
```

Once the eNB is up and running, you can attach the Quectel device using the  following command:

```bash
root@fit32: quectel-attach
```

Then, wait about 30s and you should see the wwan0 network interface up and running a new route set to use this connection.

You can check the 4G/5G connection using the following command:

```bash
root@fit32: check-quectel-cx
```

Note that we have added an option on the **deploy.py** script to handle automatically all the steps described above. Just use the option -Q and precise the R2lab fit nodes that host the Quectel devices you're interested in.  For instance the following command will run the demo without phone (option -P0) and using only the Quectel device attached on node fit32.

```bash
mylaptop: ./deploy.py -P0 -Q32
```


You could also run a local iperf test on the wireless link. To do this, first add the following route on fit32 and run iperf:

```bash
root@fit32: route add -net 192.168.61.192/26 wwan0
root@fit32:~# ip route
default via 192.168.3.100 dev control 
12.1.1.0/30 dev wwan0 proto kernel scope link src 12.1.1.2 
192.168.3.0/24 dev control proto kernel scope link src 192.168.3.32 
192.168.61.192/26 dev wwan0 scope link 
root@fit32:~# iperf -B 12.1.1.2 -u -i 1 -s
```
Then, on another terminal connect to the **prod-trf-gen** container on the CN host (i.e., fit17 by default):

```bash
oaici@fit17:~$ docker exec -it prod-trf-gen /bin/bash
root@4e44085d3d83:/iperf-2.0.5# ping -c 2 12.1.1.2
PING 12.1.1.2 (12.1.1.2) 56(84) bytes of data.
64 bytes from 12.1.1.2: icmp_seq=1 ttl=63 time=23.4 ms
root@4e44085d3d83:/iperf-2.0.5# iperf -c 12.1.1.2 -u -i 1 -t 10 -b 1M
------------------------------------------------------------
Client connecting to 12.1.1.2, UDP port 5001
Sending 1470 byte datagrams, IPG target: 11215.21 us (kalman adjust)
UDP buffer size:  208 KByte (default)
------------------------------------------------------------
[  3] local 192.168.61.198 port 38275 connected with 12.1.1.2 port 5001
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0- 1.0 sec   131 KBytes  1.07 Mbits/sec
[  3]  1.0- 2.0 sec   128 KBytes  1.05 Mbits/sec
[  3]  2.0- 3.0 sec   128 KBytes  1.05 Mbits/sec
[  3]  3.0- 4.0 sec   128 KBytes  1.05 Mbits/sec
[  3]  4.0- 5.0 sec   128 KBytes  1.05 Mbits/sec
[  3]  5.0- 6.0 sec   128 KBytes  1.05 Mbits/sec
[  3]  6.0- 7.0 sec   129 KBytes  1.06 Mbits/sec
[  3]  7.0- 8.0 sec   128 KBytes  1.05 Mbits/sec
[  3]  8.0- 9.0 sec   128 KBytes  1.05 Mbits/sec
[  3]  9.0-10.0 sec   128 KBytes  1.05 Mbits/sec
[  3]  0.0-10.0 sec  1.25 MBytes  1.05 Mbits/sec
[  3] Sent 893 datagrams
[  3] Server Report:
[  3]  0.0-10.0 sec  1.25 MBytes  1.05 Mbits/sec   0.000 ms 2147481862/2147482755 (0%)
```



