![](oai-nodes.001.png)


# Ubuntu 16 vs 14

Images are available for ubuntu 16 for now; they are named `oai16-gw-base` and `oai16-enb-base`.

I'm working on redoing the same for ubuntu14, the names will of course be `oaiu14*` when they are ready

# prep infra

## the HSS box

```
n 23
rload -i u16-oai-gw 23 16
rwait -t 120
ss
refresh
demo
```

## the EPC box

```
n 16
rwait -t 500
ss
refresh
demo
```
## the ENB box

```
n 19
rload -i u16-oai-enb 19 
rwait -t 300
ss
refresh
demo
```

## MAC controlling the phone

*Screen sharing* -> faraday.inria.fr -> tester/tester++

```
phone status
```


## the scrambler box

```
n 11
rload -i oai-scrambler
rwait
ss
refresh
demo
```

# Run it

## common scenario for the 3 boxes

```
o init
o configure
o start

o logs
```

## the scrambler

```
o scrambler [-blast]
```

*****
*****
*****


# Various notes


## DB report

```
select imsi, imei, access_restriction,  mmeidentity_idmmeidentity from users where imsi = 208950000000002;

select * from mmeidentity where mmerealm='r2lab.fr' ;
```

## NOTES on generic kernel

***this section now obsolete, for u16 at least***

* tried to rebuild from scratch (14.04)
* created `oai-epc-kgen-builds` (skipped the base step)
* that turned out to have 4.2, so
* created `oai-epc-k319-builds` 
* however this turned out to have a broken build for freediameter (no network or something - see build_epc-i.log)
* so now that I know how to switch kernels:
  * restarted from `oai-gw-builds3`
  * reinstalled `3.19.0-58-generic`
  * set `DEFAULT="1>2"` in `/etc/default/grub`
  * applied `grub-update`
  * and produced `oai-gw-kgen-builds3`