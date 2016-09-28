# MAC addresses

* `d8:30:62:a5:3b:a7` - thunderbolt -> 192.168.4.200
* `6c:40:08:b6:c1:7e` - USB -> 192.168.4.201

# iptables / port mapping 5900 from faraday to macphone

```
iptables -t nat -A PREROUTING -j DNAT -p tcp -d 138.96.16.97 --dport 5900 --to 192.168.4.201:5900
```

# miscell

```
while true; do
 echo ============================== $(date); 
 for i in 200 201 250 251; do 
 ping -c 1 -W 1 192.168.4.$i >& /dev/null && echo "$i : YES" || echo "$i OFF"; 
 done; 
 sleep 10; 
 done
```
