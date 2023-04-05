#!/usr/bin/env python3

import click
import logging
# from pprint import pprint

from rawdata.base import DumpParser

from .header import TrdboxHeader
from .trdfeeparser import TrdFeeParser, TrdCruParser
from .rawlogging import StdoutHandler, HexDump
from .o32reader import o32reader
from .tfreader import TimeFrameReader, RdhStreamParser
from .zmqreader import zmqreader
from .minidaqreader import MiniDaqReader


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
    # logging.getLogger("rawlog.mcm").setLevel(logging.WARNING)
    # logging.getLogger("rawlog.mcm.ADC").setLevel(logging.WARNING)
    # logging.getLogger("rawlog.mcm.EOD").setLevel(logging.INFO)

    # The parsing of TRD FEE data will be handled by the TrdFeeParser
    # At this point, we can add options to tune it's behaviour
    trdfeeparser = TrdFeeParser(tracklet_format=tracklet_format)

    hdump = HexDump()

    # Instantiate the reader that will get events and subevents from the source
    if source.endswith(".o32") or source.endswith(".o32.bz2"):
        reader = o32reader(source)
        reader.set_trd_fee_parser(trdfeeparser)

    elif source.endswith(".tf"):
        reader = TimeFrameReader(source)
        # reader.log_header = lambda x: x.hexdump()

        # payloadparser = DumpParser(logging.getLogger("raw.rdh.payload"))
        payloadparser = TrdCruParser()
        payloadparser.hexdump = hdump
        rdhparser = RdhStreamParser(payloadparser)
        rdhparser.hexdump = hdump
        reader.parsers['TRD'] = rdhparser

    elif source.endswith(".lnk"):
        reader = TimeFrameReader(source)
        # payloadparser = DumpParser(logging.getLogger("raw.rdh.payload"))
        payloadparser = TrdCruParser()
        rdhparser = RdhStreamParser(payloadparser)
        reader.parsers['TRD'] = rdhparser


    elif source.endswith('.bin'):
        reader = MiniDaqReader(source)
        reader.hexdump = hdump
        reader.parsers[0x10] = trdfeeparser

    elif source.startswith('tcp://'):
        reader = zmqreader(source)
    else:
        raise ValueError(f"unknown source type: {source}")

    # We leave the rest to the reader
    reader.process(skip_events=skip_events)

