#!/usr/bin/env python3
#

import logging
import time

from .rawlogging import AddLocationFilter, HexDump
from .base import BaseHeader
from .bitstruct import BitStruct

logger = logging.getLogger(__name__)
logflt = AddLocationFilter()
logger.addFilter(logflt)

@BitStruct( # each line corresponds to a 64-bit word
    magic=32, # word0
    equipment_type=8, equipment_id=8, res0=8, version=8, # word1
    res1=8, hdrsize=8, datasize=16, # word2
    sec=32, nanosec=32) # word3, word4
class MiniDaqHeader(BaseHeader):

    def __init__(self, data, addr):

        super().__init__(data,addr)

        # parse the time information
        if self.version in [1]:
            # ( sec, ns ) = unpack("II",data[12:20])
            self.timestamp = float(self.sec) + float(self.nanosec)*1e-9
            self.time = time.ctime(self.timestamp)

    def equipment(self):
        return self.equipment_type<<8 | self.equipment_id

    # hexdump formatting info

    _hexdump_desc = [ "MiniDAQ magic word {magic}", 
        "equipment {equipment_type:02X}:{equipment_id:02X} header version v{version}",
        "hdr:{hdrsize} bytes  payload: {datasize}=0x{datasize:04X} bytes",
        "{time}", "" ]

    _hexdump_fmt = ('\033[1;37;40m', '\033[0;37;100m')

class MiniDaqReader:
    """Reader class for MiniDAQ files 

    The class can be used as an iterator over events in the file."""

    def __init__(self, filename):
        self.file = open(filename,"rb")
        self.parsers = dict()
        self.hexdump = lambda x: None # Default: no logging
        self.event = 0

    def process(self, skip_events=0):
        """Read entire file."""
        while self.file.readable():
            self.read(20)

    def read(self, size):
        addr = self.file.tell()
        data = self.file.read(20)
        if len(data)==0:
            return

        hdr = MiniDaqHeader(data, addr)
        self.hexdump(hdr)

        if hdr.equipment_type == 1:
            # eq. type 1 is a MiniDaq event, which contains subevents 
            self.read(hdr.datasize)
        elif hdr.equipment_type in self.parsers:
            self.parsers[hdr.equipment_type].reset()
            self.parsers[hdr.equipment_type].read(self.file, hdr.datasize)
            
        else:
            self.file.seek(hdr.datasize, 1)  # skip over payload






