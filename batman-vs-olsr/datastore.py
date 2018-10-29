#!/usr/bin/env python3

# pylint: disable=c0111, c0103, w0511, r0913, r0914, r1710

import sys
import re
from pathlib import Path
from datetime import datetime

from collections import defaultdict, namedtuple

# should go away eventually
import glob

from graphviz import Digraph

from r2labmap import maps

####################

from constants import (
    WIRELESS_DRIVER, TX_POWER, PHY_RATE, CHANNEL, ANTENNA_MASK)

# + force to name all parameters
def naming_scheme(*, run_name, protocol, interference,
                  autocreate=False):
    """
    Returns a pathlib Path instance that points at the directory
    where all tmp files and results are stored for those settings

    if autocreate is set to True, the directory is created if needed,
    and a message is printed in that case
    """
    root = Path(run_name)
    run_root = root / (f"t{TX_POWER}-r{PHY_RATE}-a{ANTENNA_MASK}"
                       f"-ch{CHANNEL}-I{interference}-{protocol}")
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
Packet = namedtuple(
    'Packet',
    ['id', 'rtt']
    )

PingDetails = namedtuple(
    'PingDetails',
    ['PDR', 'RTT'])


def read_ping_details(filename, warning=True):
    """
    Return a PingDetails resulting from parsing a PING file
    """

    # how many packets have we tried to send ?
    # this is in the header line written out by my-ping
    header_line = (
        r'ping .* -c (?P<nb_packets>[0-9]+) .*'
    )

    # parse each packet line
    packet_line = (
        r'.*: '
        r'icmp_seq=(?P<icmp_seq>[0-9]+) '
        r'ttl=(?P<ttl>[0-9]+) '
        r'time=(?P<rtt>[0-9.]+) ms'
    )

    nb_packets = None
    packets = []

    # returned if something goes wrong
    oops = PingDetails(PDR=1., RTT=10**10)

    try:
        with open(filename) as ping_file:
            for line in ping_file:
                match = re.match(header_line, line)
                if match:
                    nb_packets = int(match.group('nb_packets'))
                    continue

                match = re.match(packet_line, line)
                if match:
                    packets.append(Packet(
                        id=int(match.group('icmp_seq')),
                        rtt=float(match.group('rtt')),
                    ))
                    continue

    except IOError:
        if warning:
            path = Path(filename)
            print("{} was not generated in these conditions: {}"
                  .format(path.name, path.parent))

    if not nb_packets:
        print("OOPS, {filename} has no header line, can't figure nb_packets")
        return oops

    if not packets:
        # this actually happens in very bad network conditions,
        # and is not so unfrequent
        # print(f"OOPS, {filename} has no packet line")
        return oops

    pdr = 1 - len(packets) / nb_packets
    rtt = sum(packet.rtt for packet in packets) / len(packets)
    return PingDetails(RTT=rtt, PDR = pdr)


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

def is_decimal(string):
    try:
        return int(string)
    except ValueError:
        return None

#
def get_info(run_root, input_type):
    # find most recent file named trace-??-??-??
    traces = Path(run_root).glob("trace-??-??-??")
    def mod_time(path):
        return path.stat().st_mtime
    recent_first = sorted(traces, key=mod_time, reverse=True)
    try:
        with recent_first[0].open() as trace_file:
            for line in trace_file:
                if input_type not in line:
                    continue
                converted = (is_decimal(x) for x in line.split())
                return [x for x in converted if x]
    except IOError:
        print("Experiment was not run in these conditions : {}"
              .format(run_root))
    return []

####################
from customcolors import CustomColors
from bokeh.palettes import inferno, Blues

RTT_COLORS = CustomColors(
    ticks=(0., 1., 3., 5., 10., 30., 100.),
    # we need one more color than ticks
    colors=inferno(8))

PDR_COLORS = CustomColors(
    ticks=(0., 0.05, 0.3, 0.5, 0.7, 0.95, 1.),
    # we need one more color than ticks
    colors=Blues[8])


def details_from_all_senders(dataframe, run_name,
                             protocol, interference,
                             destination_id, sources):
    """
    fill input dataframe with RTT and PDR
    for all sender nodes to this receiver node
    """

    directory = naming_scheme(run_name=run_name, protocol=protocol,
                              interference=interference)

    for source_id in sources:
        if source_id == destination_id:
            ping_details = PingDetails(PDR=0., RTT=0.)
        else:
            ping_filename = (
                directory / f"PING-{source_id:02d}-{destination_id:02d}")
            ping_details = read_ping_details(ping_filename)
        dataframe.loc[source_id]['PDR'] = ping_details.PDR
        dataframe.loc[source_id]['RTT'] = ping_details.RTT
        # I could not get bokeh's colormapper system to
        # work exactly for me, so let's apply a home-made mapper
        # and store the result in separate columns
        dataframe.loc[source_id]['PDRC'] = PDR_COLORS.apply(ping_details.PDR)
        dataframe.loc[source_id]['RTTC'] = RTT_COLORS.apply(ping_details.RTT)



#######
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


# xxx need to read scrambler_id from the trace file in the results dir
def routing_graph(run_name, interference,
                  source, protocol, *, scrambler_id=5, sample=None):
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
        pos = f"{x},{y}!"
        if interference != "None" and node_id == scrambler_id:
            dot.node("", pos=pos,
                     image="scrambler.png",
                     )
        elif str(node_id) not in nodes:
            dot.node(str(node_id), '{:02d}'.format(node_id),
                     pos=pos, shape='point')
        else:
            dot.node(str(node_id), '{:02d}'.format(node_id),
                     pos=f"{x},{y}!",
                     shape='doublecircle',
                     )
    if nodes:
        dot = getEdgesFromRoutes(dot, routes)

        return dot
