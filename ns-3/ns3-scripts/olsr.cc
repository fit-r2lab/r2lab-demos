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

/*
 * Network Topology:
 *
 *       |--------data--------|   |------ OLSR ------|  
 *       A                      B ))))            (((( C
 * 192.168.2.1      192.168.2.2   10.1.1.1        10.1.1.4   
 *    (fit01)               (in fit02)            (in fit02)
 *
 *
 * This example program allows one to run ns-3 OLSR under a typical 
 * random waypoint mobility model. Packets are sent from multicast 
 * sender at fit01 to the to the ns-3 simulated nodes at fit02. 
 *
 * The number of ns-3 simulated nodes is 4. 
 * (IP addresses: 10.1.1.1 to 10.1.1.4)
 *
 * Nodes move according to RandomWaypointMobilityModel with a speed of
 * 1 m/s and no pause time within a 10x10 m region.  The WiFi is
 * in ad hoc mode with a 2 Mb/s rate (802.11b) and a Friis loss model.
 * The transmit power is set to 30 dBm.
 *
 * It is possible to change the mobility and density of the network by
 * directly modifying the speed and the number of nodes.  It is also
 * possible to change the characteristics of the network by changing
 * the transmit power (as power increases, the impact of mobility
 * decreases and the effective density increases).
 * 
 *
 * Execute the following commands in fit01:
 *   # turn-on-data 
 *   # route add -net 10.1.1.0 gw 192.168.2.2 netmask 255.255.255.0 dev data 
 *    (to add route in fit01 to send packets to 10.1.1.0)
 *   # apt install smcroute
 *
 * fit02:
 *     # turn-on-data
 *     # ifconfig data promisc up
 *
 *  Execute the program in fit02:
 *     # ./waf --run "scratch/multicast-olsr"
 *  and send multicast packets from fit01 using the command:
 *     #  mcsender -t16 -idata 225.1.2.4:1234
 *  
 *  It is essential for the program in fit02 to be running while we send
 *  packets from multicast sender at fit01.  
 *
 */

#include <fstream>
#include <iostream>
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/olsr-module.h"
#include "ns3/applications-module.h"
#include "ns3/internet-apps-module.h"
#include "ns3/ipv4-static-routing-helper.h"
#include "ns3/ipv4-list-routing-helper.h"
#include "ns3/fd-net-device-module.h"
#include "ns3/yans-wifi-helper.h"
#include "ns3/tap-bridge-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("Send multicast packets using OLSR protocol in ns-3 and R2lab");

class RoutingExperiment
{
public:
  RoutingExperiment ();
  void Run (int nSinks, double txp, std::string remote, std::string local, double stopTime, int dstnNode, bool multicast_on);

private:
  Ptr<Socket> SetupPacketReceive (Ipv4Address addr, Ptr<Node> node);
  void ReceivePacket (Ptr<Socket> socket);
  uint32_t port;
  uint32_t bytesTotal;
  uint32_t packetsReceived;

  int m_nSinks;
  double m_txp;
  bool m_traceMobility;
};

RoutingExperiment::RoutingExperiment ()
  : port (9),
    bytesTotal (0),
    packetsReceived (0),
    m_traceMobility (false)
{
}

void
RoutingExperiment::ReceivePacket (Ptr<Socket> socket)
{
  Ptr<Packet> packet;
  Address senderAddress;
  while ((packet = socket->RecvFrom (senderAddress)))
    {
      bytesTotal += packet->GetSize ();
      packetsReceived += 1;
    }
}

Ptr<Socket>
RoutingExperiment::SetupPacketReceive (Ipv4Address addr, Ptr<Node> node)
{
  TypeId tid = TypeId::LookupByName ("ns3::UdpSocketFactory");
  Ptr<Socket> sink = Socket::CreateSocket (node, tid);
  InetSocketAddress local = InetSocketAddress (addr, port);
  sink->Bind (local);
  sink->SetRecvCallback (MakeCallback (&RoutingExperiment::ReceivePacket, this));

  return sink;
}

int
main (int argc, char *argv[])
{
  RoutingExperiment experiment;

  int nSinks = 2;
  double txp = 30;

  int remote_node = 1, local_node = 2;
  std::string remote ("192.168.2.");
  std::string local ("192.168.2.");
  double stopTime = 200;
  int dstnNode = 2;
  bool multicast_on = false;
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

  experiment.Run (nSinks, txp, remote, local, stopTime, dstnNode, multicast_on);
}
 
void
RoutingExperiment::Run (int nSinks, double txp, std::string remote, std::string local, double stopTime, int dstnNode, bool multicast_on)

{
  m_nSinks = nSinks;
  m_txp = txp;

  int nWifis = 4;

  std::string rate ("256bps");
  std::string phyMode ("DsssRate11Mbps");
  int nodeSpeed = 1; //in m/s
  int nodePause = 0; //in s
  std::string mode = "UseLocal";
  std::string tapName = "tap0";

  std::string deviceName ("data");
  //Set Non-unicastMode rate to unicast mode
  Config::SetDefault ("ns3::WifiRemoteStationManager::NonUnicastMode",StringValue (phyMode));

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

  NS_LOG_INFO ("Create Nodes");
  NodeContainer nc;
  nc.Create(1);
  Ptr<Node> node = nc.Get(0);
  NodeContainer simpleadhocNodes;
  simpleadhocNodes.Create (nWifis-1);
  NodeContainer adhocNodes;
  adhocNodes.Add(node);
  adhocNodes.Add(simpleadhocNodes);
  Ptr<Node> ncheck = adhocNodes.Get(3); //To ping real node from simulated node with default IP Address 10.1.1.2


  Ipv4Address remoteIp (remote.c_str ());
  Ipv4Address localIp (local.c_str ());

  Ipv4Mask localMask ("255.255.255.0");
  NS_LOG_INFO ("Create Device");
  EmuFdNetDeviceHelper emu;
  emu.SetDeviceName (deviceName);
  NetDeviceContainer devices = emu.Install (node);
  Ptr<NetDevice> device = devices.Get (0);
  device->SetAttribute ("Address", Mac48AddressValue (Mac48Address::Allocate ()));

  // setting up wifi phy and channel using helpers
  WifiHelper wifi;
  wifi.SetStandard (WIFI_PHY_STANDARD_80211b);

  YansWifiPhyHelper wifiPhy =  YansWifiPhyHelper::Default ();
  YansWifiChannelHelper wifiChannel;
  wifiChannel.SetPropagationDelay ("ns3::ConstantSpeedPropagationDelayModel");
  wifiChannel.AddPropagationLoss ("ns3::FriisPropagationLossModel");
  wifiPhy.SetChannel (wifiChannel.Create ());

  // Add a mac and disable rate control
  WifiMacHelper wifiMac;
  wifi.SetRemoteStationManager ("ns3::ConstantRateWifiManager",
                                "DataMode",StringValue (phyMode),
                                "ControlMode",StringValue (phyMode));

  wifiPhy.Set ("TxPowerStart",DoubleValue (txp));
  wifiPhy.Set ("TxPowerEnd", DoubleValue (txp));

  wifiMac.SetType ("ns3::AdhocWifiMac");
  NetDeviceContainer adhocDevices = wifi.Install (wifiPhy, wifiMac, adhocNodes);

  MobilityHelper mobilityAdhoc;
  int64_t streamIndex = 0; // used to get consistent mobility across scenarios

  ObjectFactory pos;
  pos.SetTypeId ("ns3::RandomRectanglePositionAllocator");
  pos.Set ("X", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=10.0]"));
  pos.Set ("Y", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=10.0]"));

  Ptr<PositionAllocator> taPositionAlloc = pos.Create ()->GetObject<PositionAllocator> ();
  streamIndex += taPositionAlloc->AssignStreams (streamIndex);

  std::stringstream ssSpeed;
  ssSpeed << "ns3::UniformRandomVariable[Min=0.0|Max=" << nodeSpeed << "]";
  std::stringstream ssPause;
  ssPause << "ns3::ConstantRandomVariable[Constant=" << nodePause << "]";
  mobilityAdhoc.SetMobilityModel ("ns3::RandomWaypointMobilityModel",
                                  "Speed", StringValue (ssSpeed.str ()),
                                  "Pause", StringValue (ssPause.str ()),
                                  "PositionAllocator", PointerValue (taPositionAlloc));
  mobilityAdhoc.SetPositionAllocator (taPositionAlloc);
  mobilityAdhoc.Install (adhocNodes);
  streamIndex += mobilityAdhoc.AssignStreams (adhocNodes, streamIndex);
  NS_UNUSED (streamIndex); // From this point, streamIndex is unused
  OlsrHelper olsr;
  Ipv4ListRoutingHelper list;
  Ipv4StaticRoutingHelper ipv4RoutingHelper;
  InternetStackHelper internet;

  olsr.ExcludeInterface (adhocNodes.Get (0), 1); //Specify the first node's emu device as a non-OLSR device.

  list.Add (ipv4RoutingHelper, 10);
  list.Add (olsr, 20);
  internet.SetRoutingHelper (list);
  internet.Install (adhocNodes);

  NS_LOG_INFO ("Create IPv4 Interface");
  Ptr<Ipv4> ipv4 = node->GetObject<Ipv4> ();
  uint32_t interface = ipv4->AddInterface (device);
  Ipv4InterfaceAddress address = Ipv4InterfaceAddress (localIp, localMask);
  ipv4->AddAddress (interface, address);
  ipv4->SetMetric (interface, 1);
  ipv4->SetUp (interface);

  Ipv4Address gateway ("0.0.0.0");
  Ptr<Ipv4StaticRouting> staticRouting = ipv4RoutingHelper.GetStaticRouting (ipv4);
  staticRouting->SetDefaultRoute (gateway, interface);

  NS_LOG_INFO ("Assigning IP address");

  Ipv4AddressHelper addressAdhoc;
  addressAdhoc.SetBase ("10.1.1.0", "255.255.255.0");
  Ipv4InterfaceContainer adhocInterfaces;
  adhocInterfaces = addressAdhoc.Assign (adhocDevices);

  Ptr<Ipv4> stack = adhocNodes.Get (0)->GetObject<Ipv4> ();
  Ptr<Ipv4RoutingProtocol> rp_Gw = (stack->GetRoutingProtocol ());
  Ptr<Ipv4ListRouting> lrp_Gw = DynamicCast<Ipv4ListRouting> (rp_Gw);

  Ptr<olsr::RoutingProtocol> olsrrp_Gw;

  for (uint32_t i = 0; i < lrp_Gw->GetNRoutingProtocols ();  i++)
    {
      int16_t priority;
      Ptr<Ipv4RoutingProtocol> temp = lrp_Gw->GetRoutingProtocol (i, priority);
      if (DynamicCast<olsr::RoutingProtocol> (temp))
        {
          olsrrp_Gw = DynamicCast<olsr::RoutingProtocol> (temp);
        }
    }
 
 // Add the required routes into the Ipv4StaticRouting Protocol instance
 // and have the node generate HNA messages for all these routes
 // which are associated with non-OLSR interfaces specified above.
  Ptr<Ipv4StaticRouting> hnaEntries = Create<Ipv4StaticRouting> ();

  // Add the required routes into the Ipv4StaticRouting Protocol instance
  // and have the node generate HNA messages for all these routes
  // which are associated with non-OLSR interfaces specified above.
  hnaEntries->AddNetworkRouteTo (Ipv4Address ("192.168.2.0"), Ipv4Mask ("255.255.255.0"), uint32_t (1), uint32_t (1));
  olsrrp_Gw->SetRoutingTableAssociation (hnaEntries);
  
  if(multicast_on)
  {
  Ipv4Address multicastGroup ("225.1.2.4");

  // Now, we will set up multicast routing.  We need to do three things:
  // 1) Configure a (static) multicast route on node B
  // 2) Set up a default multicast route on the node B 
  // 3) Have node  join the multicast group
  // We have a helper that can help us with static multicast
  Ipv4StaticRoutingHelper multicast;

  // 1) Configure a (static) multicast route on node B (multicastRouter)
  Ptr<Node> multicastRouter = nc.Get (0);  // The node in question
  Ptr<NetDevice> inputIf = devices.Get (0);  // The input NetDevice
  NetDeviceContainer outputDevices;  // A container of output NetDevices
  outputDevices.Add (adhocDevices.Get (0));  // (we only need one NetDevice here)

  multicast.AddMulticastRoute (multicastRouter, remoteIp, 
                               multicastGroup, inputIf, outputDevices);

  // 2) Set up a default multicast route on the node B
  Ptr<Node> sender = nc.Get (0);
  Ptr<NetDevice> senderIf = devices.Get (0);
  multicast.SetDefaultMulticastRoute (sender, senderIf);
  }

 else 
  {
 //To ping real node fit01 from simulated node with default IP address 10.1.1.2
  NS_LOG_INFO ("Create V4Ping Appliation");
  Ptr<V4Ping> app = CreateObject<V4Ping> ();
  app->SetAttribute ("Remote", Ipv4AddressValue (remoteIp));
  app->SetAttribute ("Verbose", BooleanValue (true) );
  ncheck->AddApplication (app);
  app->SetStartTime (Seconds (1.0));
  app->SetStopTime (Seconds (21.0));
  }

  for (int i = 0; i < nSinks; i++)
    {
      Ptr<Socket> sink = SetupPacketReceive (adhocInterfaces.GetAddress (i), adhocNodes.Get (i));
    }
  
  TapBridgeHelper tapBridge;
  tapBridge.SetAttribute ("Mode", StringValue (mode));
  tapBridge.SetAttribute ("DeviceName", StringValue (tapName));
  tapBridge.Install (adhocNodes.Get (dstnNode), adhocDevices.Get (dstnNode));
 
  // DEBUG: To print all routing tables
  /*
  Ipv4GlobalRoutingHelper g;
  Ptr<OutputStreamWrapper> routingStream = Create<OutputStreamWrapper>
  ("dynamic-global-routing.routes", std::ios::out);
  g.PrintRoutingTableAllAt (Seconds (12), routingStream);
  */

  emu.EnablePcapAll("emu",true);
  wifiPhy.EnablePcapAll("packets",true);

  NS_LOG_INFO ("Run Simulation.");

  Simulator::Stop (Seconds (stopTime));
  Simulator::Run ();

  Simulator::Destroy ();
}

