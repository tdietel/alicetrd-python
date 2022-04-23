#!/usr/bin/env python3

import click
import logging

from .header import TrdboxHeader
# from .trdfeeparser import TrdFeeParser, logflt
from .rawlogging import ColorFormatter
from .o32reader import o32reader
from .zmqreader import zmqreader

class digits_csv_file:

    def __init__(self,filename="digits.csv", ntimebins=30):
        self.outfile = open(filename,"w")
        self.ntimebins = ntimebins
        self.outfile.write("ev,det,rob,mcm,channel,padrow,padcol")
        for i in range(self.ntimebins):
            self.outfile.write(f",A{i:02}")
        self.outfile.write("\n")

    def __call__(self,ev,det,rob,mcm,ch,digits):
        # TODO: calculate pad row/column from rob/mcm/channel
        padrow = -1
        padcol = -1

        # save output to file
        self.outfile.write(f"{ev},{det},{rob},{mcm},{ch},{padrow},{padcol},")
        self.outfile.write(",".join([str(x) for x in digits]))
        self.outfile.write("\n")

@click.command()
@click.argument('source', default='tcp://localhost:7776')
@click.option('-o', '--loglevel', default=logging.INFO)
@click.option('-k', '--skip-events', default=0)
def rec_digits(source, loglevel, skip_events):

    ch = logging.StreamHandler()
    ch.setFormatter(ColorFormatter())
    logging.basicConfig(level=loglevel, handlers=[ch])

    # Run silently
    logflt.set_verbosity(0)


    # Instantiate the reader that will get events and subevents from the source
    if source.endswith(".o32") or source.endswith(".o32.bz2"):
        reader = o32reader(source)
    elif source.startswith('tcp://'):
        reader = zmqreader(source)
    else:
        raise ValueError(f"unknown source type: {source}")

    # The actual parsing of TRD subevents is handled by the LinkParser
    lp = LinkParser(store_digits=digits_csv_file("digits.csv"))

    # Loop through events and subevents
    for evno,event in enumerate(reader):
        lp.next_event()

        if evno<skip_events:
            continue

        for subevent in event.subevents:
            lp.process(subevent.payload)
