/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2018 INRIA
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Author: Indukala Naladala <indukala.naladala@inria.fr>
 *
 */

// Network Topology: 
//
//  +----------+
//  |   fit01  |
//  |          |
//  |          |
//  |          |
//  |          |
//  +----------+
//    |           n0            n1            n2            n3
//    |           +--------+    +--------+    +--------+    +--------+
//    +-----------|  emu   |    |        |    |        |    |        |
//         data   |        |    |        |    |        |    |        |
//    192.168.2.0 +--------+    +--------+    +--------+    +--------+
//                |  CSMA  |    |  CSMA  |    |  CSMA  |    |  CSMA  |
//                +--------+    +--------+    +--------+    +--------+
//                   |             |             |             |
//                   |             |             |             |
//                   |             |             |             |
//                   ===========================================
//                                 CSMA LAN 10.1.1.0
//                                    (in fit02)
//
// fit01 and fit02 are two real nodes in R2lab. n0, n1, n2 and n3 are ns-3 
// simulated nodes runnning on fit02. To send multicast packets from fit01  
// to the ns-3 simulated nodes in fit02 execute these commands in fit01:
//     # turn-on-data 
//     # route add -net 10.1.1.0 gw 192.168.2.2 netmask 255.255.255.0 dev data 
//       (to add route in fit01 to send packets to 10.1.1.0)
//     # apt install smcroute
// fit02:
//     # turn-on-data
//     # ifconfig data promisc up
//
//  Execute the program in fit02:
//     # ./waf --run "scratch/multicast-csma"
//  and send multicast packets from fit01 using the command:
//     #  mcsender -t16 -idata 225.1.2.4:1234
//  
//  It is essential for the program in fit02 to be running while we send
//  packets from multicast sender at fit01.  
//


#include "ns3/abort.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/fd-net-device-module.h"
#include "ns3/csma-module.h"
#include "ns3/applications-module.h"
#include "ns3/internet-apps-module.h"
#include "ns3/ipv4-static-routing-helper.h"
#include "ns3/ipv4-list-routing-helper.h"
#include "ns3/tap-bridge-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("Send multicast packets to CSMA channel in ns-3 and R2lab");

int
main (int argc, char *argv[])
{
  NS_LOG_INFO ("Ping simulated node in ns-3 from real node in R2lab");

  std::string deviceName ("data");
  int remote_node = 1, local_node = 2;
  std::string remote ("192.168.2.");
  std::string local ("192.168.2.");
  std::string mode = "UseLocal";
  std::string tapName = "tap0";  
  bool multicast_on = false;
  double stopTime = 22;
  int dstnNode = 2;
  
  // 
  // Allow the user to override any of the defaults at run-time, via command
  // -line arguments
  //
  CommandLine cmd;
  cmd.AddValue ("stopTime", "Stop time (seconds)", stopTime);
  cmd.AddValue ("dstnNode", "Destination Node", dstnNode);
  cmd.AddValue ("remote", "Remote Node", remote_node);
  cmd.AddValue ("local", "Local Node", local_node);
  cmd.AddValue ("multicast", "Multicast Option", multicast_on);
  cmd.Parse (argc, argv);
  remote = remote + std::to_string(remote_node);
  local = local + std::to_string(local_node);


  Ipv4Address remoteIp (remote.c_str ());
  Ipv4Address localIp (local.c_str ());

  Ipv4Mask localMask ("255.255.255.0");

  //
  // Since we are using a real piece of hardware we need to use the realtime
  // simulator.
  //
  GlobalValue::Bind ("SimulatorImplementationType", StringValue ("ns3::RealtimeSimulatorImpl"));

  //
  // Since we are going to be talking to real-world machines, we need to enable
  // calculation of checksums in our protocols.
  //
  GlobalValue::Bind ("ChecksumEnabled", BooleanValue (true));

  NS_LOG_INFO ("Create Node");
  NodeContainer n;
  n.Create(1);
  Ptr<Node> node = n.Get(0);
  NodeContainer m;
  m.Add(n.Get(0));
  m.Create(3);
  Ptr<Node> ncheck = m.Get(3);

  //
  // Create an emu device, allocate a MAC address and point the device to the 
  // Linux device name.  The device needs a transmit queueing discipline so
  // create a droptail queue and give it to the device.  Finally, "install" 
  // the device into the node.
  //
  // The ns-3 allocated MAC address will be sent out over your network since 
  // the emu net device will spoof it. 
  //
  NS_LOG_INFO ("Create Device");
  EmuFdNetDeviceHelper emu;
  emu.SetDeviceName (deviceName);
  NetDeviceContainer devices = emu.Install (node);
  Ptr<NetDevice> device = devices.Get (0);
  device->SetAttribute ("Address", Mac48AddressValue (Mac48Address::Allocate ()));

  CsmaHelper csma;
  csma.SetChannelAttribute ("DataRate", DataRateValue (DataRate (5000000)));
  csma.SetChannelAttribute ("Delay", TimeValue (MilliSeconds (2)));

  NetDeviceContainer nd = csma.Install (m);

  // Add default Internet stack to the node.
  NS_LOG_INFO ("Add Internet Stack");
  InternetStackHelper internetStackHelper;
  internetStackHelper.Install (m);

  NS_LOG_INFO ("Create IPv4 Interface");
  Ptr<Ipv4> ipv4 = node->GetObject<Ipv4> ();
  uint32_t interface = ipv4->AddInterface (device);
  Ipv4InterfaceAddress address = Ipv4InterfaceAddress (localIp, localMask);
  ipv4->AddAddress (interface, address);
  ipv4->SetMetric (interface, 1);
  ipv4->SetUp (interface);

  Ipv4Address gateway ("0.0.0.0");

  Ipv4StaticRoutingHelper ipv4RoutingHelper;
  Ptr<Ipv4StaticRouting> staticRouting = ipv4RoutingHelper.GetStaticRouting (ipv4);
  staticRouting->SetDefaultRoute (gateway, interface);

  NS_LOG_INFO ("Assign IP Addresses.");
  Ipv4AddressHelper ipv4Addr;
  ipv4Addr.SetBase ("10.1.1.0", "255.255.255.0");
  ipv4Addr.Assign (nd);

  Ipv4GlobalRoutingHelper::PopulateRoutingTables ();
  
  if(multicast_on)
  {
  Ipv4Address multicastGroup ("225.1.2.4");

  // Now, we will set up multicast routing.  We need to do three things:
  // 1) Configure a (static) multicast route on node n0
  // 2) Set up a default multicast route on the node n0 
  // 3) Have node n4 join the multicast group
  // We have a helper that can help us with static multicast
  Ipv4StaticRoutingHelper multicast;

  // 1) Configure a (static) multicast route on node n0 (multicastRouter)
  Ptr<Node> multicastRouter = n.Get (0);  // The node in question
  Ptr<NetDevice> inputIf = devices.Get (0);  // The input NetDevice
  NetDeviceContainer outputDevices;  // A container of output NetDevices
  outputDevices.Add (nd.Get (0));  // (we only need one NetDevice here)

  multicast.AddMulticastRoute (multicastRouter, remoteIp, 
                               multicastGroup, inputIf, outputDevices);
  
  // 2) Set up a default multicast route on the sender n0 
  Ptr<Node> sender = n.Get (0);
  Ptr<NetDevice> senderIf = devices.Get (0);
  multicast.SetDefaultMulticastRoute (sender, senderIf);
  }
  else
  {
   NS_LOG_INFO ("Create V4Ping Appliation");
  Ptr<V4Ping> app = CreateObject<V4Ping> ();
  app->SetAttribute ("Remote", Ipv4AddressValue (remoteIp));
  app->SetAttribute ("Verbose", BooleanValue (true) );
  ncheck->AddApplication (app);
  app->SetStartTime (Seconds (1.0));
  app->SetStopTime (Seconds (21.0));

  }
 
  TapBridgeHelper tapBridge;
  tapBridge.SetAttribute ("Mode", StringValue (mode));
  tapBridge.SetAttribute ("DeviceName", StringValue (tapName));
  tapBridge.Install (m.Get (dstnNode), nd.Get (dstnNode));

  //
  // Enable a promiscuous pcap trace to see what is coming and going on our device.
  //
  emu.EnablePcap ("emu-ping", device, true);
  csma.EnablePcapAll ("packets", true);

  //
  // Now, do the actual emulation.
  //
  NS_LOG_INFO ("Run Emulation.");
  Simulator::Stop (Seconds (stopTime));
  Simulator::Run ();
  Simulator::Destroy ();
  NS_LOG_INFO ("Done.");
}


 

