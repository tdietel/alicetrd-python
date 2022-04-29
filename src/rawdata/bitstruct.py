#!/usr/bin/env python3

from collections import namedtuple, Counter, OrderedDict
import itertools
import struct
import logging

class BitStructWord:
    """A bit struct that can be represented as a single 8, 16 or 32 bit word"""

    _partinfo_t = namedtuple("fieldinfo_t", ['name', 'size', 'offset'])
    _extractinfo_t = namedtuple("extracinfo_t", ["shift", "mask"])
    _fmtchar_map = { 8:"B", 16: "H", 32: "L" }

    def __init__(self):
        self._partinfo = list()
        self._size = 0

    def add_field(self, name, size):
        self._partinfo.append(self._partinfo_t(name, size, self._size))
        self._size += size

        if self._size in self._fmtchar_map:
            self.parseable = True
            self.fmtchar = self._fmtchar_map[self._size]
            self.keys = tuple(p.name for p in self._partinfo)
            self._extractinfo = tuple(
                self._extractinfo_t(self._size-p.offset-p.size, (1<<p.size)-1)
                for p in self._partinfo)

        else:
            self.fmtchar = None
            self.parseable = False

    def unpack(self, word):
        return tuple( (word>>e.shift) & e.mask for e in self._extractinfo )

    def decode(self, word):
        for p,v in zip(self._partinfo, self.unpack(word)):
            shift = self._size - p.offset - p.size
            mask = (1 << p.size) - 1
            print(f"{p.name}:  0x{word:X} -> mask=0x{mask<<shift:X} -> 0x{v:X}")

    # def hexdump(self,word):
    #     for p, v in zip(self._partinfo, self.unpack(word)):

class HexDump:

    _markers = dict()

    def __init__(self, bitwidth=32):
        self.logger = logging.getLogger("hexdump")
        self.fmtchar = {32: "I"}[bitwidth]
        self.introfmt = {
            32: "{addr:012X} {word[0]:08X}    "
        }[bitwidth]
        self.bitwidth = 32

    def fromfile(self, stream, nbytes):
        addr = stream.tell()
        data = stream.read(nbytes)
        self(data,addr)

    @classmethod
    def add_marker(cls, addr, message):
        if addr in cls._markers:
            cls._markers[addr].append(message)
        else:
            cls._markers[addr] = [message]

    def __call__(self, data, addr):
        for i,words in enumerate(struct.iter_unpack(self.fmtchar,data)):
            if addr+4*i in self._markers:
                for m in self._markers[addr+4*i]:
                    self.logger.info(f"MARK: {m}")

            intro = self.introfmt.format(addr=addr+4*i, word=words)
            # desc = x._hexdump_desc[i].format(**vars(x))
            self.logger.info(intro)


def hexdump(x, bitwidth=32):
    fmtchar = {32: "I"}[bitwidth]
    introfmt = {
        32: "{addr:012X} {word[0]:08X}    "
    }[bitwidth]

    addr = x._addr if x._addr is not None else 0

    logger = logging.getLogger("hexdump").info

    for i,words in enumerate(struct.iter_unpack(fmtchar,x._data)):
        intro = introfmt.format(addr=addr+4*i, word=words)
        desc = x._hexdump_desc[i].format(**vars(x))
        logger(intro+desc)

def auto_hexdump_str(fieldinfo):
    
    # print(bitgroups(fieldinfo,32))
    fmts = list()
    for dword in bitgroups(fieldinfo, 32):
        fmt = " ".join(f"{k}=0x{{{k}:0{v//4}X}}" for k,v in dword.items())
        fmts.append(fmt)
        # print(fmt)

    return(fmts)

def bitgroups(fieldinfo, bitwidth=32):

    # temporary list that holds the variables for all bits
    bits = list()

    # for each bit, determine which variable it belongs to
    for name,size in fieldinfo.items():
        bits.extend(name for i in range(size))

    # group the bits in words of size bitwidth
    groups = list()
    for i in range(0, len(bits), bitwidth):
        cnt = OrderedDict.fromkeys(bits[i:i+bitwidth], 0)
        for k in bits[i:i+bitwidth]:
            cnt[k] += 1
        groups.append(cnt)

    return groups



class BitStruct:
    "A struct with fields that can be less than a byte wide"

    _fmtchar_map = {8: "B", 16: "H", 32: "L", 64: "Q"}

    def __init__(self, **fieldinfo):

        self._fmt = "<"
        self._fmtdecoder = list()
        self._keys = list()

        bitstruct = None
        for name, size in fieldinfo.items():
            if bitstruct is None and size in self._fmtchar_map:
                # we can use a simple struct.unpack() to extract this field
                self._fmt += self._fmtchar_map[size]
                self._fmtdecoder.append(lambda x: [x])
                self._keys.append(name)
            else:
                # either we have a field that is not a multiple of 8 bits wide,
                # or we are already in a part that is not 8-bit aligned

                # we need to prepare a parser for this part of the field
                if bitstruct is None:
                    bitstruct = BitStructWord()

                # tell the parser about this field
                bitstruct.add_field(name, size)
                self._keys.append(name)

                # if we can parse the fields up to here, let's do it
                if bitstruct.parseable:
                    self._fmt += bitstruct.fmtchar
                    self._fmtdecoder.append(bitstruct.unpack)
                    bitstruct = None

        # print(self._fmt, struct.calcsize(self._fmt))

        self._fmthexdesc = auto_hexdump_str(fieldinfo)


    def __call__(self, klass):
        """Decorator to teach classes to parse a BitStruct"""
        # _orig_init = klass.__init__

        # def _new_init(klass, data, addr=None):
        #     # klass._data = data
        #     # klass._addr = addr
        #     klass._hexdump_desc = None
        #     for k, v in zip(self.keys, self.unpack(data)):
        #         setattr(klass,k,v)
        #     # klass._bitstruct_keys = self.keys
        #     _orig_init(klass)

        #     if klass._hexdump_desc is None:
        #         klass._hexdump_desc = self._fmthexdesc

        # klass.__init__ = _new_init
        klass.unpack = self.unpack
        klass.keys = self.keys
        klass.header_size = struct.calcsize(self._fmt)

        try:
            klass._hexdump_desc
        except AttributeError:
            klass._hexdump_desc = self._fmthexdesc

        # def decode(klass):
            # for k in klass._bitstruct_keys:
                # print(f"{k} = {getattr(klass,k)}")
        # klass.decode = decode
        klass.hexdump = hexdump

        return klass

    def unpack(self, data):
        return tuple( itertools.chain.from_iterable(
            decode(value)
            for decode, value 
            in zip(self._fmtdecoder, struct.unpack(self._fmt, data))) )

    def keys(self):
        return self._keys


    # def decode(self,data):
    #     fmtdata = struct.unpack(self._fmt, data)
    #     for k,v in zip(self._fmtinfo, fmtdata):
    #         if isinstance(k,str):
    #             print(k,v)
    #         elif isinstance(k,BitStructWord):
    #             print(v)
    #             k.decode(v)




if __name__ == "__main__":

    # RDH_header = BitStruct(
    #     version=8, hdrsize=8, fee=16, prio=8, src=8, r0=16,
    #     offset=16, datasize=16,
    #     link=8, count=8, cru=12, ep=4)

    rdhdata = (b'\x06\x40\x00\x00\x00\x04\x00\x00'
               b'\x60\x00\x60\x00\x0f\xd5\x37\x02'
               b'\x00\x00\x00\x00\x11\x36\x0c\x00'
               b'\x01\x00\x00\x03\x04\x00\x00\x02'
               b'\x03\x40\x00\x00\x00\x00\x00\x00'
               b'\x00\x00\x00\x00\x00\x00\x00\x00'
               b'\x00\x00\x00\x00\x00\x00\x00\x00'
               b'\x00\x00\x00\x00\x00\x00\x00\x00')

    
    @BitStruct(
        version=8, hdrsize=8, fee=16, # 1st 32-bit dword
        prio=8, src=8, r0=16, # 2nd dword
        offset=16, datasize=16, # 3rd dword
        link=8, count=8, cru=12, ep=4) # 4th dword
    class rdh_t:

    
        # pass
        def __init__(self):
            print("rdh c'tor")
            
            self._hexdump_desc = [
                "RDHv{version} fee={fee}",
                "pri={prio} src={src}",
                "size=0x{datasize:04X} next=0x{offset:04X}",
                "link={link} count={count} cru={cru} ep={ep}"]
    
            



    rdh = rdh_t(rdhdata[0:16])
    # rdh.decode()
    rdh.hexdump()

            # for i in k:
                # print(i.name, (v&i.mask)>>shift)
    #     if k.startswith("reserved_"):
    #         next
    #     elif k=="cru_ep":
    #         # possible improvement: decode CRU and endpoint (EP)
    #         next
    #     else:
    #         print(k,v)


