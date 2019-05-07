/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2011 INRIA
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
 *  Authors: Frederic Urbani <frederic.urbani@inria.fr>
 *   and tap parts from fd-tap-p2p.c from Alina Quereilhac <alina.quereilhac@sophia.inria.fr
*/

#include "ns3/network-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/internet-apps-module.h" // added by hayamizu on 8 April 2019
#include "ns3/applications-module.h" // added by hayamizu on 8 April 2019
#include "ns3/network-module.h" // added by hayamizu on 8 April 2019
// #include "ns3/dce-module.h" // commented by hayamizu on 8 April 2019
#include "ns3/tap-bridge-module.h"
#include "ns3/point-to-point-helper.h"
#include "ns3/csma-helper.h"

//kazu adds
#include "ns3/dce-module.h"
#include "ns3/fd-net-device-module.h"

#include <iostream>
#include <fstream>
#include <sys/stat.h>
#include <sys/wait.h>
#include <string.h>
#include <list>
#include <errno.h>

// added by hayamizu on 11 April 2019 for wifi-mobility scenario /////
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/bridge-helper.h"
///////////////////////////////////////////

////////////////////////////////////////////////////////////////////////////
//
//  +----------+
//  | external |
//  |  Linux   |
//  |   Host   |
//  |          |
//  | "thetap" |
//  +----------+
//  | 10.1.1.1 |
//  +----------+
//       |           node0         node1
//       |       +----------+    +----------+
//       +-------| fd-net   |    |          |
//               |          |    |          |
//               +----------+    +----------+
//               |  CSMA    |    |  CSMA    |
//               +----------+    +----------+
//               | 10.0.0.1 |    | 10.0.0.2 | udp-echo-server listening on port 2000
//               +----------+    +----------+
//                     |               |
//                     |               |
//                     |               |
//                     =================
//                      CSMA LAN 10.0.0
//
//////////////////////////////////////////////////////////////////////////////

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("v4-ping-test");

std::string nexthop = "192.168.2.6";
//std::string nexthop = "192.168.2.19";

static void PrintPositions (std::string s, Ptr<Node> sta)
{
  Ptr<MobilityModel> mob = sta->GetObject<MobilityModel>();
  Vector pos = mob->GetPosition ();
  NS_LOG_INFO ("time=	" << Simulator::Now().GetSeconds() << "	" << s << "	" << pos.x << "," << pos.y);
  Simulator::Schedule (Seconds(1.0), (&PrintPositions), s, sta);
}
  


static void
SetPosition (Ptr<Node> node, Vector position)
{
  Ptr<MobilityModel> mobility = node->GetObject<MobilityModel> ();
  mobility->SetPosition (position);
}

static void
SetPositionVelocity (Ptr<Node> node, Vector position, Vector velocity)
{
  Ptr<ConstantVelocityMobilityModel> mobility = node->GetObject<ConstantVelocityMobilityModel> ();
  mobility->SetPosition (position);
  mobility->SetVelocity (velocity);
}



int
main (int argc, char *argv[])
{
  std::string mode = "ConfigureLocal";
  //std::string mode = "UseLocal";
  std::string tapName = "thetap";
	std::string pubAddr = "";

  CommandLine cmd;
  cmd.AddValue ("mode", "Mode setting of TapBridge", mode);
  cmd.AddValue ("tapName", "Name of the OS tap device", tapName);
  cmd.AddValue ("pubAddr", "publisher IP-v4 address", pubAddr);
  cmd.Parse (argc, argv);

	if(pubAddr == ""){
		fprintf(stderr, "Specify Publisher Address: ./waf --run \"dce-tcp-test --pubAddr=XXX\"\n");
		exit(-1);	
	}else{
		std::cout << "Publisher Addr: " << pubAddr << std::endl;
	}

  LogComponentEnable ("v4-ping-test", LOG_LEVEL_ALL);
  // LogComponentEnable ("Ipv4GlobalRouting", LOG_LEVEL_ALL);
  // LogComponentEnable ("GlobalRouter", LOG_LEVEL_ALL);
  // LogComponentEnable ("V4Ping", LOG_LEVEL_ALL);
  // LogComponentEnable ("Ipv4StaticRouting", LOG_LEVEL_ALL);
  // LogComponentEnable ("TapBridge", LOG_LEVEL_ALL);
  // LogComponentEnable ("Ipv4AddressHelper", LOG_LEVEL_ALL);
  // LogComponentEnable ("BridgeHelper", LOG_LEVEL_ALL);
  // LogComponentEnable ("BridgeNetDevice", LOG_LEVEL_ALL);
  // LogComponentEnable ("Ipv4Address", LOG_LEVEL_ALL);
  ///////////////////////////////////////////

  GlobalValue::Bind ("SimulatorImplementationType", StringValue ("ns3::RealtimeSimulatorImpl"));
  GlobalValue::Bind ("ChecksumEnabled", BooleanValue (true));

  NodeContainer nodes;
  nodes.Create (5);
  
  Ptr<Node> TAP = nodes.Get(0); // tap-bridge node
  Ptr<Node> SW = nodes.Get(1); // switch
  Ptr<Node> AP1 = nodes.Get(2);
  Ptr<Node> AP2 = nodes.Get(3);
  Ptr<Node> STA = nodes.Get(4);
  
  NodeContainer apNodes;
  apNodes.Add (AP1);
  apNodes.Add (AP2);

  NodeContainer csmaNodes;
  csmaNodes.Add (TAP); // emu (gw)
  csmaNodes.Add (SW);
  csmaNodes.Add (AP1);
  csmaNodes.Add (AP2);
  NodeContainer wifiNodes;
  wifiNodes.Add (AP1);
  wifiNodes.Add (AP2);
  wifiNodes.Add (STA);

  //kazu adds:
  DceManagerHelper dceManager;
  dceManager.Install (nodes);


    
  NetDeviceContainer csmaDev[apNodes.GetN()+1];
  // NetDeviceContainer *csmaDev = new NetDeviceContainer[apNodes.GetN()+1];

  InternetStackHelper stack;
  // stack.Install (csmaNodes);
  CsmaHelper csma, csma2;
  csma.SetChannelAttribute ("DataRate", DataRateValue (100000000));
  csma.SetChannelAttribute ("Delay", TimeValue (MilliSeconds (1)));
  csma2.SetChannelAttribute ("DataRate", DataRateValue (100000000));
  csma2.SetChannelAttribute ("Delay", TimeValue (MilliSeconds (1)));

  Ipv4AddressHelper addresses;
  //addresses.SetBase ("10.0.0.0", "255.255.255.0");
  addresses.SetBase ("10.1.1.0", "255.255.255.0");

  stack.Install (apNodes);
  stack.Install (TAP);
  stack.Install (SW);

  for (uint32_t i = 0; i < apNodes.GetN(); ++i)
    {
      csmaDev[i] = csma.Install (NodeContainer(apNodes.Get(i), SW));
    }
  csmaDev[2] = csma2.Install (NodeContainer (TAP, SW));
  
  BridgeHelper switch0;
  NetDeviceContainer switchDev;
  for (uint32_t i = 0; i < 3; ++i) // # of csma between SW-APs + # of csma2 between SW-TAP (2 + 1 = 3)
    {
      switchDev.Add (csmaDev[i].Get(1));
    }
  switch0.Install (SW, switchDev);

  Ipv4InterfaceContainer tapInterface = addresses.Assign (csmaDev[2].Get(0));
  Ptr<NetDevice> gw_device = csmaDev[2].Get(0); // ToDo
  
  ///// setting wifi
  // for STA
  YansWifiPhyHelper wifiPhy = YansWifiPhyHelper::Default ();
  wifiPhy.SetPcapDataLinkType (YansWifiPhyHelper::DLT_IEEE802_11_RADIO);
  YansWifiChannelHelper wifiChannel = YansWifiChannelHelper::Default ();
  wifiPhy.SetChannel (wifiChannel.Create());

  WifiHelper wifi;
  wifi.SetStandard (WIFI_PHY_STANDARD_80211g);
  WifiMacHelper wifiMac;

  NetDeviceContainer staDev;
  Ipv4InterfaceContainer staInterface;
  stack.Install (STA);
  MobilityHelper mobility;
  mobility.SetMobilityModel ("ns3::ConstantVelocityMobilityModel");
  mobility.Install (STA);

  Ssid ssid = Ssid ("wifi-default");
  wifiMac.SetType ("ns3::StaWifiMac",
                   "Ssid", SsidValue (ssid),
                   // "ScanType", EnumValue (StaWifiMac::ACTIVE),
                   // "QosSupported", BooleanValue (true),
                   "ActiveProbing", BooleanValue (true));
  staDev = wifi.Install (wifiPhy, wifiMac, STA);
  staInterface = addresses.Assign(staDev);
  SetPositionVelocity (STA, Vector (-50.0, 10.0, 0.0), Vector (10.0, 0.0, 0.0));
  // SetPositionVelocity (STA, Vector (0.0, 0.0, 0.0), Vector (0.0, 0.0, 0.0));

  //kazu test:
  Ipv4InterfaceAddress adr = STA->GetObject<Ipv4> ()->GetAddress(1,0); // (1,0), 1=index of ipinterfacePaier, j=interface address index (if interface has multiple addresses);
  //Ipv4InterfaceAddress adr = STA->GetObject<Ipv4> ()->GetAddress(2,0); 
  std::cout << "STA adr: " << adr << std::endl;

  // for AP
  for (uint32_t ap = 0; ap < apNodes.GetN(); ++ap)
    // for (uint32_t ap = 0; ap < 1; ++ap)
    {
      NetDeviceContainer apDev;
      Ipv4InterfaceContainer apInterface;
      MobilityHelper mobility_ap;
      BridgeHelper bridge;
      mobility_ap.SetPositionAllocator ("ns3::GridPositionAllocator",
                                     "MinX", DoubleValue (0.0),
                                     "MinY", DoubleValue (0.0),
                                     "DeltaX", DoubleValue (5.0),
                                     "DeltaY", DoubleValue (5.0),
                                     "GridWidth", UintegerValue (1),
                                     "LayoutType", StringValue("RowFirst"));
      mobility_ap.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
      mobility_ap.Install (apNodes.Get(ap));
      wifiMac.SetType ("ns3::ApWifiMac", "Ssid", SsidValue(ssid));
      wifiPhy.Set ("ChannelNumber", UintegerValue (1));
      // wifiPhy.Set ("ChannelNumber", UintegerValue (1+(ap%3)*5));
      // wifiPhy.Set ("ChannelNumber", UintegerValue (ap*10 + 1));
      apDev = wifi.Install (wifiPhy, wifiMac, apNodes.Get(ap));

      NetDeviceContainer bridgeDev;
      bridgeDev = bridge.Install (apNodes.Get(ap), NetDeviceContainer (apDev, csmaDev[ap].Get(0)));
      // apInterface = addresses.Assign (bridgeDev); // assign AP IP address to bridge, not wifi
      // apInterface = addresses.Assign(apDev); // not apDev
      // SetPosition (apNodes.Get(ap), Vector (ap*150.0, 0.0, 0.0));
      SetPosition (apNodes.Get(ap), Vector (ap*300.0, 0.0, 0.0));

      // list position
      Ptr<MobilityModel> mob = apNodes.Get(ap)->GetObject<MobilityModel>();
      Vector pos = mob->GetPosition ();
      NS_LOG_INFO ("AP" << apNodes.Get(ap)->GetId() - 1 << "'s location = (" << pos.x << "," << pos.y << ")");
    }
 
  EmuFdNetDeviceHelper emu;
  std::string deviceName ("data");
  //std::string deviceName ("eth0");
  // std::string deviceName ("wlxb0c74578f22d");
  emu.SetDeviceName (deviceName);

  NetDeviceContainer emudevices = emu.Install (TAP);
  Ptr<NetDevice> device = emudevices.Get (0);
  device->SetAttribute ("Address", Mac48AddressValue (Mac48Address::Allocate ()));
 
  // IP setting of TAP node
  Ptr<Ipv4> ipv4_tap = TAP->GetObject<Ipv4> ();
  uint32_t interface = ipv4_tap->AddInterface (device);
  std::string local("192.168.2.32");// same subnet(segment) with eno1
  Ipv4Address localIp (local.c_str());
  Ipv4Mask localMask ("255.255.255.0");
  Ipv4InterfaceAddress address = Ipv4InterfaceAddress (localIp, localMask);
  ipv4_tap->AddAddress (interface, address);
  ipv4_tap->SetMetric (interface, 1);
  ipv4_tap->SetUp (interface);
  Ipv4Address gateway ("0.0.0.0");
  Ipv4StaticRoutingHelper ipv4RoutingHelper;
  Ptr<Ipv4StaticRouting> staticRouting = ipv4RoutingHelper.GetStaticRouting (ipv4_tap);
  staticRouting->SetDefaultRoute (gateway, interface);

  /*  Ptr<Ipv4> ipv4_n1 = nodes.Get(1)->GetObject<Ipv4> ();
  uint32_t interface_n1 = ipv4_n1->AddInterface (devices.Get(1));
  std::string local_n1("10.0.0.2"); 
  Ipv4Address localIp_n1 (local_n1.c_str());
  Ipv4Mask localMask_n1 ("255.255.255.0");
  Ipv4InterfaceAddress address_n1 = Ipv4InterfaceAddress (localIp_n1, localMask_n1);
  ipv4_n1->AddAddress (interface_n1, address_n1);
  ipv4->SetMetric (interface_n1, 1);
  ipv4->SetUp (interface_n1);
  Ipv4Address gateway_n1 ("10.0.0.1");
  Ptr<Ipv4StaticRouting> staticRouting_n1 = ipv4RoutingHelper.GetStaticRouting (ipv4_n1);
  staticRouting_n1->SetDefaultRoute (gateway_n1, interface_n1);
  */
  /*
  Ptr<Ipv4> ipv4n1 = nodes.Get(1)->GetObject<Ipv4> ();
  Ipv4Address gatewayn1 ("10.0.0.1");
  Ptr<Ipv4StaticRouting> staticRoutingn1 = ipv4RoutingHelper.GetStaticRouting (ipv4n1);
  uint32_t interfacen1 = ipv4n1->AddInterface ();
  staticRoutingn1->SetDefaultRoute (gatewayn1, 1);
  */

  Ptr<Ipv4> ipv4_sta;
  //set IP static routing to the gateway (node 0)
  ipv4_sta = STA->GetObject<Ipv4> ();
  uint32_t interface_sta = 1; // 1 is index of net-device, 0=loopback, 1=ethernet/wireless
  //Ipv4Address gateway_sta ("10.0.0.1");
  Ipv4Address gateway_sta ("10.1.1.1");
  Ipv4StaticRoutingHelper ipv4RoutingHelper_sta;
  Ptr<Ipv4StaticRouting> staticRouting_sta = ipv4RoutingHelper_sta.GetStaticRouting (ipv4_sta);
  staticRouting_sta->SetDefaultRoute (gateway_sta, interface_sta);
  
  /*
  uint32_t nleaves = 3;
  Ptr<Ipv4> ipv4[nleaves+2];
  for (uint32_t i = 2; i < nleaves+2 ; ++i)
    {
      //set IP static routing to the gateway (node 0)
      ipv4[i] = nodes.Get(i)->GetObject<Ipv4> ();
      uint32_t interface_l = 1; // 1 is index of net-device, 0=loopback, 1=ethernet, 2=wireless
      Ipv4Address gateway_l ("10.0.0.1");
      Ipv4StaticRoutingHelper ipv4RoutingHelper_l;
      Ptr<Ipv4StaticRouting> staticRouting_l = ipv4RoutingHelper_l.GetStaticRouting (ipv4[i]);
      staticRouting_l->SetDefaultRoute (gateway_l, interface_l);
    }
  */
  /* written by matsuzono-san
  //set n1's static routing
  Ptr<Ipv4> ipv4n1 = nodes.Get(1)->GetObject<Ipv4> ();
  uint32_t n1interface = 1;
  Ipv4Address n1gateway ("10.0.0.1");
  Ipv4StaticRoutingHelper ipv4RoutingHelpern1;
  Ptr<Ipv4StaticRouting> staticRoutingn1 = ipv4RoutingHelpern1.GetStaticRouting (ipv4n1);
  staticRoutingn1->SetDefaultRoute (n1gateway, n1interface);
  */

  // Ipv4GlobalRoutingHelper::PopulateRoutingTables ();

  // Simulator::Schedule (Seconds(0.0), (&PrintPositions), "ap0", STA);

  
  // added by hayamizu on 8 April 2019 /////
#if 0
  NS_LOG_INFO ("Create V4Ping Appliation");
  uint32_t nApps = 1;
  Ptr<V4Ping> app[nApps];
  for (uint32_t i = 0; i < nApps; ++i)
    {
      app[i] = CreateObject<V4Ping> ();
    }
  Ptr<Node> ncheck = STA;
  NS_LOG_INFO ("PING from 10.0.0.2 -> 172.217.25.99 (google.co.jp)");
  app[0]->SetAttribute ("Remote", Ipv4AddressValue ("172.217.25.99"));
  app[0]->SetAttribute ("Verbose", BooleanValue (true) );
  ncheck->AddApplication (app[0]);
  app[0]->SetStartTime (Seconds (1.0));
  app[0]->SetStopTime (Seconds (49.9));
#endif
  

  TapBridgeHelper tapBridge;
  tapBridge.SetAttribute ("Mode", StringValue (mode));
  tapBridge.SetAttribute ("DeviceName", StringValue (tapName));
  tapBridge.Install (nodes.Get (0), gw_device);
  
  // goal
  // NS_LOG_INFO ("Create V4Ping Appliation");
  // Ptr<V4Ping> app = CreateObject<V4Ping> ();
  // Ptr<Node> ncheck = nodes.Get(1);
  // app->SetAttribute ("Remote", Ipv4AddressValue ("10.1.1.1"));
  // app->SetAttribute ("Remote", Ipv4AddressValue ("10.0.0.1"));
  // app->SetAttribute ("Remote", Ipv4AddressValue ("192.168.1.1"));
  // app->SetAttribute ("Remote", Ipv4AddressValue ("192.168.2.32"));
  // app->SetAttribute ("Remote", Ipv4AddressValue ("192.168.2.32"));
  // app->SetAttribute ("Verbose", BooleanValue (true) );
  // ncheck->AddApplication (app);
  // app->SetStartTime (Seconds (2.0));
  // app->SetStopTime (Seconds (21.0));
  /*
  // local ping
  Ptr<V4Ping> app_local = CreateObject<V4Ping> ();
  app_local->SetAttribute ("Remote", Ipv4AddressValue ("10.0.0.1"));
  app_local->SetAttribute ("Verbose", BooleanValue (true) );
  Ptr<Node> ncheck_local = nodes.Get(1);
  ncheck_local->AddApplication (app_local);
  app_local->SetStartTime (Seconds (6.0));
  app_local->SetStopTime (Seconds (10.0));
  // self ping (node 0)
  Ptr<V4Ping> app_self = CreateObject<V4Ping> ();
  app_self->SetAttribute ("Remote", Ipv4AddressValue ("10.0.0.1"));
  app_self->SetAttribute ("Verbose", BooleanValue (true) );
  Ptr<Node> ncheck_self = nodes.Get(0);
  ncheck_self->AddApplication (app_self);
  app_self->SetStartTime (Seconds (11.0));
  app_self->SetStopTime (Seconds (21.0));
  // self ping (node 1)
  Ptr<V4Ping> app_self = CreateObject<V4Ping> ();
  app_self->SetAttribute ("Remote", Ipv4AddressValue ("10.0.0.2"));
  app_self->SetAttribute ("Verbose", BooleanValue (true) );
  Ptr<Node> ncheck_self = nodes.Get(1);
  ncheck_self->AddApplication (app_self);
  app_self->SetStartTime (Seconds (2.0));
  app_self->SetStopTime (Seconds (21.0));
  */
  ///////////////////////////////////

  #if 1
  DceApplicationHelper dce;
  ApplicationContainer apps;

  dce.SetStackSize (1 << 20);

  // Launch iperf client on node 0
  dce.SetBinary ("iperf");
  dce.ResetArguments ();
  dce.ResetEnvironment ();
  dce.AddArgument ("-c");
  //dce.AddArgument ("192.168.2.33");
  dce.AddArgument (pubAddr.c_str());
  dce.AddArgument ("-i");
  dce.AddArgument ("1");
  //dce.AddArgument ("0.5");
  dce.AddArgument ("-p");
  dce.AddArgument ("80");
  dce.AddArgument ("--time");
  dce.AddArgument ("40");
  //if (useUdp)
  //  {
  //    dce.AddArgument ("-u");
  //    dce.AddArgument ("-b");
  //    dce.AddArgument (bandWidth);
  //}
  //apps = dce.Install (nodes.Get (0));
  //apps = dce.Install (nodes.Get (1));
  apps = dce.Install (STA);
  apps.Start (Seconds (1.0));
  apps.Stop (Seconds (45));
  #endif




  //Ipv4GlobalRoutingHelper::PopulateRoutingTables ();
  // Pcap
  emu.EnablePcap ("emu-ping", device, true);
  csma.EnablePcapAll ("packets", true);

  Simulator::Stop (Seconds (50.0));
  Simulator::Run ();
  Simulator::Destroy ();

  return 0;
}
