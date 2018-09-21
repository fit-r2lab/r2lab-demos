#!/usr/bin/env python3

# pylint: disable=c0111

import re
import glob

from graphviz import Digraph

from r2labmap import maps

from runs import naming_scheme

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
                # TODO If condition to be sure that the line contains the info
                # TODO PARSE LINE TO get ms
                if "bytes" in line and "ms" in line:
                    if "(DUP!)" not in line:
                        *values, time, ms = line.split()
                        junk, time = time.split("=")
                    else:
                        *values, time ,ms, dup = line.split()
                        junk, time = time.split("=")
                    pings_time.append(time)

    except IOError as e:
        file = str(filename)
        *rest, pingfile = file.split("/")
        path = ""
        for item in rest[:-1]:
            path  += item + "/"
        path += rest[-1]
        #word, src, dst = pingfile.split("-")
        #file_name = "PING-{:02d}-{:02d}".format(int(dst), int (src))
        #inverted_file_path = re.sub("PING-.*", inverted_file_name , file)
        #try:
        #    with open(inverted_file_path) as revert_pings_file:
        #         for line in revert_pings_file:
                    #TODO If condition to be sure that the line contains the info
                    #TODO PARSE LINE TO get ms
                    #            if "bytes" in line and "ms" in line:
                    #                 if "(DUP!)" not in line:
                    #                     *values, time ,ms = line.split()
                    #       junk, time = time.split("=")
                    #   else:
                    #       *values, time ,ms, dup = line.split()
                    #       junk, time = time.split("=")
                    #   pings_time.append(time)


#except IOError as e2:
        print("{} was not generated in these conditions: {}"
              .format(pingfile, path))
#        print("Nor file {}: {}".format(filename, e))
    if len(pings_time) < 500:
        pings_time.extend([-1] * (500-len(pings_time)))
    return pings_time

def readPDR(filename):
    """
        Will the PDR of the ping by parsing the output of the command.
        The line is typically :
        500 packets transmitted, 500 received, 0% packet loss, time 720ms
        If we have some lost:
        592 packets transmitted, 0 received, 100% packet loss, time 5994ms
    """

    pdr = [101]
    pattern = re.compile('(\d{1,3}(?=%))')
    try:
        with open(filename) as pings_file:
            for line in pings_file:
                if "%" in line:
                    pdr = pattern.findall(line)

    except IOError as e:
        file = str(filename)
        *rest, pingfile = file.split("/")
        path = ""
        for item in rest[:-1]:
            path  += item + "/"
        path += rest[-1]

        #word, src, dst = pingfile.split("-")
        #file_name = "PING-{:02d}-{:02d}".format(int(src), int (dst))
        #inverted_file_path = re.sub("PING-.*", inverted_file_name , file)
        #try:
        #    with open(inverted_file_path) as revert_pings_file:
        #        for line in revert_pings_file:
        #            if "%" in line:
        #                pdr = pattern.findall(line)

#except IOError as e2:
        print("{} was not generated in these conditions: {}" .format(pingfile, path ))
#        print("Nor {}: {}".format(filename, e))
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
    except IOError as e:
        print("Routes were not generated for these conditions: {}" .format(filename))
    return routes

def getAllRoutes(filename):
    routes = []
    try:
        with open(filename) as routes_file:
            for line in routes_file:
                    routes.append(line.rstrip())
    except IOError as e:
        print("Routes were not generated for these conditions: {}" .format(filename))
    return routes
def getAllRoutes_sample(filename, sampleNum):
    routes = []
    cursorOK = False
    try:
        with open(filename) as routes_file:
            for line in routes_file:
                if "SAMPLE" in line and cursorOK:
                    cursorOK = False
                    break
                if cursorOK:
                    routes.append(line.rstrip())
                if "SAMPLE {}".format(sampleNum) in line:
                    cursorOK = True
    except IOError as e:
        print("Routes were not generated for these conditions: {}" .format(filename))
    return routes

def getSourceDestFromRoute(route):
    src , *values , dest = route.split(" -- ")
    return src, dest
def generatSourceDestRouteString(source, dest):
    return "fit{:02d} - fit{:02d}".format(source, dest)
def generateRouteListForBlockGraph(route, data):
    return [route] * len(data)
def getInfo(run_root, type):
    try:
        with (run_root / "info.txt").open() as info_file:
            lines = info_file.readlines()
        if type == "Sources":
            return lines[3].split()
        if type == "Destinations":
            return lines[5].split()
        if type == "Nodes":
            return lines[1].split()
    except IOError as e:
        print("Experiment was not run in these conditions : {}".format(run_root))
    return []
def graphDataRTT(run_name, tx_power, phy_rate, antenna_mask, channel, interference, protocol, source):
    #routes = getAllRoutes(naming_scheme(run_name=run_name, tx_power=tx_power,
    #                                    phy_rate=phy_rate, antenna_mask=antenna_mask,
    #                                 channel=channel, interference = interference, protocol = protocol) / "ROUTES-{:02d}".format(source))
                                     #print(routes)
    directory =naming_scheme(run_name=run_name, tx_power=tx_power,
                             phy_rate=phy_rate, antenna_mask=antenna_mask,
                             channel=channel, interference = interference,
                             protocol = protocol)
    dests = getInfo(directory, "Destinations")
    xValues = []
    yValues = []
    RTT_dic = {}
        #for dst in dests:
        #    RTT_dic[(int(source), int(dst))] = []
    for destination in dests:
        source_id = int(source)
        destination_id = int(destination)
        if source_id != destination_id:
            if (source_id, destination_id) not in RTT_dic:
                RTT_dic[(source_id, destination_id)] = [float(value)
                                                       for value in readRTT(directory
                                                                            / "PING-{:02d}-{:02d}".format(source_id, destination_id))]
            else:
                RTT_dic[(source_id, destination_id)].extend(  [float(value)
                                                    for value in readRTT(directory
                        / "PING-{:02d}-{:02d}".format(source_id, destination_id))])

            if len(RTT_dic[(source_id, destination_id)]) == 0:
                RTT_dic[(source_id, destination_id)]=[0]
                                                                                      #print(RTT_dic[(source_id, destination_id)])
            xValues.extend( generateRouteListForBlockGraph(generatSourceDestRouteString(source_id, destination_id ), RTT_dic[(source_id, destination_id)]))
            yValues.extend( RTT_dic[source_id, destination_id])
        """for route in routes:
            source, destination = getSourceDestFromRoute(route)
            source_id = int(source)
            destination_id = int(destination)

            RTT_dic[(source_id, destination_id)] = [float(value) for value in readRTT(naming_scheme(run_name=run_name, tx_power=tx_power,
                                    phy_rate=phy_rate, antenna_mask=antenna_mask,
                                    channel=channel, interference = interference, protocol = protocol)
                / "PING-{:02d}-{:02d}".format(source_id, destination_id))]

            if len(RTT_dic[(source_id, destination_id)]) == 0:
                RTT_dic[(source_id, destination_id)]=[0]
            #print(RTT_dic[(source_id, destination_id)])


            xValues.extend( generateRouteListForBlockGraph(generatSourceDestRouteString(source_id, destination_id ), RTT_dic[(source_id, destination_id)]))
            yValues.extend( RTT_dic[source_id, destination_id])"""

    return xValues, yValues

def graphDataMultipleRTT(run_name_family, tx_power, phy_rate, antenna_mask, channel,
                         interference, protocol, source, dests, maxdata):

    xValues = []
    yValues = []
    RTT_dic = {}
    countmax = 0

    for run_name in glob.glob(f"{run_name_family}*/"):
        if countmax >= maxdata:
            break
        countmax+=1
        #print(run_name)
        directory = naming_scheme(run_name=run_name, tx_power=tx_power,
                                  phy_rate=phy_rate, antenna_mask=antenna_mask,
                                  channel=channel, interference = interference,
                                  protocol = protocol)
                                  #dests = getInfo( directory, "Destinations")
        for destination in dests:

            source_id = int(source)
            destination_id = int(destination)
            if source_id == destination_id:
                continue
            if (source_id, destination_id) not in RTT_dic:
                RTT_dic[(source_id, destination_id)] = [float(value)
                                                        for value in readRTT(directory
                                                                             / "PING-{:02d}-{:02d}".format(source_id, destination_id))]
            else:
                RTT_dic[(source_id, destination_id)].extend(  [float(value)
                                                               for value in readRTT(directory
                                                                                    / "PING-{:02d}-{:02d}".format(source_id, destination_id))])

            if len(RTT_dic[(source_id, destination_id)]) == 0:
                RTT_dic[(source_id, destination_id)]=[0]
                #print(RTT_dic[(source_id, destination_id)])
            xValues.extend( generateRouteListForBlockGraph(generatSourceDestRouteString(source_id, destination_id ), RTT_dic[(source_id, destination_id)]))
            yValues.extend( RTT_dic[source_id, destination_id])
    return xValues, yValues
def graphDataPDR(run_name, tx_power, phy_rate, antenna_mask, channel, interference, protocol, source):
    directory =naming_scheme(run_name=run_name, tx_power=tx_power,
                             phy_rate=phy_rate, antenna_mask=antenna_mask,
                             channel=channel, interference = interference, protocol = protocol)
                             #routes = getAllRoutes( directory/ "ROUTES-{:02d}".format(source))
    dests = getInfo(directory, "Destinations")
    xValues = []
    yValues = []
    PDR_dic = {}
    for destination in dests:
        # for route in routes:
        #     source, destination = getSourceDestFromRoute(route)
         source_id = int(source)
         destination_id = int(destination)
         if source_id == destination_id:
             continue
         #print(readPDR( directory / "PING-{:02d}-{:02d}".format(source_id, destination_id)))
         PDR_dic[(source_id, destination_id)] = [100 - int(value)
                                                 for value in readPDR( directory / "PING-{:02d}-{:02d}".format(source_id, destination_id))]
         xValues.extend( [generatSourceDestRouteString(source_id, destination_id)])

         yValues.extend( PDR_dic[source_id, destination_id])
    return xValues, yValues
def graphDataMultiplePDRCount(run_name_family, tx_power, phy_rate, antenna_mask, channel,
                         interference, protocol, source, dest, maxdata):
    yValues = [0] * 101
    xValues = list(range(0,101))
    #FOR EVERY DATA WITH RUN_NAME_FAMILY
    countmax = 0

    for run_name in glob.glob(f"{run_name_family}/*/"):
        if countmax >= maxdata:
            break
        countmax+=1
        directory =naming_scheme(run_name=run_name, tx_power=tx_power,
                                 phy_rate=phy_rate, antenna_mask=antenna_mask,
                                 channel=channel, interference = interference, protocol = protocol)
        pdr = [100 - int(value)
               for value in readPDR(directory / "PING-{:02d}-{:02d}"\
                                    .format(source, dest))]
        if pdr[0] != -1:
            yValues[pdr[0]] += 1

    return xValues, yValues
def graphDataMultiplePDR(run_name_family, tx_power, phy_rate, antenna_mask, channel,
                         interference, protocol, source, dest, maxdata):
    yValues = []
    xValues = [generatSourceDestRouteString(int(source),int(dest))] * maxdata
    #FOR EVERY DATA WITH RUN_NAME_FAMILY
    countmax = 0

    for run_name in glob.glob(f"{run_name_family}/*/"):
        if countmax >= maxdata:
            break
        countmax+=1
        directory =naming_scheme(run_name=run_name, tx_power=tx_power,
                                 phy_rate=phy_rate, antenna_mask=antenna_mask,
                                 channel=channel, interference = interference,
                                 protocol = protocol)
        pdr = [100 - int(value)
               for value in readPDR(directory / "PING-{:02d}-{:02d}"\
                                    .format(source, dest))]
        if pdr[0] != -1:
            yValues.append(pdr[0])
        else:
            yValues.append(0)

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
            if("-- -1 --" not in route):
                for i in range(0 , len(nodes)-1):
                    dot.edge(nodes[i], nodes[i+1])
            else:
                nodes.remove('-1')
                for i in range(0 , len(nodes)-2):
                    dot.edge(nodes[i], nodes[i+1], color = "red")
                dot.edge(nodes[len(nodes)-3], nodes[len(nodes) - 1], label = "LOOP FOR ROUTES TO THIS DEST", color = "red" )
    return dot
def generateRouteGraph(run_name, tx_power, phy_rate, antenna_mask, channel, interference, protocol, source, sample = None):
    node_to_pos, dump1, holes = maps(lambda x : x+1, lambda y : 5-y)
    #print (node_to_pos)
    dot = Digraph(comment='Routing table for fit{:02d}'.format(source), engine = 'fdp')
    dot.attr(splines = 'true')
    dot.attr(rankdir='LR')
    #dot.attr('node', shape='doublecircle')
    #dot.format = 'png'
    directory =naming_scheme(run_name=run_name, tx_power=tx_power,
                             phy_rate=phy_rate, antenna_mask=antenna_mask,
                             channel=channel, interference = interference, protocol = protocol)
    if sample is None:
        routes = getAllRoutes( directory/ "ROUTES-{:02d}".format(source))
    else:
        routes = getAllRoutes_sample( directory/ "SAMPLES" / "ROUTES-{:02d}-SAMPLE".format(source), sample)
    nodes = getNodesFromRoutes(routes)
    nodes = list(set(nodes)- set(['0']))

    dot.node("  ", pos = "4,4!", shape = "box")
    dot.node(" ", pos = "6,4!", shape = "box")
    for node_id in range(1, 38):
        if node_id == 5:
            dot.node("Interference", pos = "1,1!", shape = "tripleoctagon")
            continue
        if str(node_id) not in nodes:
            dot.node(str(node_id), 'fit{:02d}'.format(node_id),
                     pos = "{},{}!".format(node_to_pos[node_id][0],node_to_pos[node_id][1]),
                     shape = 'point')
        else:
            dot.node(str(node_id), 'fit{:02d}'.format(node_id),
                     pos = "{},{}!".format(node_to_pos[node_id][0],node_to_pos[node_id][1]),
                     shape = 'doublecircle')
    if len(nodes) > 0 :
        dot = getEdgesFromRoutes(dot, routes)

        return dot
def get_sample_count(run_name, tx_power, phy_rate, antenna_mask, channel, interference, protocol, source):
     directory =naming_scheme(run_name=run_name, tx_power=tx_power,
                         phy_rate=phy_rate, antenna_mask=antenna_mask,
                         channel=channel, interference = interference, protocol = protocol)
     filename = directory/ "SAMPLES" / "ROUTES-{:02d}-SAMPLE".format(source)
     samplenumber = 0
     try:
                     with open(filename) as routes_file:
                        for line in routes_file:
                            if "SAMPLE" in line:
                                samplenumber = samplenumber+1

     except IOError as e:
                     return None
     return samplenumber

def generateRouteGraphData(run_name_family, tx_power, phy_rate, antenna_mask, channel,
                       interference, protocol, source, dests=[],
                       maxdata=1):

    xValues = []
    yValues = []
    dic_hop_dest = {}
    destinations = [int(dest) for dest in dests]
    countmax = 1

    for run_name in glob.glob(f"{run_name_family}/*/"):

        if countmax > maxdata:
            break
        countmax += 1
        directory = naming_scheme(run_name=run_name, tx_power=tx_power,
                                  phy_rate=phy_rate, antenna_mask=antenna_mask,
                                  channel=channel, interference=interference,
                                  protocol=protocol)
        routes = getAllRoutes(directory /
                                     "ROUTES-{:02d}".format(source)
                                     )
        dic_hop_dest = {}
        for route in routes:
            nodes = route.split(" -- ")
            counter = 0
            target = nodes[-1]
            if int(target) in destinations:
                if "-- 0 --" in route or "-- -1 --" in route:
                    dic_hop_dest[
                    generatSourceDestRouteString(int(source),
                                                 int(nodes[-1]))] = 0

                    continue
                for node in nodes:
                    if counter > 0 and target == node:
                        dic_hop_dest[
                                    generatSourceDestRouteString(int(source),
                                                        int(node))] = counter

                    counter += 1
        for route, hops in dic_hop_dest.items():
            xValues.append(route)
            yValues.append(hops)
    return xValues, yValues
