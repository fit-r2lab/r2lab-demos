#!/usr/bin/env python3
import re
from r2labProtocolEval import naming_scheme
from graphviz import Digraph

def readRTT(filename):
    """
        Will generate a list of time (in ms) by parsing the output of the ping command.
        One line is typically :
        72 bytes from 10.0.0.4: icmp_seq=2 ttl=64 time=1.34 ms
    """
    pings_time = []
    try:
        with open(filename) as pings_file:
            for line in pings_file:
                #TODO If condition to be sure that the line contains the info
                #TODO PARSE LINE TO get ms
                if "bytes" in line and "ms" in line:
                    *values, time ,ms = line.split()
                    junk, time = time.split("=")
                    pings_time.append(time)
            pings_file.close()

    except IOError as e:
        file = str(filename)
        *rest, pingfile = file.split("/")
        word, src, dst = pingfile.split("-")
        inverted_file_name = "PING-{:02d}-{:02d}".format(int(dst), int (src))
        inverted_file_path = re.sub("PING-.*", inverted_file_name , file)
        try:
            with open(inverted_file_path) as revert_pings_file:
                for line in revert_pings_file:
                    #TODO If condition to be sure that the line contains the info
                    #TODO PARSE LINE TO get ms
                    if "bytes" in line and "ms" in line:
                        *values, time ,ms = line.split()
                        junk, time = time.split("=")
                        pings_time.append(time)
                revert_pings_file.close()
        except IOError as e2:
                print("Cannot open file {}: {}" .format(inverted_file_name, e2))
                print("Nor file {}: {}".format(filename, e))
    return pings_time

def readPDR(filename):
    """
        Will the PDR of the ping by parsing the output of the command.
        The line is typically :
        500 packets transmitted, 500 received, 0% packet loss, time 720ms
        If we have some lost:
        592 packets transmitted, 0 received, 100% packet loss, time 5994ms
    """

    pdr = 0
    patern = re.compile('(\d{1,3}(?=%))')
    try:
        with open(filename) as pings_file:
            for line in pings_file:
                if "%" in line:
                    pdr = patern.findall(line)
            pings_file.close()
    except IOError as e:
        file = str(filename)
        *rest, pingfile = file.split("/")
        word, src, dst = pingfile.split("-")
        inverted_file_name = "PING-{:02d}-{:02d}".format(int(dst), int (src))
        inverted_file_path = re.sub("PING-.*", inverted_file_name , file)
        try:
            with open(inverted_file_path) as revert_pings_file:
                for line in revert_pings_file:
                    if "%" in line:
                        pdr = patern.findall(line)
                revert_pings_file.close()

        except IOError as e2:
            print("Cannot open file {}: {}" .format(inverted_file_name, e2))
            print("Nor file {}: {}".format(filename, e))
    return pdr
def isValidRoute(route):
    if "- 0 -" in route:
        return False
    return True

def getRoutes(filename):
    routes = []
    try:
        with open(filename) as routes_file:
            for line in routes_file:
                if isValidRoute(line):
                    routes.append(line.rstrip())
            routes_file.close()
    except IOError as e:
        print("Cannot open file {}: {}" .format(filename, e))
    return routes

def getAllRoutes(filename):
    routes = []
    try:
        with open(filename) as routes_file:
            for line in routes_file:
                    routes.append(line.rstrip())
            routes_file.close()
    except IOError as e:
        print("Cannot open file {}: {}" .format(filename, e))
    return routes

def getSourceDestFromRoute(route):
    src , *values , dest = route.split(" -- ")
    return src, dest
def generatSourceDestRouteString(source, dest):
    return "fit{:02d} - fit{:02d}".format(source, dest)
def generateRouteListForBlockGraph(route, data):
    return [route] * len(data)
def graphDataRTT(run_name, tx_power, phy_rate, antenna_mask, channel, interference, protocol, source):
    routes = getAllRoutes(naming_scheme(run_name=run_name, tx_power=tx_power,
                                        phy_rate=phy_rate, antenna_mask=antenna_mask,
                                     channel=channel, interference = interference, protocol = protocol) / "ROUTES-{:02d}".format(source))
                                     #print(routes)

    xValues = []
    yValues = []
    RTT_dic = {}
    for route in routes:
        source, destination = getSourceDestFromRoute(route)
        source_id = int(source)
        destination_id = int(destination)
        RTT_dic[(source_id, destination_id)] = [float(value) for value in readRTT(naming_scheme(run_name=run_name, tx_power=tx_power,
                                phy_rate=phy_rate, antenna_mask=antenna_mask,
                                channel=channel, interference = interference, protocol = protocol)
            / "PING-{:02d}-{:02d}".format(source_id, destination_id))]
        if "-- 0 --" in route:
            RTT_dic[(source_id, destination_id)]=[0]
        #print(RTT_dic[(source_id, destination_id)])


        xValues.extend( generateRouteListForBlockGraph(generatSourceDestRouteString(source_id, destination_id ), RTT_dic[(source_id, destination_id)]))
        yValues.extend( RTT_dic[source_id, destination_id])
    
    return xValues, yValues


def graphDataPDR(run_name, tx_power, phy_rate, antenna_mask, channel, interference, protocol, source):
    directory =naming_scheme(run_name=run_name, tx_power=tx_power,
                             phy_rate=phy_rate, antenna_mask=antenna_mask,
                             channel=channel, interference = interference, protocol = protocol)
    routes = getAllRoutes( directory/ "ROUTES-{:02d}".format(source))
    xValues = []
    yValues = []
    PDR_dic = {}
    for route in routes:
         source, destination = getSourceDestFromRoute(route)
         source_id = int(source)
         destination_id = int(destination)
         #print(readPDR( directory / "PING-{:02d}-{:02d}".format(source_id, destination_id)))
         PDR_dic[(source_id, destination_id)] = [100 - int(value)
                                                 for value in readPDR( directory / "PING-{:02d}-{:02d}".format(source_id, destination_id))]
         xValues.extend( [generatSourceDestRouteString(source_id, destination_id)])
                                                                                                                   
         yValues.extend( PDR_dic[source_id, destination_id])
    return xValues, yValues
def getNodesFromRoutes(routes):
    nodes = []
    for route in routes:
        nodes.extend(route.split(" -- "))
    return list(set(nodes))

def getEdgesFromRoutes(dot, routes):
    for route in routes:
        if("-- 0 --" not in route):
            nodes = route.split(" -- ")
            for i in range(0 , len(nodes)-1):
                dot.edge(nodes[i], nodes[i+1])
    return dot
def generateRouteGraph(run_name, tx_power, phy_rate, antenna_mask, channel, interference, protocol, source, sampleNum = None):
    dot = Digraph(comment='Routing table for fit{:02d}'.format(source))
    dot.attr(rankdir='LR')
    dot.attr('node', shape='doublecircle')
    #dot.format = 'png'
    directory =naming_scheme(run_name=run_name, tx_power=tx_power,
                             phy_rate=phy_rate, antenna_mask=antenna_mask,
                             channel=channel, interference = interference, protocol = protocol)
    if sampleNum is None:
        routes = getAllRoutes( directory/ "ROUTES-{:02d}".format(source))
    else:
        routes = getAllRoutes( directory/ "SAMPLES" / "ROUTES-{:02d}-SAMPLE{}".format(source,sampleNum))
    nodes = getNodesFromRoutes(routes)
    nodes = list(set(nodes)- set(['0']))
    if len(nodes) > 0 :
        for node in nodes:
            dot.node(node, 'fit{:02d}'.format(int(node)))
        dot = getEdgesFromRoutes(dot, routes)
        #dot.render(directory / "ROUTES-DIAGRAM-{:02d}".format(source), view=False)
        return dot#str(directory / "ROUTES-DIAGRAM-{:02d}.png".format(source))


