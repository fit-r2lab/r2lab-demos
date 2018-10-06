#!/usr/bin/env python3

# pylint: disable=c0111, c0103, w0511, r0913, r0914, r1710

import sys
import re
import glob
from pathlib import Path
from datetime import datetime

from graphviz import Digraph

from r2labmap import maps

####################

# the constant wireless conditions
WIRELESS_DRIVER = 'ath9k'
# the minimum for atheros cards
TX_POWER = 5
# the more ambitious, the more likely to create trouble
PHY_RATE = 54
# arbitrary
CHANNEL = 10
# only one antenna seems again the most fragile conditions
ANTENNA_MASK = 1

# + force to name all parameters
def naming_scheme(*, run_name, protocol, interference,
                  tx_power=TX_POWER, phy_rate=PHY_RATE,
                  antenna_mask=ANTENNA_MASK, channel=CHANNEL,
                  autocreate=False):
    """
    Returns a pathlib Path instance that points at the directory
    where all tmp files and results are stored for those settings

    if autocreate is set to True, the directory is created if needed,
    and a message is printed in that case
    """
    root = Path(run_name)
    run_root = root / (f"t{tx_power}-r{phy_rate}-a{antenna_mask}"
                       f"-ch{channel}-I{interference}-{protocol}")
    if autocreate:
        if not run_root.is_dir():
            print(f"Creating result directory: {run_root}")
            run_root.mkdir(parents=True, exist_ok=True)
    return run_root


####################

### helpers
def apssh_time():
    now = datetime.now()
    return f"{now:%H-%M-%S}"


def time_line(line, file=sys.stdout):
    """
    write line with apssh-style timestamp prefix
    add newline if needed
    """
    file.write(f"{apssh_time()} {line}")
    if line[-1] != "\n":
        file.write("\n")


####################

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
                        *_, time, _ = line.split()
                        _, time = time.split("=")
                    else:
                        *_, time, _, _ = line.split()
                        _, time = time.split("=")
                    pings_time.append(time)

    except IOError:
        file = str(filename)
        *rest, pingfile = file.split("/")
        path = ""
        for item in rest[:-1]:
            path += item + "/"
        path += rest[-1]
        print("{} was not generated in these conditions: {}"
              .format(pingfile, path))

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
    pattern = re.compile(r'(\d{1,3}(?=%))')
    try:
        with open(filename) as pings_file:
            for line in pings_file:
                if "%" in line:
                    pdr = pattern.findall(line)

    except IOError:
        file = str(filename)
        *rest, pingfile = file.split("/")
        path = ""
        for item in rest[:-1]:
            path += item + "/"
        path += rest[-1]
        print("{} was not generated in these conditions: {}"
              .format(pingfile, path))

    return pdr


def is_valid_route(route):
    if "- 0 -" in route:
        return False
    return True


def get_all_routes(filename):
    routes = []
    try:
        with open(filename) as routes_file:
            for line in routes_file:
                routes.append(line.rstrip())
    except IOError:
        print("Routes were not generated for these conditions: {}"
              .format(filename))
    return routes


def get_all_routes_sample(filename, sampleNum):
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
    except IOError:
        print("Routes were not generated for these conditions: {}"
              .format(filename))
    return routes


def generate_source_dest_route_string(source, dest):
    return "fit{:02d} - fit{:02d}".format(source, dest)


def generate_route_list_for_block_graph(route, data):
    return [route] * len(data)


# xxx this won't work any more ...
def get_info(run_root, input_type):
    try:
        with (run_root / "info.txt").open() as info_file:
            lines = info_file.readlines()
        if input_type == "Sources":
            return lines[3].split()
        if input_type == "Destinations":
            return lines[5].split()
        if input_type == "Nodes":
            return lines[1].split()
    except IOError:
        print("Experiment was not run in these conditions : {}"
              .format(run_root))
    return []

####################

def routing_graph(run_name, interference,
                  source, protocol, sample=None):
    node_to_pos, _, _ = maps(lambda x: x+1, lambda y: 5-y)
    dot = Digraph(comment='Routing table for fit{:02d}'
                  .format(source), engine='fdp')
    dot.attr('graph', label=protocol)
    dot.attr(splines='true')
    dot.attr(rankdir='LR')
    dot.attr('graph', size='5, 3')
    # half size as default is 96 -> h=364
    # 48 -> h=243 ! how come ?
    # dot.attr(dpi='48')
    #dot.attr('node', shape='doublecircle')
    #dot.format = 'png'
    directory = naming_scheme(run_name=run_name, protocol=protocol,
                              interference=interference)
    if sample is None:
        routes = get_all_routes(directory / "ROUTES-{:02d}".format(source))
    else:
        routes = get_all_routes_sample(
            directory / "SAMPLES" / "ROUTES-{:02d}-SAMPLE".format(source),
            sample)
    nodes = getNodesFromRoutes(routes)
    nodes = list(set(nodes)- set(['0']))

    # pillars
    dot.node("  ", pos="4,4!", shape="box")
    dot.node(" ", pos="6,4!", shape="box")

    for node_id in range(1, 38):
        x, y = node_to_pos[node_id]
        if node_id == 5 and interference != "None":
            dot.node("Interference", pos="1,1!", shape="tripleoctagon")
            continue
        if str(node_id) not in nodes:
            dot.node(str(node_id), '{:02d}'.format(node_id),
                     pos=f"{x},{y}!",
                     shape='point')
        else:
            dot.node(str(node_id), '{:02d}'.format(node_id),
                     pos=f"{x},{y}!",
                     shape='doublecircle',
                     )
    if nodes:
        dot = getEdgesFromRoutes(dot, routes)

        return dot


def get_sample_count(run_name, protocol, interference, source,
                     tx_power=TX_POWER, phy_rate=PHY_RATE,
                     antenna_mask=ANTENNA_MASK, channel=CHANNEL):
    directory = naming_scheme(run_name=run_name, protocol=protocol,
                              interference=interference)
    filename = directory / "SAMPLES" / "ROUTES-{:02d}-SAMPLE".format(source)
    samplenumber = 0
    try:
        with open(filename) as routes_file:
            for line in routes_file:
                if "SAMPLE" in line:
                    samplenumber += 1

    except IOError:
        return None
    return samplenumber


def RTT_graph_data(run_name, interference, protocol, source,
                   tx_power=TX_POWER, phy_rate=PHY_RATE,
                   antenna_mask=ANTENNA_MASK, channel=CHANNEL):

    directory = naming_scheme(run_name=run_name, protocol=protocol,
                              interference=interference)
    dests = get_info(directory, "Destinations")
    xValues = []
    yValues = []
    RTT_dic = {}

    for destination in dests:
        source_id = int(source)
        destination_id = int(destination)
        if source_id != destination_id:
            if (source_id, destination_id) not in RTT_dic:
                # xxx use defaultdict
                RTT_dic[(source_id, destination_id)] = [
                    float(value)
                    for value in readRTT(
                        directory / "PING-{:02d}-{:02d}"
                        .format(source_id, destination_id))
                    ]
            else:
                RTT_dic[(source_id, destination_id)].extend([
                    float(value)
                    for value in readRTT(
                        directory / "PING-{:02d}-{:02d}"
                        .format(source_id, destination_id))])

            if not RTT_dic[(source_id, destination_id)]:
                RTT_dic[(source_id, destination_id)] = [0]

            xValues.extend(
                generate_route_list_for_block_graph(
                    generate_source_dest_route_string(source_id, destination_id),
                    RTT_dic[(source_id, destination_id)]))

            yValues.extend(RTT_dic[source_id, destination_id])

    return xValues, yValues






def graphDataMultipleRTT(
        run_name_family, tx_power, phy_rate, antenna_mask, channel,
        interference, protocol, source, dests, maxdata):

    xValues = []
    yValues = []
    RTT_dic = {}
    countmax = 0

    for run_name in glob.glob(f"{run_name_family}*/"):
        if countmax >= maxdata:
            break
        countmax += 1

        directory = naming_scheme(run_name=run_name, protocol=protocol,
                                  interference=interference)

        for destination in dests:
            source_id = int(source)
            destination_id = int(destination)
            if source_id == destination_id:
                continue
            # ditto defaultdict
            if (source_id, destination_id) not in RTT_dic:
                RTT_dic[(source_id, destination_id)] = [
                    float(value)
                    for value in readRTT(
                        directory / "PING-{:02d}-{:02d}"
                        .format(source_id, destination_id))]
            else:
                RTT_dic[(source_id, destination_id)].extend([
                    float(value)
                    for value in readRTT(
                        directory / "PING-{:02d}-{:02d}"
                        .format(source_id, destination_id))])

            if not RTT_dic[(source_id, destination_id)]:
                RTT_dic[(source_id, destination_id)] = [0]

            xValues.extend(
                generate_route_list_for_block_graph(
                    generate_source_dest_route_string(source_id, destination_id),
                    RTT_dic[(source_id, destination_id)]))

            yValues.extend(RTT_dic[source_id, destination_id])

    return xValues, yValues


def graphDataPDR(run_name, tx_power, phy_rate, antenna_mask,
                 channel, interference, protocol, source):
    directory = naming_scheme(run_name=run_name, protocol=protocol,
                              interference=interference)

    dests = get_info(directory, "Destinations")
    xValues = []
    yValues = []
    PDR_dic = {}

    for destination in dests:
        source_id = int(source)
        destination_id = int(destination)
        if source_id == destination_id:
            continue
        #print(readPDR( directory / "PING-{:02d}-{:02d}".format(source_id, destination_id)))
        PDR_dic[(source_id, destination_id)] = [
            100 - int(value)
            for value in readPDR(
                directory / "PING-{:02d}-{:02d}"
                .format(source_id, destination_id))]

        xValues.extend([generate_source_dest_route_string(source_id, destination_id)])
        yValues.extend(PDR_dic[source_id, destination_id])

    return xValues, yValues


def graphDataMultiplePDRCount(
        run_name_family, tx_power, phy_rate, antenna_mask, channel,
        interference, protocol, source, dest, maxdata):

    yValues = [0] * 101
    xValues = list(range(0, 101))
    #FOR EVERY DATA WITH RUN_NAME_FAMILY
    countmax = 0

    for run_name in glob.glob(f"{run_name_family}/*/"):
        if countmax >= maxdata:
            break
        countmax += 1
        directory = naming_scheme(run_name=run_name, protocol=protocol,
                                  interference=interference)
        pdr = [100 - int(value)
               for value in readPDR(directory / "PING-{:02d}-{:02d}"\
                                    .format(source, dest))]
        if pdr[0] != -1:
            yValues[pdr[0]] += 1

    return xValues, yValues


def graphDataMultiplePDR(
        run_name_family, tx_power, phy_rate, antenna_mask, channel,
        interference, protocol, source, dest, maxdata):

    yValues = []
    xValues = [generate_source_dest_route_string(int(source), int(dest))] * maxdata
    #FOR EVERY DATA WITH RUN_NAME_FAMILY
    countmax = 0

    for run_name in glob.glob(f"{run_name_family}/*/"):
        if countmax >= maxdata:
            break
        countmax += 1
        directory = naming_scheme(run_name=run_name, protocol=protocol,
                                  interference=interference)
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
        if "-- 0 --" not in route:
            nodes = route.split(" -- ")
            if "-- -1 --" not in route:
                for i in range(0, len(nodes)-1):
                    dot.edge(nodes[i], nodes[i+1])
            else:
                nodes.remove('-1')
                for i in range(0, len(nodes)-2):
                    dot.edge(nodes[i], nodes[i+1], color="red")
                dot.edge(nodes[len(nodes)-3],
                         nodes[len(nodes) - 1],
                         label="LOOP FOR ROUTES TO THIS DEST",
                         color="red")
    return dot


def generateRouteGraphData(
        run_name_family, tx_power, phy_rate, antenna_mask, channel,
        interference, protocol, source, dests=None,
        maxdata=1):

    if dests is None:
        dests = []

    xValues = []
    yValues = []
    dic_hop_dest = {}
    destinations = [int(dest) for dest in dests]
    countmax = 1

    for run_name in glob.glob(f"{run_name_family}/*/"):

        if countmax > maxdata:
            break
        countmax += 1
        directory = naming_scheme(run_name=run_name, protocol=protocol,
                                  interference=interference)
        routes = get_all_routes(
            directory / "ROUTES-{:02d}".format(source))
        dic_hop_dest = {}
        for route in routes:
            nodes = route.split(" -- ")
            counter = 0
            target = nodes[-1]
            if int(target) in destinations:
                if "-- 0 --" in route or "-- -1 --" in route:
                    dic_hop_dest[
                        generate_source_dest_route_string(
                            int(source), int(nodes[-1]))] = 0

                    continue
                for node in nodes:
                    if counter > 0 and target == node:
                        dic_hop_dest[
                            generate_source_dest_route_string(
                                int(source), int(node))] = counter

                    counter += 1
        for route, hops in dic_hop_dest.items():
            xValues.append(route)
            yValues.append(hops)
    return xValues, yValues
