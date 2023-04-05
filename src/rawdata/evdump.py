#!/usr/bin/env python3

import click
import logging
# from pprint import pprint

from rawdata.base import DumpParser

from .factory import make_reader
# from .header import TrdboxHeader
from .rawlogging import StdoutHandler, HexDump
# from .trdfeeparser import TrdFeeParser, TrdCruParser


@click.command()
@click.argument('source', default='tcp://localhost:7776')
@click.option('-o', '--loglevel', default=logging.INFO)
@click.option('-s', '--suppress', multiple=True)
@click.option('-q', '--quiet', count=True)
@click.option('-k', '--skip-events', default=0)
@click.option('-t', '--tracklet-format', default="auto")
def evdump(source, loglevel, suppress, quiet, skip_events, tracklet_format):

    # Configure logging with a handler that works better with less
    # This handler terminates the programme when a pipe into less terminates.
    lh = StdoutHandler()
    logging.basicConfig(level=loglevel, handlers=[lh])

    # # This is how parts of the hexdump can be deactivated
    # logging.getLogger("rawlog").setLevel(logging.WARNING)
    # logging.getLogger("rawlog.mcm").setLevel(logging.WARNING)
    # logging.getLogger("rawlog.mcm.ADC").setLevel(logging.WARNING)
    # logging.getLogger("rawlog.mcm.EOD").setLevel(logging.INFO)


    # We leave the rest to the reader
    reader = make_reader(source)
    reader.add_trd_parser(tracklet_format=tracklet_format)
    reader.process(skip_events=skip_events)

