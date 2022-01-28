#!/usr/bin/env python3
#

import sys
import zmq
import numpy as np
import argparse
from struct import unpack
import time
import logging


class TrdboxHeader:

    def __init__(self, data):

        # ( self.magic, self.equipment_type, self.equipment_id, self.version,
        # self.header_size, self.payload_size )

        # parse the first 3 data words
        (magic, ety,eid,ver, hsz,psz)= unpack("IBBxBxBH",data[0:12])

        # get the dwords of the header
        dw = np.frombuffer(data[:hsz], dtype=np.uint32)

        if magic == 0xDA7AFEED:
            logging.info(f"hdr00  {dw[0]:08x}  magic token")
        else:
            logging.error(f"hdr00  {dw[0]:08x}  unknown magic token")
            raise AssertionError('invalid magic token')

        logging.info(f"hdr00  {dw[1]:08x}  equipment {ety:02X}:{eid:02X} header version v{ver}")
        logging.info(f"hdr00  {dw[2]:08x}  hdr:{hsz}b  payload: {psz}=0x{psz:04X}b 0x{psz//4:X} dwords")

        self.equipment_type = ety
        self.equipment_id = eid
        self.header_size = hsz
        self.payload_size = psz

        # parse the time information
        if ver in [1]:
            ( sec, ns ) = unpack("II",data[12:20])
            self.timestamp = float(sec) + float(ns)*1e-9

        logging.info(f"hdr00  {dw[3]:08x}  {time.ctime(self.timestamp)}")
        # logging.info(f"hdr00  {dw[3]:08x}  {time.ctime(time.gmtime(sec))}")
        logging.info(f"hdr00  {dw[4]:08x}  {ns}")




    # def __str__(self):
    #
    #     r = ""
    #     for i,d in enumerate(self.dword):
    #         r += f"hdr{i:02x}  {d:08x}  {self.describe_dword(i,d)}\n"
    #     return r

    def equipment(self):
        return self.equipment_type<<8 | self.equipment_id

    # def describe_dword(self,i,d):
    #
    #     if i==0:
    #         if d == 0xDA7AFEED:
    #             return "magic token"
    #         else:
    #             return "ERROR: unknown magic token"
    #
    #     if i==1:
    #         (ety,eid,ver) = (self.equipment_type,self.equipment_id,self.version)
    #         return f"equipment {ety:02X}:{eid:02X} header version v{ver}"
    #
    #     if i==2:
    #         (h,p) = (self.header_size, self.payload_size)
    #         return f"hdr:{h}b  payload: {p}=0x{p:04X}b 0x{p//4:X} dwords"
    #
    #     if i==3:
    #         return time.ctime(self.timestamp)
    #         # return time.ctime(time.gmtime(self.timestamp))
