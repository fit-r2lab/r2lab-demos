The ns3-scenario.py script is used to integrate the network simulator, ns-3 with R2lab. 
Consider two nodes, fit03 (the server) and fit04 (the client). 
A network simulation is running on fit04. 
We try to ping a simulated node in fit04 from the real node fit03. 
The following options are available:

Point to point scenario:

1) Ping
  
   We ping an ns-3 simulated node, running on fit04 from fit03. 
We can use the --target option to specify the ns-3 simulated node. 
By default, the ns-3 node with IP address 10.1.1.2 is pinged from fit03.
   This is the default scenario in the script.

2) VLC 

   We send unicast packets from fit03 to the ns-3 simulated node with IP address 
10.1.1.2 using VLC. This option can be enabled through --vlc.


Multicast scenario:

1) mcsender
 
   We send multicast packets from fit03 to the ns-3 simulated nodes using mcsender, 
a multicast test tool to send multicast test packets. 
This option can be enabled using --multicast.

2) VLC 

    We send multicast packets from fit03 to the ns-3 simulated nodes using VLC. 
This option can be enabled using --multicast --vlc.



The following two topology options are available for all the scenarios listed above:

1) CSMA

   The ns-3 simulated network in fit04 is a CSMA channel consisting of 4 simulated nodes, 
with IP addresses ranging from 10.1.1.1 to 10.1.1.4. 
CSMA channel is the default topology for all scenarios.

2) OLSR

   The ns-3 simulated network in fit04 uses the Optimized Link State Routing (OLSR) 
protocol, which is a dynamic mobile ad hoc unicast routing protocol. 
This topology can be enabled by using --olsr.


Example:

To run the scenario where the network simulated in fit04 uses OLSR and receives 
multicast packets sent from fit03 using VLC, the command is:

python3 ns3-scenario.py --vlc --multicast --olsr 


Additional details:

1) The server node and client node for ns-3 scenario can be mentioned using the arguments, 
--server and --client.
2) The target ns-3 simulated node, where the tap device is to be created can be mentioned 
using the argument --target.
3) The duration for which ns-3 simulation has to run on the client node can be mentioned 
using the argument --duration.
4) If images have to be loaded on the server and client nodes, -l has to be used.

For example, to have fit01 as the server node and fit02 as the client node, with ns-3 
simulated node with IP address 10.1.1.3 as the target, we use the command: (images are 
loaded on fit01 and fit02)
python3 ns3-scenario.py --server=1 --client=2 --target=3 -l

Here, fit01 will ping the ns-3 simulated node with IP address 10.1.1.3, which is running 
on fit02. The ns-3 network topology would be CSMA channel.



Output:

1) The script retrieves pcap file generated for the target ns-3 simulated node to the 
local machine.
2) tcpdump output at tap0 on the client node is also retrieved at the local machine. 
(currently gives output only for CSMA channel)
