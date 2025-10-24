#!/usr/bin/env python3

"""
exact same logic but uses apssh's YAML loader
to build the scenario
"""

from asynciojobs import Scheduler
from apssh import SshNode, HostFormatter
from apssh import YamlLoader

# for the epilogue that runs a command locally
import asyncio
from asynciojobs import Job

GWNAME = "faraday.inria.fr"
SLICE = "inria_admin"
NODES = ['fit01', 'fit02']

def main(nodename1, nodename2, *, verbose=True):

    # of course you choose which are the moving parts
    # in your own use case
    # here we decide for this set of parameters between
    # the Python part and the template
    # also, a real code would probably use names like
    # gateway, sender and receiver instead of
    # gwname, nodename1 and nodename2
    # but we want to claerly differentiate between
    # - the jinja variables (like gwname),
    # - the YAML hard-wired names (like gateway)
    # - the YAML ids (like faraday)
    # which are all in their own namespace
    jinja_variables = dict(
        slice=SLICE,
        gwname=GWNAME,
        nodename1=nodename1,
        nodename2=nodename2,
        verbose=verbose,
    )

    # the input is first passed to jinja for expansing
    # the {{variable}} expresssions,
    # and then to the yaml loader per se, hence the double extension
    loader = YamlLoader("demo-v2.yaml.j2")

    # save_intermediate means we will save
    # the output of jinja in "demo-v2.yaml" for debugging/inspection

    scheduler = loader.load(jinja_variables, save_intermediate = verbose)

    # adopt current verbosity in resulting scheduler
    scheduler.verbose = verbose

    # debug: to visually inspect the full scenario
    # see also demo-v1.py for more options on graphic output
    if verbose:
        complete_output = "demo-v2"
        print(f"Verbose: storing full scenario in {complete_output}.svg")
        scheduler.export_as_svgfile(complete_output)

    ok = scheduler.orchestrate()
    if not ok:
        scheduler.debrief()

if __name__ == '__main__':
    # set verbose to True to see more details
    main(*NODES, verbose=False)
