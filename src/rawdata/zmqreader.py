#!/usr/bin/env python3
#

import sys
import zmq
import numpy as np
import argparse
from struct import unpack
import time
import click
import logging
from typing import NamedTuple
from datetime import datetime

from .header import TrdboxHeader
# from .trdfeeparser import TrdFeeParser, logflt
# from .rawlogging import ColorFormatter
# from .rawlogging import AddLocationFilter

# create logger with 'spam_application'
logger = logging.getLogger(__name__)

# # create console handler with a higher log level
# ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)

# ch.setFormatter(CustomFormatter())
# logger.addHandler(ch)

class event_t(NamedTuple):
    timestamp: datetime
    subevents: tuple

class subevent_t(NamedTuple):
    # timestamp: datetime
    equipment_type: int
    equipment_id: int
    payload: np.ndarray


class zmqreader:
    """Reader class for events distributed over ZeroMQ.

    The class can be used as an iterator over events in the file."""


    def __init__(self, source, equipments=None):

        #  Socket to talk to server
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)

        logging.info(f"Subscribing to ZeroMQ publisher at {source}")
        self.socket.connect(source)

        # Subscribe to data feed
        magicbytes = np.array([0xDA7AFEED],dtype=np.uint32).tobytes()

        if equipments is None:
            self.socket.setsockopt(zmq.SUBSCRIBE, magicbytes)
        else:
            for eq in equipments:
                filter = magicbytes + (eq).to_bytes(1,'little');
                self.socket.setsockopt(zmq.SUBSCRIBE, filter)

    def __iter__(self):
        return self

    def __next__(self):

        rawdata = self.socket.recv()

        header = TrdboxHeader(rawdata)
        if header.equipment_type == 0x10:
            payload = np.frombuffer(rawdata[header.header_size:], dtype=np.uint32)

            subevent = subevent_t(header.equipment_type, header.equipment_id, payload)

            return event_t(header.timestamp, tuple([subevent]))

        else:
            raise ValueError(f"unhandled equipment type 0x{header.equipment_type:0x2}")

        # logging.info(header, end="")
