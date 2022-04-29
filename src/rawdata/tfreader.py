#!/usr/bin/env python3
#

import logging
from sqlite3 import DataError
import numpy as np
from struct import unpack

from .rawlogging import AddLocationFilter
from .base import BaseParser, BaseHeader
from .bitstruct import BitStruct

logger = logging.getLogger(__name__)
logflt = AddLocationFilter()
logger.addFilter(logflt)


class DataHeader:
    def __init__(self, rawdata, addr):
        if not isinstance(rawdata,bytes) or len(rawdata)!=0x60:
            raise TypeError(f"Invalid DataHeader raw data format {len(rawdata)}")

        self.parse(rawdata)
        self.log(rawdata, addr)

    def parse(self, rawdata):

        # 1st dword
        fields = unpack('<4sLLL', rawdata[0x00:0x10])
        self.magic = fields[0].rstrip(b'\0').decode()
        self.hdrsize, self.flags, self.version = fields[1:4]

        # 2nd dword
        fields = unpack('<8s4s4s', rawdata[0x10:0x20])
        self.hdrdesc = fields[0].rstrip(b'\0').decode()
        # 2 padding/ignored fields

        # 3rd dword
        # fields = unpack('<16s', rawdata[0x20:0x30])
        self.datadesc = rawdata[0x20:0x30].rstrip(b'\0').decode()

        # 4th dword
        fields = unpack('<4sL4sL', rawdata[0x30:0x40])
        self.origin = fields[0].rstrip(b'\0').decode()
        # ignore serialization method
        self.nparts = fields[1]
        self.subspec = fields[3]

        # 5th dword
        fields = unpack('<LLQ', rawdata[0x40:0x50])
        self.subspec, self.part, self.datasize = fields

        # 6th dword
        fields = unpack('<LLL4s', rawdata[0x50:0x60])
        self.orbit, self.tfcount, self.runno = fields[0:3]
        
    def __str__(self):
        return f"{self.magic} 0x{self.hdrsize:X} - {self.datadesc} - {self.origin}/{self.subspec} {self.runno} {self.part} flags=0x{self.flags:X} payload = {self.datasize}b parts={self.nparts}"

    def log(self, data, addr):
        for i, dw in enumerate(unpack("<24L", data)):
            hl = 'h' if i % 2 else 'l'
            logging.getLogger("raw.o2h").info(
                f"{addr+4*i:012X} {dw:08X}    O2DH  "
                + self.describe_dword(i))

    def describe_dword(self, i):
        dword_desc = list((
            "============== {magic} ==============", "", "", "",
            "{hdrdesc}", "", "", "",
            "{datadesc}", "", "", "",
            "{origin}", "part {part} (of {nparts})", "", "",
            "", "", 
            "0x{datasize:012X} = {datasize} bytes", 
            "",
            "", "","","----------------------------------"
        ))

        return dword_desc[i].format(**vars(self))

@BitStruct( # each line corresponds to a 64-bit word
    version=8, hdrsize=8, fee=16, prio=8, src=8, zero0=16, # word0
    offset=16, datasize=16, link=8, count=8, cru=12, ep=4, # word1
    bc=12, res1=20, orbit=32, # word2
    zero2=64, # word3
    trg=32, pagecnt=16, stop=8, zero4=8, # word4
    zero5=64,  # word5
    detfield=32, detpar=16, zero6=16,  # word6
    zero7=64) # word7
class RawDataHeader(BaseHeader):
    def __init__(self,data,addr):
        super().__init__(data,addr)
        assert(self.zero7==0)
        
        self._hexdump_desc[0] = "RDHv{version} fee={fee}"
        # self._hexdump_desc[8:16] = ""

        # for i, desc in enumerate(self._hexdump_desc):
        #     self._hexdump_desc[i] = f"RDH[{i//2}.{i%2}]  {desc}"


        # self._hexdump_desc = [
        #     "RDHv{version} fee={fee}",
        #     "pri={prio} src={src}",
        #     "size=0x{datasize:04X} next=0x{offset:04X}",
        #     "link={link} count={count} cru={cru} ep={ep}",
        #     "", "", "", "", 
        #     "", "", "", "", 
        #     "", "", "", ""]



# class RawDataHeader(BaseHeader):
#     """ RDH v6 
        
#     https: // gitlab.cern.ch/AliceO2Group/wp6-doc/-/blob/master/rdh/RDHv6.md"""

#     header_size=0x40

#     def __init__(self, data, addr):
#         # if not isinstance(rawdata, np.ndarray) or len(rawdata) != 16:
#         if not isinstance(data, bytes) or len(data) != 0x40:
#             raise TypeError(f"Invalid DataHeader raw data format {type(data)} {len(data)}")

#         self.parse(data)
#         self.log(data, addr)

#     def parse(self, data):
#         fieldinfo = dict(
#             version="B", hdrsize="B", fee_id="H",
#             prio="B", src_id="B", reserved_0="H",
#             offset="H", datasize="H",
#             link="B", count="B", cru_ep="H")

#         fielddata = unpack("<" + "".join(fieldinfo.values()), data[0:16])
#         for k,v in zip(fieldinfo.keys(), fielddata):
#             if k.startswith("reserved_"):
#                 next
#             elif k=="cru_ep":
#                 # possible improvement: decode CRU and endpoint (EP)
#                 next
#             else:
#                 setattr(self,k,v)

#         self.payload_size = self.datasize - self.header_size

#         if self.src_id == 4:
#             self.id_desc = f"TRD-{self.fee_id:04d}"
#         else:
#             self.id_desc = f"SRC={self.src_id} FEE={self.fee_id}"

#     def log(self, data, addr):

#         for i, dw in enumerate(unpack("<16L", data)):
#             hl = 'h' if i % 2 else 'l'
#             logging.getLogger("raw.rdh").info(
#                 f"{addr+4*i:012X} {dw:08X}    RDH[{i//2}{hl}]  "
#                 + self.describe_dword(i))

#     def describe_dword(self,i):
#         dword_desc = list((
#             "RDHv{version}({hdrsize}) bytes fee={fee_id}", 
#             "{id_desc}", 
#             "size={datasize}", "", "", "", "", "", "", "", "", "", "", "", "", ""
#         ))

#         return dword_desc[i].format(**vars(self))



class TimeFrameReader:
    """Reader class for ALICE O2 time frames.

    The class can be used as an iterator over events in the file."""

    def __init__(self, filename):
        self.file = open(filename,"rb")
        self.parsers = dict()

    def process(self, skip_events=0):
        while self.file.readable():
            addr = self.file.tell()
            data = self.file.read(0x60)
            if len(data)==0:
                break
            hdr = DataHeader(data, addr)

            if hdr.origin in self.parsers:
                self.parsers[hdr.origin].read(self.file, hdr.datasize)

            else:
                self.file.seek(hdr.datasize, 1)  # skip over payload


class RdhStreamParser(BaseParser):
    def __init__(self, payload_parser):
        self.parser = payload_parser

    def read(self, stream, size):

        maxpos = stream.tell()+size
        while stream.tell() < maxpos:
            if size < RawDataHeader.header_size:
                raise DataError("Insufficient data")

            rdh = RawDataHeader.read(stream)
            payload_size = rdh.datasize - RawDataHeader.header_size
            self.parser.read(stream, payload_size)



if __name__=="__main__":
    reader = TimeFrameReader(
        "/Users/tom/cernbox/data/noise/504419/o2_rawtf_run00504419_tf00006252.tf")



