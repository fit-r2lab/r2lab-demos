# macphones

## reachable from the outside w/ VNC or Screen Sharing

```
faraday-macphone1.inria.fr has address 138.96.16.99
root@faraday ~ (master *) #
host faraday-macphone2.inria.fr
faraday-macphone2.inria.fr has address 138.96.16.100
```

```
iptables -t nat -A PREROUTING -d 138.96.16.99/32 -p tcp -m tcp --dport 5900 -j DNAT --to-destination 192.168.4.201:5900
iptables -t nat -A PREROUTING -d 138.96.16.100/32 -p tcp -m tcp --dport 5900 -j DNAT --to-destination 192.168.4.202:5900
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

* gmail: `demodianainria@gmail.com`
* skype: `demor2lab`
* see macphone-private.md for more details

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

## Nexus 5 (now, instead of Nexus 6)

* SIM pin code is # `1234`
* Android Device ID is `1D54D2632597731`
* Google Service Framework (GSF) is `31700F125B218CD6` - useful for downloading apk files

* This setting does not survive reboot**
  * app 4G switcher
  * Set preferred network type -> LTE only
  * verify several times that this mode does not change by relaunching the app 4G switcher
* profil APN
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

* Verify also that:
	* Settings/Wi-Fi Mode is off
	* Settings/Bluetooth Mode is off
	* Settings/Data Usage/Cellular Data is on

* NOTES
  * after reboot, you need to restart the vysor application
  * *phone-reboot* does not do the exact same job than a manual reboot, e.g., you don't need to enter PIN for SIM just after the *phone-reboot* command...

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

