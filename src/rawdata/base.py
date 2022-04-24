
import numpy # probably overkill - replace with struct.unpack?
import logging
from struct import unpack

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

    def __init__(self, data, addr):
        if not isinstance(data, bytes) or len(data) != self.header_size:
            raise TypeError(
                f"Invalid DataHeader raw data format {type(data)} {len(data)}")

        self.parse(data)
        self.log(data, addr)

    @classmethod
    def read(cls, stream):
        addr = stream.tell()
        data = stream.read(cls.header_size)
        return cls(data,addr)

    def parse(data):
        pass

    def log(self, data, addr):
        logger = logging.getLogger("raw.rdh")
        for i, dw in enumerate(unpack("<16L", data)):
            logger.info(f"{addr+4*i:012X} {dw:08X}    "
                        + self.describe_dword(i))

    def describe_dword(self, i):
        return ""