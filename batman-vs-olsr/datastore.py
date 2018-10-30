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

# all parameters must be named
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



interference_line = (
    r'.*interference=(?P<interference>[\w]+) '
    r'from scrambler=(?P<scrambler_id>[0-9]+)'
)

# parse trace file
def retrieve_scrambler_id(run_name, protocol, interference):
    root = naming_scheme(run_name=run_name, protocol=protocol,
                         interference=interference)
    traces = root.glob("trace*")
    for tracepath in traces:
        with tracepath.open() as trace:
            for line in trace:
                match = re.match(interference_line, line)
                if match:
                    interference = match.group('interference')
                    scrambler_id = match.group('scrambler_id')
                    return int(scrambler_id) if interference != "None" else None

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
Packet = namedtuple( 'Packet', ['icmp_seq', 'rtt'] )

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
                        icmp_seq=int(match.group('icmp_seq')),
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
    return PingDetails(RTT=rtt, PDR=pdr)


####################
from customcolors import CustomColors
from bokeh.palettes import Viridis

PDR_COLORS = CustomColors(
    ticks=((-1, 'left'), (0., 'left'), 0.5, (1., 'right')),
    # we need one more color than ticks
    colors=["red", "green", "yellow", "orange", "black"])


RTT_COLORS = CustomColors(
    ticks=((0., 'left'), 1., 2., 3., 5., 10., 30., 100.),
    # we need one more color than ticks
    colors=['red'] + list(reversed(Viridis[8])))

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
            ping_details = PingDetails(PDR=-1, RTT=0.)
        else:
            ping_filename = (
                directory / f"PING-{source_id:02d}-{destination_id:02d}")
            ping_details = read_ping_details(ping_filename)
        dataframe.loc[source_id]['PDR'] = ping_details.PDR
        dataframe.loc[source_id]['RTT'] = ping_details.RTT
        # I could not get bokeh's colormapper system to
        # work exactly for me, so let's apply a home-made mapper
        # and store the result in separate columns
        dataframe.loc[source_id]['PDRC'] = PDR_COLORS.color(ping_details.PDR)
        dataframe.loc[source_id]['RTTC'] = RTT_COLORS.color(ping_details.RTT)



#######
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

def get_nodes_from_routes(routes):
    nodes = []
    for route in routes:
        nodes.extend(route.split(" -- "))
    return list(set(nodes))


def get_edges_from_routes(dot, routes):
    # keep track to avoid dups
    matrix = set()
    for route in routes:
        if "-- 0 --" in route:
            continue
        nodes = route.split(" -- ")
        if "-- -1 --" not in route:
            for prev, next in zip(nodes, nodes[1:]):
                if (prev, next) not in matrix:
                    dot.edge(prev, next)
                    matrix.add((prev, next))
        else:
            nodes.remove('-1')
            for i in range(0, len(nodes)-2):
                dot.edge(nodes[i], nodes[i+1], color="red")
            dot.edge(nodes[len(nodes)-3],
                     nodes[len(nodes) - 1],
                     label="LOOP FOR ROUTES TO THIS DEST",
                     color="red")
    return dot


def routing_graph(run_name, interference,
                  source, protocol):
    scrambler_id = retrieve_scrambler_id(run_name, protocol, interference)
    node_to_pos, _, _ = maps(lambda x: x+1, lambda y: 5-y)
    dot = Digraph(comment=f'Routing table for fit{source:02d}',
                  engine='fdp')
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
    routes = get_all_routes(directory / "ROUTES-{:02d}".format(source))
    nodes = get_nodes_from_routes(routes)
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
            shape = "doublecircle"
            fillcolor = "red" if node_id == source else "white"
            fontcolor = "white" if node_id == source else "black"
            dot.node(str(node_id), '{:02d}'.format(node_id),
                     pos=f"{x},{y}!",
                     shape=shape,
                     style='filled',
                     fillcolor=fillcolor,
                     fontcolor=fontcolor,
                     )
    if nodes:
        dot = get_edges_from_routes(dot, routes)

        return dot
