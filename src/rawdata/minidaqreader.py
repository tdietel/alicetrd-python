#!/usr/bin/env python3
#

import logging
from sqlite3 import DataError
import numpy as np
from struct import unpack

from .rawlogging import AddLocationFilter, HexDump
from .base import BaseParser, BaseHeader
from .bitstruct import BitStruct
from .header import TrdboxHeader

logger = logging.getLogger(__name__)
logflt = AddLocationFilter()
logger.addFilter(logflt)




class MiniDaqReader:
    """Reader class for MiniDAQ files 

    The class can be used as an iterator over events in the file."""

    def __init__(self, filename):
        self.file = open(filename,"rb")
        self.parsers = dict()
        # self.log_header = lambda x: x.hexdump()
        # self._skipped_stf = dict()

    def process(self, skip_events=0):
        while self.file.readable():
            addr = self.file.tell()
            data = self.file.read(20)
            if len(data)==0:
                break
            hdr = TrdboxHeader(data)
            self.log_header(hdr)

            if hdr.equipment_type in self.parsers:
                self.parsers[hdr.equipment_type].read(self.file, hdr.payload_size)

            else:
                self.file.seek(hdr.payload_size, 1)  # skip over payload
        #self.log_skipped_stf()

    def log_header(self, hdr):
        logging.getLogger("raw.o2h").info(hdr)

    def log_skipped_stf(self):
        if len(self._skipped_stf) > 0:
            msg = "... skipped STFs: "
            for key,count in self._skipped_stf.items():
                msg += f" {key}({count})"
            logging.getLogger("raw.o2h").info(msg)





