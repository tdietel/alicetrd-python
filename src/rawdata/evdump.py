#!/usr/bin/env python3

import click
import logging
import sys
import os
import subprocess
import itertools
from pprint import pprint

from rawdata.base import DumpParser

from .header import TrdboxHeader
from .trdfeeparser import TrdFeeParser, TrdCruParser
# from .trdfeeparser import logflt
from .rawlogging import ColorFormatter, HexDump
from .o32reader import o32reader
from .tfreader import TimeFrameReader, RdhStreamParser
from .zmqreader import zmqreader
from .minidaqreader import MiniDaqReader

class StdoutHandler(logging.StreamHandler):

    def __init__(self):
        super().__init__(sys.stdout)
        self.setFormatter(ColorFormatter())

        ## It would be nice to open a pager directly...
        # self.pipe = os.pipe2(O_NONBLOCK | O_CLOEXEC)
        # self.pager = subprocess.run(["less", "-r"], stdin=sys.stdout)
        # self.setStream(sys.stdout)

    def handleError(self, record):
        t, v, tb = sys.exc_info()
        if t==BrokenPipeError:
            sys.stderr.write("bla")
            raise SystemExit(0)

        else:
            super().handleError(record)

@click.command()
@click.argument('source', default='tcp://localhost:7776')
@click.option('-o', '--loglevel', default=logging.INFO)
@click.option('-s', '--suppress', multiple=True)
@click.option('-q', '--quiet', count=True)
@click.option('-k', '--skip-events', default=0)
@click.option('-t', '--tracklet-format', default="run3")
def evdump(source, loglevel, suppress, quiet, skip_events, tracklet_format):

    lh = StdoutHandler()
    logging.basicConfig(level=loglevel, handlers=[lh])

    # Select dwords to suppress
    # logflt.set_verbosity(9)
    # for s in suppress:
    #     logflt.dword_types[s.upper()]['suppress'] = True

    # The parsing of TRD FEE data will be handled by the TrdFeeParser
    # At this point, we can add options to tune it's behaviour
    lp = TrdFeeParser()
    # lp.set_skip_events(skip_events)

    hdump = HexDump()

    # Instantiate the reader that will get events and subevents from the source
    if source.endswith(".o32") or source.endswith(".o32.bz2"):
        reader = o32reader(source)
        reader.set_trd_fee_parser(lp)

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
        payloadparser = TrdFeeParser(tracklet_format=tracklet_format)
        reader.parsers[0x10] = payloadparser

    elif source.startswith('tcp://'):
        reader = zmqreader(source)
    else:
        raise ValueError(f"unknown source type: {source}")

    # We leave the rest to the reader
    reader.process(skip_events=skip_events)

    # try:

    #     # Loop through events and subevents
    #     for evno,event in enumerate(reader):
    #         if evno<skip_events:
    #             continue

    #         for subevent in event.subevents:
    #             lp.process(subevent.payload)

    # except BrokenPipeError:
    #     return
