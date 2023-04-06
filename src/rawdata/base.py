
import numpy # probably overkill - replace with struct.unpack?
import logging
import struct

class BaseParser:
    """Parser base class
    
    A parser is a class that parses binary data."""

    def parse(self, data, addr):
        """Virtual parser function
        
        This function must be overloaded to implement the actual parsing
        of the data.
        
        Arguments:
          data : bytes    - data to be parsed
          addr : int      - an integer to describe the location of the data 
                            for logging, e.g. the offset in a file"""

        pass

    def read(self, stream, nbytes):
        """Helper function to read data from file and parse it."""
        addr = stream.tell()
        data = stream.read(nbytes)
        # if len(data) != nbytes:
        logging.getLogger("raw.baseparser").info(
            f"incomplete read{len(data)} of {nbytes} bytes")
        return self.parse(data,addr)


class DumpParser(BaseParser):
    def __init__(self, logger):
        self.logger = logger

    def parse(self, data, addr):
        # probably overkill - replace with struct.unpack?
        self.logger.info(f"dump buffer at {addr:X} of {len(data)} bytes")
        remainder = len(data)%4
        if remainder>0:
            data = data + b'\0'*(4-remainder)
        self.logger.info(f"dump buffer at {addr:X} of {len(data)} bytes")

        for i, x in enumerate(numpy.frombuffer(data, dtype=numpy.uint32)):
            self.logger.info(f"{addr+0x40+4*i:012X} {x:08X}")


class BaseHeader:
    header_size = 0
    _hexdump_fmt = ('\033[1;37;40m', '\033[0;37;100m')
    _hexdump_desc = ("")

    def __init__(self, data, addr):
        if not isinstance(data, bytes) or len(data) != self.header_size:
            raise TypeError(
                f"Invalid DataHeader raw data format {type(data)} {len(data)}")

        self._addr = addr
        self._data = data
        # print(self.keys())
        # print(self.unpack(data))
        for k, v in zip(self.keys(), self.unpack(data)):
            setattr(self,k,v)
        
    @classmethod
    def read(cls, stream):
        addr = stream.tell()
        data = stream.read(cls.header_size)
        # print(f"Reading {cls.__name__} at offset 0x{addr:06X}")
        header = cls(data, addr)
        # header.hexdump()
        return header

    def hexdump(self, logger):
        for i, words in enumerate(struct.iter_unpack("<L", self._data)):

            if len(self._hexdump_desc) == 1:
                desc = self._hexdump_desc
            else:
                desc = self._hexdump_desc[i]

            if len(self._hexdump_fmt) == 1:
                fmt = self._hexdump_fmt[0]
            elif len(self._hexdump_fmt) == 2:
                fmt = self._hexdump_fmt[0] if i==0 else (self._hexdump_fmt[1])
            else:
                fmt = self._hexdump_fmt[i]

            # self.dump_dword(addr+4*i, words[0], txt)
            logger.info(fmt+desc, extra=dict(hexaddr=self._addr+4*i, hexdata=words[0]))


    def unpack(self, data):
        pass

    def keys(self):
        pass

    def describe_dword(self, i):
        return ""

