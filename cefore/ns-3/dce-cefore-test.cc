#include "ns3/network-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/dce-module.h"
#include "ns3/tap-bridge-module.h"
#include "ns3/point-to-point-helper.h"
#include "ns3/csma-helper.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"

//kazu adds
#include "ns3/fd-net-device-module.h"
#include "ns3/ipv4-static-routing-helper.h" // tmp
#include "ns3/ipv4-list-routing-helper.h"   // tmp


#include <iostream>
#include <fstream>
#include <sys/stat.h>
#include <sys/wait.h>
#include <string.h>
#include <list>
#include <errno.h>

using namespace ns3;
NS_LOG_COMPONENT_DEFINE ("DceTapWifiCefore");

#define ENABLE_AP_CACHE 1 // csmgrd in simulation is not stable, so not use....
#define MOBILITY 1 
//#define USE_M_OPTION 1 // cefgetfile finishes after getting 5000 chunks
//std::string maxChunk = "5382"; // cefgetfiles continues to receive the number of chunks when USE_M_OPTION=1.
 
// This is a cefgetfile param similar to tcp window size.
// During the download, the pipeline size is fixed in the current cefgetfile implementation. 
std::string PIPELINE = "32"; 
//std::string PIPELINE = "64"; 

// the name prefix that the remote node uses when caching a content
//std::string contentNamePrefix = "ccn:/realRemote"; 
std::string contentNamePrefix = "ccn:/streaming"; 

// server cefputfile
const char *ccnContentName = "ccn:/streaming/test"; // the content name of the "CacheFile".
//const char *InFile = "/tmp/CreatedCacheFile"; // the content name of the "CacheFile".
std::string outFile = "/tmp/tmp";
//const char *CacheFile = "./files-0/tmp/CreatedCacheFile"; // node-0 caches this file/data

std::string nexthop = "192.168.2.6"; //XXX
//std::string nexthop = "192.168.2.19"; //XXX

static void
SetPositionVelocity (Ptr<Node> node, Vector position, Vector velocity)
{
  Ptr<ConstantVelocityMobilityModel> mobility = node->GetObject<ConstantVelocityMobilityModel> ();
  mobility->SetPosition (position);
  mobility->SetVelocity (velocity);

  Vector pos = mobility->GetPosition ();

  std::cout << "nodeId-" << node->GetId() << " x =" << pos.x << " y =" << pos.y << std::endl;
}


#if 0
void
CreateCacheFile () // create a file to be cached by node-0 using cefputfile
{
  mkdir ("files-0/tmp", 0777);
  std::ofstream ofs (CacheFile, std::fstream::trunc);

  if(!ofs) {
    std::cerr << "cannot open " << CacheFile << std::endl;
    std::exit(1);
  }

  //ofs << "This is a message cached by node-1 for simple Test!!\n" ;
  #if 1
  for (int i=0; i<100; i++)
  //for (int i=0; i<60000; i++)
  {
    ofs << i ;
    ofs << " aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaabbbbbbbbbbbbbbbbbbbbbccccccccccccccccccc\n";
  }
  #endif

  ofs.close ();
}
#endif


void
CreateFib(int nodeId) {

  std::string folder ("./files-");
  std::ostringstream nodeStr;
  nodeStr << nodeId;
  folder = folder + nodeStr.str();
  
  std::string fileName = folder + "/usr/local/cefore/cefnetd.fib";
  std::ofstream ofs (fileName.c_str(), std::fstream::trunc);
  if(!ofs) {
    std::cerr << "cannot open " << fileName << std::endl;
    std::exit(1);
   }

	std::cout << "nexthop: " << nexthop << std::endl;

  if(nodeId == 3) // create wifi consumer's fib
  {
    std::cout << "Create Fib on node-" << nodeId << " (wifi-consumer):" << std::endl;
    std::string prefix = contentNamePrefix;
    
  
    std::string address1 = "10.2.2.1";
    std::string address2 = "10.2.2.2";
    std::cout << "\t" << prefix << " udp " << address1 << " " << address2 << std::endl; 

    //ofs << prefix << " udp " << address << std::endl;
    ofs << prefix << " udp " << address1 << " " << address2 << std::endl; 
  
  }else if (nodeId == 1){ // create AP1 fib
    
    std::cout << "Create Fib on node-" << nodeId << " (AP node):" << std::endl;
    std::string prefix = contentNamePrefix;
    //std::string address = "10.1.1.1";
    //std::string address = "133.69.36.80"; //XXX
    //std::string address = "192.168.2.6"; //XXX
    std::string address = nexthop; //XXX
    //std::string address = "192.168.2.25"; //XXX
    std::cout << "\t" << prefix << " udp " << address << std::endl; 
    
    ofs << prefix << " udp " << address << std::endl;
  
  }else if (nodeId == 2){ // create AP2 fib
 
    std::cout << "Create Fib on node-" << nodeId << " (AP node):" << std::endl;
    std::string prefix = contentNamePrefix;
    //std::string address = "10.1.1.1";
    //std::string address = "192.168.2.6"; //XXX
    std::string address = nexthop; //XXX
    //std::string address = "192.168.2.25"; //XXX
    std::cout << "\t" << prefix << " udp " << address << std::endl; 
    
    ofs << prefix << " udp " << address << std::endl;

  }else{
    
    std::cerr << "CreateFib(): bad nodeId: " << nodeId << std::endl;
    exit(1); 
  }


  ofs.close();
}

// change the cefnetd.conf to enable cefnetd to use csmgrd (cache daemon).
void
EnableCache (int nodeId){
  std::string folder ("./files-");
  std::ostringstream nodeStr;
  nodeStr << nodeId;
  folder = folder + nodeStr.str();
  std::string path = folder + "/usr/local/cefore/cefnetd.conf";

  std::ofstream ofs (path.c_str(), std::fstream::trunc);
  if(!ofs) {
    std::cerr << "cannot open " << path << std::endl;
    std::exit(1);
  }

  std::cout << "Enable node " << nodeId << " to use cache." << std::endl;
  //ofs << "USE_CACHE=1" ;
  ofs << "CS_MODE=1\nLOG_LEVEL=4\n" ;

  ofs.close ();
}

void
CopyCeforeConfig(int nodeId)
{
  std::string folder ("./files-");
  std::ostringstream nodeStr;
  nodeStr << nodeId;
  folder = folder + nodeStr.str();
  mkdir (folder.c_str(), 0777);
  folder = folder + "/usr";
  mkdir (folder.c_str(), 0777);
  folder = folder + "/local";
  mkdir (folder.c_str(), 0777);
  folder = folder + "/cefore";
  mkdir (folder.c_str(), 0777);

  std::ifstream isConf ("./CeforeDefaultConfigFile/cefnetd.conf", std::ios::in|std::ios::binary);
  if(!isConf) {
    std::cerr << "cannot open " << "./CeforeDefaultConfigFile/cefnetd.conf" << std::endl;
    std::exit(1);
  }
  std::ofstream osConf ((folder+"/cefnetd.conf").c_str(), std::ios::out|std::ios::binary);
  osConf << isConf.rdbuf();
  isConf.close(); osConf.close();
  std::ifstream isFib ("./CeforeDefaultConfigFile/cefnetd.fib", std::ios::in|std::ios::binary);
  if(!isFib) {
    std::cerr << "cannot open " << "./CeforeDefaultConfigFile/cefnetd.fib" << std::endl;
    std::exit(1);
  }
  std::ofstream osFib ((folder+"/cefnetd.fib").c_str(), std::ios::out|std::ios::binary);
  osFib << isFib.rdbuf();
  isFib.close(); osFib.close();

  std::ifstream isCsm ("./CeforeDefaultConfigFile/csmgrd.conf", std::ios::in|std::ios::binary);
  if(!isCsm) {
    std::cerr << "cannot open " << "./CeforeDefaultConfigFile/csmgrd.conf" << std::endl;
    std::exit(1);
  }
  std::ofstream osCsm ((folder+"/csmgrd.conf").c_str(), std::ios::out|std::ios::binary);
  osCsm << isCsm.rdbuf();
  isCsm.close(); osCsm.close();

  std::ifstream isCcoreKey ("./CeforeDefaultConfigFile/ccore-public-key", std::ios::in|std::ios::binary);
  if(!isCcoreKey) {
    std::cerr << "cannot open " << "./CeforeDefaultConfigFile/ccore-public-key" << std::endl;
    std::exit(1);
  }
  std::ofstream osCcoreKey ((folder+"/ccore-public-key").c_str(), std::ios::out|std::ios::binary);
  osCcoreKey << isCcoreKey.rdbuf();
  isCcoreKey.close(); osCcoreKey.close();

  std::ifstream isDfKey ("./CeforeDefaultConfigFile/default-public-key", std::ios::in|std::ios::binary);
  if(!isDfKey) {
    std::cerr << "cannot open " << "./CeforeDefaultConfigFile/default-public-key" << std::endl;
    std::exit(1);
  }
  std::ofstream osDfKey ((folder+"/default-public-key").c_str(), std::ios::out|std::ios::binary);
  osDfKey << isDfKey.rdbuf();
  isDfKey.close(); osDfKey.close();

  std::ifstream isCefKey ("./CeforeDefaultConfigFile/cefnetd.key", std::ios::in|std::ios::binary);
  if(!isCefKey) {
    std::cerr << "cannot open " << "./CeforeDefaultConfigFile/cefnetd.key" << std::endl;
    std::exit(1);
  }
  std::ofstream osCefKey ((folder+"/cefnetd.key").c_str(), std::ios::out|std::ios::binary);
  osCefKey << isCefKey.rdbuf();
  isCefKey.close(); osCefKey.close();

  std::ifstream isDfPriKey ("./CeforeDefaultConfigFile/default-private-key", std::ios::in|std::ios::binary);
  if(!isDfPriKey) {
    std::cerr << "cannot open " << "./CeforeDefaultConfigFile/default-private-key" << std::endl;
    std::exit(1);
  }
  std::ofstream osDfPriKey ((folder+"/default-private-key").c_str(), std::ios::out|std::ios::binary);
  osDfPriKey << isDfPriKey.rdbuf();
  isDfPriKey.close(); osDfPriKey.close();

  std::ifstream isPlgConf ("./CeforeDefaultConfigFile/plugin.conf", std::ios::in|std::ios::binary);
  if(!isPlgConf) {
    std::cerr << "cannot open " << "./CeforeDefaultConfigFile/plugin.conf" << std::endl;
    std::exit(1);
  }
  std::ofstream osPlgConf ((folder+"/plugin.conf").c_str(), std::ios::out|std::ios::binary);
  osPlgConf << isPlgConf.rdbuf();
  isPlgConf.close(); osPlgConf.close();

}


int
main (int argc, char *argv[])
{
  std::string mode = "ConfigureLocal";
  std::string tapName = "tap0";
  int numWifiNodes = 1;
 
  int csmaRate = 100000000;
  std::cout << "csmaRate: " << csmaRate/1000000 << " Mbps." << std::endl;
 
  CommandLine cmd;
  //cmd.AddValue ("tapName", "Name of the OS tap device", tapName);
  cmd.AddValue ("numWifiNodes", "number of the wifi station nodes", numWifiNodes);
  
  cmd.Parse (argc, argv);

  GlobalValue::Bind ("SimulatorImplementationType", StringValue ("ns3::RealtimeSimulatorImpl"));
  GlobalValue::Bind ("ChecksumEnabled", BooleanValue (true));

  NodeContainer csmaNodes;
  //csmaNodes.Create (2);
  csmaNodes.Create (3);
  NodeContainer tapNode;
  tapNode = csmaNodes.Get(0);
  //NodeContainer serverNode;
  //serverNode = csmaNodes.Get(0);
  NodeContainer wifiApNode;
  wifiApNode.Add(csmaNodes.Get(1));
  wifiApNode.Add(csmaNodes.Get(2));
  NodeContainer wifiStaNodes;
  wifiStaNodes.Create(numWifiNodes);

  DceManagerHelper dceManager;
  dceManager.Install (csmaNodes);
  dceManager.Install (wifiStaNodes);

  CsmaHelper csma;
  csma.SetChannelAttribute ("DataRate", DataRateValue (csmaRate));
  csma.SetChannelAttribute ("Delay", TimeValue (MilliSeconds (1)));
  //PointToPointHelper csma;
  //csma.SetDeviceAttribute ("DataRate", StringValue ("10Mbps"));
  //csma.SetChannelAttribute ("Delay", StringValue("10ms"));
  
  NetDeviceContainer csmaDevices = csma.Install (csmaNodes);

  #if 1
  InternetStackHelper stack;
  Ipv4DceRoutingHelper ipv4RoutingHelper; 
  stack.SetRoutingHelper (ipv4RoutingHelper);
  stack.Install (csmaNodes);
  stack.Install (wifiStaNodes);
  #endif
  

  //
  // set EmuFdNetDevice
  // 
  EmuFdNetDeviceHelper emu;
  std::string deviceName ("data");
  //std::string deviceName ("eth0");
  emu.SetDeviceName (deviceName);
  Ptr<Node> node = tapNode.Get(0); // --> tap-bridge node
  NetDeviceContainer emudevices = emu.Install (node); //--> devices in indika-csma
  Ptr<NetDevice> device = emudevices.Get (0);
  device->SetAttribute ("Address", Mac48AddressValue (Mac48Address::Allocate ()));

  Ptr<Ipv4> ipv4 = node->GetObject<Ipv4> ();
  uint32_t interface = ipv4->AddInterface (device); //std::cout << "interface:" << interface << std::endl;
  std::string local("192.168.2.32"); //-->eth0
  Ipv4Address localIp (local.c_str());
  Ipv4Mask localMask ("255.255.255.0");
  Ipv4InterfaceAddress address = Ipv4InterfaceAddress (localIp, localMask);
  ipv4->AddAddress (interface, address);
  ipv4->SetMetric (interface, 1);
  ipv4->SetUp (interface);

  //Ipv4Address gateway ("0.0.0.0");
  //Ipv4Address gateway ("192.168.2.6"); //--> eth0 //XXX
  Ipv4Address gateway (nexthop.c_str()); //--> eth0 //XXX
  //Ipv4Address gateway ("192.168.2.25"); //--> eth0 //XXX
  #if 0 
  Ptr<Ipv4StaticRouting> staticRouting = ipv4RoutingHelper.GetStaticRouting (ipv4);
  staticRouting->SetDefaultRoute (gateway, interface);
  #else 
  Ipv4StaticRoutingHelper ipv4RoutingHelpern0;
  Ptr<Ipv4StaticRouting> staticRouting = ipv4RoutingHelpern0.GetStaticRouting (ipv4);
  staticRouting->SetDefaultRoute (gateway, interface);
  #endif

  #if 1 
  // static routing to real-world 
  Ptr<Node> node1 = wifiApNode.Get(0); // --> AP node
  Ptr<Ipv4> ipv4n1 = node1->GetObject<Ipv4> ();
  // The first index is 0 for loopback, then the index is incremented and allocated when device is configured (e.g. csma).
  uint32_t interfacen1 = 1;
  //uint32_t interfacen1 = 2;
  Ipv4Address n1gateway ("10.1.1.1");
  Ipv4StaticRoutingHelper ipv4RoutingHelpern1;
  Ptr<Ipv4StaticRouting> staticRoutingn1 = ipv4RoutingHelpern1.GetStaticRouting (ipv4n1);
  staticRoutingn1->SetDefaultRoute (n1gateway, interfacen1);
  #endif
  #if 1 
  // static routing to real-world 
  Ptr<Node> node2 = wifiApNode.Get(1); // --> AP node
  Ptr<Ipv4> ipv4n2 = node2->GetObject<Ipv4> ();
  // The first index is 0 for loopback, then the index is incremented and allocated when device is configured (e.g. csma).
  uint32_t interfacen2 = 1;
  //uint32_t interfacen1 = 2;
  Ipv4Address n2gateway ("10.1.1.1");
  Ipv4StaticRoutingHelper ipv4RoutingHelpern2;
  Ptr<Ipv4StaticRouting> staticRoutingn2 = ipv4RoutingHelpern2.GetStaticRouting (ipv4n2);
  staticRoutingn2->SetDefaultRoute (n2gateway, interfacen2);
  #endif


  //
  // set Cefore Config
  //
  // copy cefore config files to each node's directory (files-n/usr/local/cefore)
  //for(int nodeId=0; nodeId < (numWifiNodes+2); nodeId++)
  for(int nodeId=1; nodeId < (numWifiNodes+3); nodeId++)
    CopyCeforeConfig(nodeId);

  // create Fib on the AP.
  CreateFib(wifiApNode.Get(0)->GetId());
  CreateFib(wifiApNode.Get(1)->GetId());
  // create Fib on the wifi consumers.
  for(int wifiNodeId=0; wifiNodeId < numWifiNodes; wifiNodeId++)
    CreateFib(wifiStaNodes.Get(wifiNodeId)->GetId());

  //Enable server Cache
  //EnableCache(0);

  //Enable AP cache
  if(ENABLE_AP_CACHE){
    EnableCache(1);
    EnableCache(2);
  }

  //Create data file
  //CreateCacheFile();


  /* 
   * Wifi configuration
   */
  YansWifiChannelHelper channel = YansWifiChannelHelper::Default ();
  YansWifiPhyHelper phy = YansWifiPhyHelper::Default ();
  phy.SetPcapDataLinkType (YansWifiPhyHelper::DLT_IEEE802_11_RADIO);
  phy.SetChannel (channel.Create ());

  WifiHelper wifi;
  //wifi.SetRemoteStationManager ("ns3::AarfWifiManager");
  #if 1 
  wifi.SetStandard (WIFI_PHY_STANDARD_80211g);
  //wifi.SetStandard (WIFI_PHY_STANDARD_80211a);
  #else 
  wifi.SetStandard (WIFI_PHY_STANDARD_80211n_5GHZ);
  //wifi.SetRemoteStationManager ("ns3::ConstantRateWifiManager", "DataMode", StringValue("HtMcs7"), "ControlMode", StringValue("HtMcs0"));
  wifi.SetRemoteStationManager ("ns3::ConstantRateWifiManager", "DataMode", StringValue("HtMcs7"), "ControlMode", StringValue("OfdmRate24Mbps"));
  #endif

  WifiMacHelper mac;
  Ssid ssid = Ssid ("ns-3-ssid");
  mac.SetType ("ns3::StaWifiMac",
               "Ssid", SsidValue (ssid),
               "ActiveProbing", BooleanValue (false));

  NetDeviceContainer staDevices;
  staDevices = wifi.Install (phy, mac, wifiStaNodes);

  mac.SetType ("ns3::ApWifiMac",
               "Ssid", SsidValue (ssid));

  NetDeviceContainer apDevices;
  apDevices = wifi.Install (phy, mac, wifiApNode);

  MobilityHelper mobility;
  mobility.SetMobilityModel ("ns3::ConstantVelocityMobilityModel");
  mobility.Install (wifiStaNodes);

  #if 0// static model
  std::cout << "No Move!!\n"; 
  //SetPositionVelocity (wifiStaNodes.Get(0), Vector (0.0, 10.0, 0.0), Vector (0.0, 0.0, 0.0));
  SetPositionVelocity (wifiStaNodes.Get(0), Vector (0.0, 10.0, 0.0), Vector (0.0, 0.0, 0.0));
  mobility.Install (wifiApNode);
  SetPositionVelocity (wifiApNode.Get(0), Vector (0.0, 0.0, 0.0), Vector (0.0, 0.0, 0.0));
  SetPositionVelocity (wifiApNode.Get(1), Vector (300.0, 0.0, 0.0), Vector (0.0, 0.0, 0.0));
  #else // Moving model
  SetPositionVelocity (wifiStaNodes.Get(0), Vector (-50.0, 10.0, 0.0), Vector (10.0, 0.0, 0.0));
  mobility.Install (wifiApNode);
  SetPositionVelocity (wifiApNode.Get(0), Vector (0.0, 0.0, 0.0), Vector (0.0, 0.0, 0.0));
  SetPositionVelocity (wifiApNode.Get(1), Vector (300.0, 0.0, 0.0), Vector (0.0, 0.0, 0.0));
  #endif



  Ipv4AddressHelper addresses;
  addresses.SetBase ("10.1.1.0", "255.255.255.0");
  Ipv4InterfaceContainer csmaInterfaces = addresses.Assign (csmaDevices);
  addresses.SetBase ("10.2.2.0", "255.255.255.0");
  addresses.Assign (apDevices);
  addresses.Assign (staDevices);

  #if 1 
  TapBridgeHelper tapBridge;
  tapBridge.SetAttribute ("Mode", StringValue (mode));
  tapBridge.SetAttribute ("DeviceName", StringValue (tapName));
  tapBridge.Install (tapNode.Get (0), csmaDevices.Get (0));
  //tapBridge.Install (csmaNodes.Get (0), csmaDevices.Get (0));
  #endif

  //Ipv4GlobalRoutingHelper::PopulateRoutingTables ();

  DceApplicationHelper dce;
  ApplicationContainer apps;

  dce.SetStackSize (1 << 29);


#if 1 
  #if 0
  // Launch cefnetd on wifi nodes 
  dce.SetBinary ("cefnetd");
  dce.ResetArguments ();
  dce.ResetEnvironment ();
  apps = dce.Install (serverNode);
  apps.Start (Seconds (1.0));
  #endif 
 
  // Launch cefnetd on wifi nodes 
  dce.SetBinary ("cefnetd");
  dce.ResetArguments ();
  dce.ResetEnvironment ();
  apps = dce.Install (wifiStaNodes);
  apps.Start (Seconds (0.1));
  
  // Launch cefnetd on AP node  
  dce.SetBinary ("cefnetd");
  dce.ResetArguments ();
  dce.ResetEnvironment ();
  apps = dce.Install (wifiApNode);
  apps.Start (Seconds (0.2));


  #if 0
  // Launch cefputfile on server node 
  dce.ResetArguments();
  dce.SetBinary ("cefputfile");
  dce.AddArgument (ccnContentName);
  dce.AddArgument ("-f");
  dce.AddArgument (InFile);
  //dce.AddArgument ("-r");
  //dce.AddArgument ("3");
  apps = dce.Install (serverNode);
  //apps = dce.Install (csmaNodes.Get(0));
  apps.Start (Seconds (3.5));
  #endif

  double scheduleTime = 1.0; 
  //double scheduleTime = 15.0; 
  for(int wifiNodeId=0; wifiNodeId < numWifiNodes; wifiNodeId++)
  {

    std::string targetName = contentNamePrefix + "/test";    
    dce.SetBinary ("cefgetfile");
    dce.ResetArguments ();
    dce.ResetEnvironment ();
    dce.AddArgument (targetName.c_str());
    dce.AddArgument ("-f");
    dce.AddArgument (outFile.c_str());
    int use_smi = 1;
    if(use_smi){
      dce.AddArgument ("-z");
      dce.AddArgument ("sg");
    }else{
      dce.AddArgument ("-s");
      dce.AddArgument (PIPELINE.c_str());
    } 
    //if(USE_M_OPTION){
    //  dce.AddArgument ("-m");
    //  dce.AddArgument (maxChunk.c_str());
    //} 
    apps = dce.Install (wifiStaNodes.Get(wifiNodeId));
    apps.Start (Seconds (scheduleTime));
    //apps.Stop (Seconds (33));
    
    std::cout << "wifi-consumer-nodeId: " << wifiStaNodes.Get(wifiNodeId)->GetId() << std::endl;
    if(use_smi)
      fprintf(stdout, "\t Use SMI\n");  
    else 
      fprintf(stdout, "\t Use Only RGI\n") ; 
    std::cout << "\t Time: " << scheduleTime << std::endl;
    //scheduleTime += 0.5;
  
    #if 0 
    // for test:
    dce.ResetArguments ();
    dce.ResetEnvironment ();
    dce.AddArgument (targetName.c_str());
    dce.AddArgument ("-f");
    dce.AddArgument (outFile.c_str());
    dce.AddArgument ("-s");
    dce.AddArgument (PIPELINE.c_str());
    apps = dce.Install (wifiStaNodes.Get(wifiNodeId));
    scheduleTime += 1.0;
    apps.Start (Seconds (scheduleTime));
    #endif

  }
#endif

  //Simulator::Stop (Seconds (50.0));
  //Simulator::Stop (Seconds (36.0));
  Simulator::Stop (Seconds (41.0));
  Simulator::Run ();
  Simulator::Destroy ();

  return 0;
}
