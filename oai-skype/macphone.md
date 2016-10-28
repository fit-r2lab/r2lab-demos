# macphone per se

## MAC addresses

* `d8:30:62:a5:3b:a7` - thunderbolt -> 192.168.4.200
* `6c:40:08:b6:c1:7e` - USB -> 192.168.4.201

## iptables / port mapping 5900 from faraday to macphone

```
iptables -t nat -A PREROUTING -j DNAT -p tcp -d 138.96.16.97 --dport 5900 --to 192.168.4.201:5900
```

## miscell : checking for switches on VLAN 40 (192.168.4.x)

```
while true; do
 echo ============================== $(date); 
 for i in 200 201 250 251; do 
 ping -c 1 -W 1 192.168.4.$i >& /dev/null && echo "$i : YES" || echo "$i OFF"; 
 done; 
 sleep 10; 
 done
```

# Experimental accounts

## used on the MAC

* skype: `chamber r2lab`

## used on the phone

* gmail: `demodianainria@gmail.com` / `007ddi007`
* skype: `demor2lab`
* this google account has a indefinite licence to use vysor pro - acquired on Oct. 28 2016

# Phone(s)

## common to all phones

After an install/upgrade, make sure to check for these manually:

### Basic & Convenience

* In the **Settings ⟹ Developer Options** menu:
* **USB debugging** must be *on* 
* also make sure to turn *on* the **Stay awake** topic, because it's very hard to unlock the screen through the Screen Sharing utility

### Cellular networks

* In the **Settings ⟹ Cellular network settings** menu:
* Access point names: r2lab, oai.ipv4 (not sure this is required actually...)

## Nexus 5

* SIM pin code is # `1234`
* Android Device ID is `1D54D2632597731`
* Google Service Framework (GSF) is `31700F125B218CD6` - useful for downloading apk files

## Nexus 6

* pin code # `1234` 
* This setting does not survive reboot**
  * appli 4G switcher
  * Set preferred network type -> LTE only
* profil apn 
  * Settings
  * ... more
  * Cellular networks (requires airplane mode OFF)
  * Access point names
  * Check that r2lab is selected 
  * Details should be
    * APN = oai.ipv4
    * MCC = 208
    * MNC = 95
    * Bearer = LTE

* NOTES
  * after reboot, you need to restart the vysor application

# google play

## retrieving `.apk` files for installation through `adb install`

I tried to get in a position where I could do installs remotely while 4G connection was broken; this did not work out..

* I installed `Device ID` (from Evozi) that gave me the GSF ID for that device
* I added a chrome extension on my own MAC named `Direct APK Downloader`
* Once this extension is in place, when visiting google play store with that chrome, I get an additional button `Download APK`
* Clicking this leads me to a login where I can give
  * my gmail account
  * its password
  * the GSF ID
* at that point the google play website whined because I had not been using that email to reach the google store from the phone itself (the GSF comes from the phone)


