#!/usr/bin/env python3
#

import logging
import time

from .rawlogging import AddLocationFilter, HexDump
from .base import BaseHeader
from .bitstruct import BitStruct
from .trdfeeparser import make_trd_parser
import struct

logger = logging.getLogger(__name__)
logflt = AddLocationFilter()
logger.addFilter(logflt)

@BitStruct( # each line corresponds to a 32-bit word
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

    def hexdump(self):
        hexlogger = logger.getChild(f"hexdump.minidaq")

        txt = list((
            f"MiniDAQ magic word 0x{self.magic:08x}",
            f"equipment {self.equipment_type:02X}:{self.equipment_id:02X} header version v{self.version}",
            f"hdr:{self.hdrsize} bytes  payload: {self.datasize}=0x{self.datasize:04X} bytes",
            f"{self.time}", ""))

        for i, words in enumerate(struct.iter_unpack("<I", self._data)):
            extra = dict(hexaddr=self._addr+4*i, hexdata=words[0])
            hexlogger.getChild(f"MQ{i}").info(txt, extra=extra)

class MiniDaqReader:
    """Reader class for MiniDAQ files 

    The class can be used as an iterator over events in the file."""

    def __init__(self, filename):
        self.file = open(filename,"rb")
        
        # find filesize
        self.file.seek(0,2)
        self.filesize =self.file.tell()
        self.file.seek(0)

        self.parsers = dict()
        self.hexdump = lambda x: None # Default: no logging
        self.event = 0

    def add_trd_parser(self, **kwargs):
        self.parsers[0x10] = make_trd_parser(has_cruheader=False, **kwargs)

    def process(self, skip_events=0):
        """Read entire file."""
        while self.file.tell() < self.filesize:
            self.read()

    def read(self):
        addr = self.file.tell()
        data = self.file.read(20)
        if len(data)!=20:
            logger.info(f"read {len(data)} bytes at offset {addr}")
            return

        hdr = MiniDaqHeader(data, addr)
        # self.hexdump(hdr)
        hdr.hexdump()

        if hdr.equipment_type == 1:
            # eq. type 1 is a MiniDaq event, which contains subevents 
            self.read()
        elif hdr.equipment_type in self.parsers:
            # self.parsers[hdr.equipment_type].reset()
            self.parsers[hdr.equipment_type].parse(self.file, hdr.datasize)
        else:
            self.file.seek(hdr.datasize, 1)  # skip over payload

        self.event += 1
        logger.warning(f"Processed {self.event} events")





