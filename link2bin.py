#!/usr/bin/env python3

from pathlib import Path
from struct import pack,iter_unpack

# from pytrd import trdfeeparser
import rawdata

filename = "Link_0"
datadir = Path("/Users/tom/cernbox/data/2022-05-02/data_20220502")

data = b""

with open(datadir/filename) as f:
    for i,line in enumerate(f.readlines()):
        col = tuple(int(x,0) for x in line.split())

        if col[0] != col[1] or col[0] != col[2]:
            print (f"MISMATCH in line {i}: {col} { line.rstrip() }")

        # print (f"LINE {i}: {col} { line.rstrip() }")

        data = pack("H", col[0]) + data


data = data[2:]
print(len(data))
for i,dw in enumerate(iter_unpack("<I", data)):
    print(i,hex(dw[0]))


with open(datadir / (filename+".bin"), "wb" ) as f:
    f.write(data)

