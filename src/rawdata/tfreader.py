#!/usr/bin/env python3
#

import logging
import numpy as np
from collections import namedtuple
from collections.abc import Iterable
from struct import unpack
from typing import NamedTuple
from datetime import datetime
from struct import unpack
from functools import wraps

from .rawlogging import AddLocationFilter

logger = logging.getLogger(__name__)
logflt = AddLocationFilter()
logger.addFilter(logflt)

# class event_t(NamedTuple):
#     # timestamp: datetime
#     metadata: dict
#     subevents: tuple

# class subevent_t(NamedTuple):
#     # timestamp: datetime
#     equipment_type: str
#     equipment_id: int
#     payload: Iterable[int]
#     # payload: np.ndarray


class DataHeader:
    def __init__(self, rawdata, addr):
        if not isinstance(rawdata,bytes) or len(rawdata)!=0x60:
            raise TypeError(f"Invalid DataHeader raw data format {len(rawdata)}")

        self.parse(rawdata)
        self.log(rawdata, addr)

    def parse(self, rawdata):
        # basehdr_fmt = '4sLLL'+'8s4s4s'
        # datahdr_fmt = '16s'+'4sL4sL'+'LLQ'+'LLL4s'
        # allfields = unpack('<'+basehdr_fmt+datahdr_fmt, rawdata)

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
            "", "", "", "",
            "", "", "", "",
            "", "","","----------------------------------"
        ))

        return dword_desc[i].format(**vars(self))


class RawDataHeader:
    """ RDH v6 
        
    https: // gitlab.cern.ch/AliceO2Group/wp6-doc/-/blob/master/rdh/RDHv6.md"""


    def __init__(self, data, addr):
        # if not isinstance(rawdata, np.ndarray) or len(rawdata) != 16:
        if not isinstance(data, bytes) or len(data) != 0x40:
            raise TypeError(f"Invalid DataHeader raw data format {type(data)} {len(data)}")

        self.parse(data)
        self.log(data, addr)

    def parse(self, data):
        fieldinfo = dict(
            version="B", hdrsize="B", fee_id="H",
            prio="B", src_id="B", reserved_0="H",
            offset="H", datasize="H",
            link="B", count="B", cru_ep="H")

        fielddata = unpack("<" + "".join(fieldinfo.values()), data[0:16])
        for k,v in zip(fieldinfo.keys(), fielddata):
            if k.startswith("reserved_"):
                next
            elif k=="cru_ep":
                # possible improvement: decode CRU and endpoint (EP)
                next
            else:
                setattr(self,k,v)

        if self.src_id == 4:
            self.id_desc = f"TRD-{self.fee_id:04d}"
        else:
            self.id_desc = f"SRC={self.src_id} FEE={self.fee_id}"

    def log(self, data, addr):

        for i, dw in enumerate(unpack("<16L", data)):
            hl = 'h' if i % 2 else 'l'
            logging.getLogger("raw.rdh").info(
                f"{addr+4*i:012X} {dw:08X}    RDH[{i//2}{hl}]  "
                + self.describe_dword(i))

    def describe_dword(self,i):
        dword_desc = list((
            "RDHv{version}({hdrsize}) bytes fee={fee_id}", 
            "{id_desc}", 
            "", "", "", "", "", "", "", "", "", "", "", "", "", ""
        ))

        return dword_desc[i].format(**vars(self))



class TimeFrameReader:
    """Reader class for ALICE O2 time frames.

    The class can be used as an iterator over events in the file."""


    def __init__(self, filename):
        self.file = open(filename,"rb")
        # self.parts = np.zeros((128, 2048, 2), dtype=np.uint64)
        # self.parts = list()
        # self.parts = list((list() for i in range(0,128)))
        self.parsers = dict()
        

        # part_t = namedtuple("part_t", ["subspec", "offset", "size"])



    def process(self, skip_events=0):
        while self.file.readable():
            addr = self.file.tell()
            data = self.file.read(0x60)
            if len(data)==0:
                break
            hdr = DataHeader(data, addr)
            # logger.info(str(hdr))

            if hdr.origin in self.parsers:
                addr = self.file.tell()
                # data = self.file.read(0x60)
                data = self.file.read(hdr.datasize)
                self.parsers[hdr.origin].process(data,addr)
                # make sure we have enough space in the list
                # while len(self.parts) <= hdr.part:
                #     self.parts.append(list())

                # # append the index information
                # p = part_t(hdr.subspec, self.file.tell(), hdr.datasize)
                # self.parts[hdr.part].append(p)



                # self.parse_trd_stf(p.offset, p.size)
                # addr = self.file.tell()
                # rdh = RawDataHeader(self.file.read(0x40), addr)

                # # self.file.seek(hdr.datasize-0x40, 1)  # skip over payload
                # linkdata = np.frombuffer(self.file.read(rdh.datasize), dtype=np.uint32)
                # for i,x in enumerate(linkdata):
                #     logger.info(f"{i} {x:08X}")

            else:
                self.file.seek(hdr.datasize, 1)  # skip over payload

        # for i in range(len(self.parts)):
        #     print(f"{i:03d}   {len(self.parts[i])}")

        # print(self.parts[0])

class RdhStreamParser():
    def process(self,data,addr):
        while len(data) > 0:
                
            rdh = RawDataHeader(data[0:0x40], addr)
            payload = data[0x40:rdh.datasize]
            data = data[rdh.datasize:]
            for i, x in enumerate(np.frombuffer(payload, dtype=np.uint32)):
                logger.info(f"{addr+0x40+4*i:012X} {x:08X}")


# class TrdCruReader:




if __name__=="__main__":
    reader = TimeFrameReader(
        "/Users/tom/cernbox/data/noise/504419/o2_rawtf_run00504419_tf00006252.tf")



