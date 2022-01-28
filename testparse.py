#!/usr/bin/env python3

import numpy as np
import sys
from rawdata import LinkParser
import rawdata
import logging

logging.basicConfig(level=logging.INFO)
rawdata.check_dword(int(sys.argv[1],0))



# with open("ev00000000_eq4097.npy", "rb") as f:
#     payload = np.load(f)
#
# # print(payload)
# lp = LinkParser()
#
# lp.process(payload)
