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

# Phone(s)

## android

After an upgrade, make sure to check for these manually

* In the **Settings ⟹ Developer Options** menu:
* **USB debugging** must be *on* 
* also make sure to turn *on* the **Stay awake** topic, because it's very hard to unlock the screen through the Screen Sharing utility

## Nexus 5

### PIN code

Nexus 5 has pin # `1234`

