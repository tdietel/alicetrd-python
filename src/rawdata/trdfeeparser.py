import numpy as np
import math
from struct import unpack
#import pylab as pl

from functools import wraps
# import functools
from collections import namedtuple
# from typing import NamedTuple
# from pprint import pprint
import logging

from .rawlogging import AddLocationFilter
from .constants import eodmarker,eotmarker,magicmarker
from .base import BaseHeader, BaseParser, DumpParser

logger = logging.getLogger(__name__)
logflt = AddLocationFilter()
logger.addFilter(logflt)


class decode:
	"""Decorator decoder class for 32-bit data words from TRAPconfig

	The constructor takes a description of a TRAP data word in the format
	used in the TRAP User Manual. It can then be used to decorate functions
	to help with the parsing of data words according to	this format. If the
	parsing succeeds, the function is called with an additional argument that
	contains the extracted fields as a namedtuple. An assertion error is
	raised dif the parsing fails."""

	def __init__(self, pattern):

		fieldinfo = dict()

		# calculate bitmask and required shift for every character
		for i,x in enumerate(x for x in pattern if x not in ": "):
			p = 31-i # bit position
			if x not in fieldinfo:
				fieldinfo[x] = dict(mask=1<<p, shift=p)
			else:
				fieldinfo[x]['mask'] |= 1<<p
				fieldinfo[x]['shift'] = p

		# remember bits marked as '0' or '1' for validation of the dword
		zero_mask = fieldinfo.pop('0')['mask'] if '0' in fieldinfo else 0
		one_mask  = fieldinfo.pop('1')['mask'] if '1' in fieldinfo else 0
		self.validate_value = one_mask
		self.validate_mask = zero_mask | one_mask

		# create a named tuple based on the field names
		self.dtype = namedtuple("decoded_fields", fieldinfo.keys() )

		# flatten the fields info to a tuple for faster retrieval
		# the field name is not stritcly necessary, but might help to debug
		self.fields = tuple(
		  (k,fieldinfo[k]['mask'],fieldinfo[k]['shift']) for k in fieldinfo )


	def __call__(self,func):

		@wraps(func)
		def wrapper(ctx, dword):
			assert( (dword & self.validate_mask) == self.validate_value)
			return func(ctx,dword,self.decode(dword))

		return wrapper

	def decode(self,dword):
		return self.dtype(*[ (dword & x[1]) >> x[2] for x in self.fields ])

class describe:
	"""Decorator to generate messages about dwords

	Probably this function is overkill and should be replaced with a single
	log statement in the decorated functions."""

	def __init__(self, fmt):
		self.format = fmt
		self.marker = ('#', '#', '|', ':')

	def __call__(self,func):

		@wraps(func)
		def wrapper(ctx,dword,fields=None):

			if fields is None:
				retval = func(ctx,dword)
				fielddata = {}

			else:
				retval = func(ctx,dword,fields)
				fielddata = fields._asdict()

			if retval is True or retval is None:
				retval = dict()

			if 'description' not in retval:
				# if (dword & 0x3) == 2:
				# mrk = ('#', '#', '|', ':')[dword&0x3]
				logger.info(self.format.format(
					dword=dword, mark=self.marker[dword & 0x3],
					**fielddata, ctx=ctx))
				# retval['description'] = msg

			return retval

		return wrapper



ParsingContext = namedtuple('ParsingContext', [
  'major', 'minor', 'nhw', 'sm', 'stack', 'layer', 'side', #from HC0
  'ntb', 'bc_counter', 'pre_counter', 'pre_phase', # from HC1
  'SIDE', 'HC', 'VER', 'det', ## derived from HCx
  'rob', 'mcm', ## from MCM header
  'store_digits', ## links to helper functions/functors
  'event', ## event number
])

# ------------------------------------------------------------------------
# Generic dwords


@describe("SKP ... skip parsing ...")
def skip_until_eod(ctx, dword):
	assert(dword != eodmarker)
	return dict(readlist=[[parse_eod, skip_until_eod]])

@describe("SKP {mark} ... trying to find: eod | mcmhdr - {dword:X}")
def find_eod_mcmhdr(ctx, dword):

	if dword == eodmarker:
		return parse_eod(ctx,dword)

	elif (dword & 0x8000000F) == 0x8000000C:
		return parse_mcmhdr(ctx,dword)

	# assert(dword != eodmarker)
	return dict(readlist=[[find_eod_mcmhdr]])


@describe("TRK tracklet")
def parse_tracklet(state, dword):
	assert(dword != eotmarker)
	return dict(readlist=[[parse_tracklet, parse_eot]])


@describe("EOT")
def parse_eot(ctx, dword):
	assert(dword == eotmarker)
	return dict(readlist=[[parse_eot, parse_hc0]])

@describe("EOD")
def parse_eod(ctx, dword):
	assert(dword == eodmarker)
	return dict(readlist=[[parse_eod]])

# ------------------------------------------------------------------------
# Half-chamber headers

@decode("xmmm : mmmm : nnnn : nnnq : qqss : sssp : ppcc : ci01")
@describe("HC0 {ctx.HC} ver=0x{m:X}.{n:X} nw={q}")
def parse_hc0(ctx, dword, fields):

	ctx.major = fields.m  # (dword >> 24) & 0x7f
	ctx.minor = fields.n  # (dword >> 17) & 0x7f
	ctx.nhw   = fields.q  # (dword >> 14) & 0x7
	ctx.sm    = fields.s  # (dword >>  9) & 0x7
	ctx.layer = fields.p  # (dword >>  6) & 0x1f
	ctx.stack = fields.c  # (dword >>  3) & 0x3
	ctx.side  = fields.i  # (dword >>  2) & 0x1

	ctx.det = 18*ctx.sm + 6*ctx.stack + ctx.layer

	# An alternative to update the context - which one is easier to read?
	# (ctx.major,ctx.minor,ctx.nhw,ctx.sm,ctx.layer,ctx.stack,ctx.side) = fields

	# Data corruption seen with configs around svn r5930 -> no major/minor info
	# This is a crude fix, and the underlying problem should be solved ASAP
	if ctx.major==0 and ctx.minor==0 and ctx.nhw==0:
		ctx.major = 0x20 # ZS
		ctx.minor = 0
		ctx.nhw   = 2


	# set an abbreviation for further log messages
	side = 'A' if fields.i==0 else 'B'
	ctx.HC   = f"{fields.s:02}_{fields.c}_{fields.p}{side}"

	readlist = list()
	for i in range(ctx.nhw):
		# check additional HC header in with HC1 last, because HC2 and HC3
		# appear like HC1 with the (invalid) phase >= 12. This order avoids
		# this ambiguity.
		readlist.append([parse_hc3, parse_hc2, parse_hc1])

	readlist.append([parse_mcmhdr])
	return dict(readlist=readlist)

@decode("tttt : ttbb : bbbb : bbbb : bbbb : bbpp : pphh : hh01")
@describe("HC1 tb={t} bc={b} ptrg={p} phase={h}")
def parse_hc1(ctx, dword, fields):

	ctx.ntb         = fields.t  # (dword >> 26) & 0x3f
	ctx.bc_counter  = fields.b  # (dword >> 10) & 0xffff
	ctx.pre_counter = fields.p  # (dword >>  6) & 0xF
	ctx.pre_phase   = fields.h  # (dword >>  2) & 0xF


@decode("pgtc : nbaa : aaaa : xxxx : xxxx : xxxx : xx11 : 0001")
@describe("HC2 - filter settings")
def parse_hc2(ctx, dword, fields):
	pass

@decode("ssss : ssss : ssss : saaa : aaaa : aaaa : aa11 : 0101")
@describe("HC3 - svn version {s} {a}")
def parse_hc3(ctx, dword, fields):
	pass

# ------------------------------------------------------------------------
# MCM headers

@decode("1rrr : mmmm : eeee : eeee : eeee : eeee : eeee : 1100")
@describe("MCM {r}:{m:02} event {e}")
def parse_mcmhdr(ctx, dword, fields):

	ctx.rob = fields.r
	ctx.mcm = fields.m
	if ctx.major & 0x20:   # Zero suppression
		return dict(readlist=[[parse_adcmask]])

	else:  # No ZS -> read 21 channels, then expect next MCM header or EOD
		adcdata = np.zeros(ctx.ntb, dtype=np.uint16)
		readlist = list()
		for ch in range(21):
			for tb in range(0, ctx.ntb, 3):
				readlist.append([parse_adcdata(channel=ch, timebin=tb, adcdata=adcdata)])

		readlist.append([parse_mcmhdr, parse_eod])
		return dict(readlist=readlist)

@decode("nncc : cccm : mmmm : mmmm : mmmm : mmmm : mmmm : 1100")
def parse_adcmask(ctx, dword, fields):
	desc = "MSK "
	count = 0
	readlist = list()

	adcdata = np.zeros(ctx.ntb, dtype=np.uint16)

	for ch in range(21):
		if ch in [9,19]:
			desc += " "

		if fields.m & (1<<ch):
			count += 1
			desc += str(ch%10)
			for tb in range ( 0, ctx.ntb , 3 ):
				readlist.append([parse_adcdata(channel=ch, timebin=tb, adcdata=adcdata)])
		else:
			desc += "."


	desc += f"  ({~fields.c & 0x1F} channels)"
	readlist.append([parse_mcmhdr, parse_eod])
	assert( count == (~fields.c & 0x1F) )

	logger.info(desc)
	return dict(readlist=readlist)
	# return dict(description=desc, readlist=readlist)


# ------------------------------------------------------------------------
# Raw data
class parse_adcdata:
	"""ADC data parser

	To parse ADC data, we need to know the channel number and the timebins
	in this dword. I don't think this data should be kept in the context.
	The parser for the MCM header / adcmask therefore stores it in the parser
	for the ADC data word. This parser therefore has to be a callable object.
	"""

	def __init__(self, channel, timebin, adcdata=None):
		self.channel = channel
		self.timebin = timebin
		self.adcdata = adcdata
		self.__name__ = "parse_adcdata"

	# @decode("xxxx:xxxx:xxyy:yyyy:yyyy:zzzz:zzzz:zzff")
	def __call__(self, ctx, dword):
		x = (dword & 0xFFC00000) >> 22
		y = (dword & 0x003FF000) >> 12
		z = (dword & 0x00000FFC) >>  2
		f = (dword & 0x00000003) >>  0

		msg = f"ADC {('#', '#', '|', ':')[dword&3]} "
		msg += f"ch {self.channel:2} " if self.timebin==0 else " "*6
		msg += f"tb {self.timebin:2} (f={f})   {x:4}  {y:4}  {z:4}"

		logger.info(msg)

		# assert( f == 2 if self.channel%2 else 3)

		if self.adcdata is not None and ctx.store_digits is not None:
			# store the ADC values in the reserved array
			for i,adc in enumerate((x,y,z)):
				if self.timebin+i < len(self.adcdata):
					self.adcdata[self.timebin+i] = adc

			# if this is the last dword for this channel -> store the digit
			if self.timebin+3 >= len(self.adcdata):
				ctx.store_digits(ctx.event, ctx.det, ctx.rob, ctx.mcm,
				                 self.channel, self.adcdata)

		return dict()


# ------------------------------------------------------------------------
class TrdFeeParser:

	# end_of_tracklet = 0x10001000
	# end_of_data     = 0x00000000


	#Defining the initial variables for class
	def __init__(self, store_digits = None):
		self.ctx = ParsingContext
		self.ctx.event = 0
		self.ctx.store_digits = store_digits
		self.readlist = None

	def next_event(self):
		self.ctx.event += 1

	def process(self,linkdata, linkpos=-1):
		'''Initialize parsing context and process data from one optical link.

		Parameter: linkdata = iterable list of uint32 data words
        '''

		self.ctx.current_linkpos = linkpos

		self.readlist = [ list([parse_tracklet, parse_eot]) ]
		self.process_linkdata(linkdata)


	def process_linkdata(self, linkdata):

		for dword in linkdata:

			self.ctx.current_linkpos += 1
			self.ctx.current_dword = dword

			logflt.where = f"{self.ctx.current_linkpos:12x} {dword:08x}  "

			# Debugging:
			# self.dump_readlist()

			try:
				# for fct in self.readlist[i]:
				expected = self.readlist.pop(0)
				for fct in expected:

					# logger.info(fct)

					# The function can raise an AssertionError to signal that
					# it does not understand the dword
					try:
						 result = fct(self.ctx,dword)

					except AssertionError as ex:
						continue

					if not isinstance(result, dict):
						break

					if 'readlist' in result:
						self.readlist.extend(result['readlist'])

					# the function handled the dword -> we are done
					# if 'description' in result:
					# 	print(f"{ctx.current_dword:06x} {dword:08x}  ", end="")
					# 	print(result['description'])

					break

				else:
					logger.error(logflt.where 
						+ "NO MATCH - expected {expected} found {dword}")
					# check_dword(dword)

					# skip everything until EOD
					self.readlist.extend([[parse_eod, skip_until_eod]])
					continue


			except IndexError:
				logger.error(logflt.where + "extra data after end of readlist")
				break

	def read(self, stream, size):

		self.ctx.current_linkpos = -1

		if self.readlist is None:
			self.readlist = [ list([parse_tracklet, parse_eot]) ]

		# logger.info(f"{self.readlist}")

		maxpos = stream.tell() + size
		while stream.tell() < maxpos:

			self.ctx.current_linkpos = stream.tell()
			dword = unpack("<L", stream.read(4))[0]
			self.ctx.current_dword = dword

			logflt.where = f"{self.ctx.current_linkpos:06x} {dword:08x}  "

			# Debugging:
			# self.dump_readlist()

			try:
				expected = self.readlist.pop(0)
				# for fct in self.readlist[i]:
				for fct in expected:

					# The function can raise an AssertionError to signal that
					# it does not understand the dword
					try:
						 result = fct(self.ctx,dword)
						#  logger.info(f"{fct.__name__}")

					except AssertionError as ex:
						continue

					if not isinstance(result, dict):
						break

					if 'readlist' in result:
						self.readlist.extend(result['readlist'])

					# the function handled the dword -> we are done
					# if 'description' in result:
					# 	print(f"{ctx.current_dword:06x} {dword:08x}  ", end="")
					# 	print(result['description'])

					break

				else:
					logger.error(logflt.where
						+ f"NO MATCH - expected {[x.__name__ for x in expected]} found {dword:X}")
					# check_dword(dword)
					# exit(1)

					# skip everything until EOD
					self.readlist.extend([[find_eod_mcmhdr]])
					continue


			except IndexError:
				logger.error(logflt.where + "extra data after end of readlist")
				break

	def dump_readlist(self):
		for j,l in enumerate(self.readlist):
			print( [ f.__name__ for f in self.readlist[j] ] )


class TrdHalfCruHeader(BaseHeader):

	header_size = 0x40 # 256 bits = 64 bytes

	""" TRD CRU Header"""
	def parse(self, data):
		fields = unpack(">L4x15B9x15H2x", data)
		# self.parse_hw0(fields[0])
		self.errflags = tuple(fields[1:16])
		self.datasize = tuple(fields[16:31])

		self.version = 42
		self.hdrsize = 99

	@describe("tttt : eeee : ssss : cccc : cccc : cccc : vvvv : vvvv")
	def parse_hw0(self, data, fields):
		self.version = fields.v
		self.stopbit = fields.s
		self.bc = fields.c
		self.endpoint = fields.e
		self.evtype = t

	def describe_dword(self, i):
		dwi = f"HCRU[{i//4}.{i%2}]  "

		if i==0:
			return dwi + "bla"
		elif i==1:
			return dwi + "bla"
		elif i<=4:
			return dwi + " ".join(
				f"{j:x}:{self.errflags[j]:x}" for j in range(4*i-5,4*i-9,-1))
		elif i==5:
			return dwi + "    " + " ".join(
				f"{j:x}:{self.errflags[j]:x}" for j in range(4*i-6, 4*i-9, -1))
		elif i<8:
			return dwi
		elif i <= 14:
			return dwi + " ".join(
				f"{j:x}:{self.datasize[j]:04X}({self.errflags[j]:x})" 
				for j in range(2*i-15, 2*i-17, -1))
		else:
			return dwi
		# dword_desc = list(("HCRU ", " - reserved -"))

		# for i in range(4):
		# 	dword_desc.append(" ".join(f"{4*i+j}:") for j in range(4))
		
		# for i in range(10):
			


		# 	dwor"3:{errflags[3]:X} 3:{errflags[3]:X} 3:{errflags[3]:X} 3:{errflags[3]:X} ", "errflags",
		# 	"errflags", "errflags+res", 
		# 	"res", "res",
		# 	"1:{datasize[1]:X} 0:{datasize[0]:X}",
		# 	"3:{datasize[3]:X} 2:{datasize[2]:X}",
		# 	"5:{datasize[5]:X} 4:{datasize[4]:X}",
		# 	"7:{datasize[7]:X} 6:{datasize[6]:X}",
		# 	"9:{datasize[9]:X} 8:{datasize[8]:X}",
		# 	"b:{datasize[11]:X} a:{datasize[10]:X}",
		# 	"d:{datasize[13]:X} c:{datasize[12]:X}",
		# 	"   - reserved -   e:{datasize[14]:X}",
		# 	"", "",
		# 	"", "",
		# 	"", ""))
		# 	# "", "", "", "", "", "", "", "",
		# 	# "", "", "", "", "", "", "", ""))
		# return dwi + dword_desc[i].format(**vars(self))


class TrdCruParser(BaseParser):
	def __init__(self):
		# self.feeparser = DumpParser(logging.getLogger("raw.trd.fee"))
		self.feeparser = TrdFeeParser() #(logging.getLogger("raw.trd.fee"))

		# We might have to resume reading data from the previous RDH page.
		# All necessary data to resume at the correct position is therefore
		# stored in instance instead of local variables.
		self.hcruheader = None
		self.link = None
		self.unread = None # bytes remaining to be parse in current link

	def read(self, stream, size):

		# logger.info(f"HCRU stream called for pos {stream.tell()} for {size} bytes")

		maxpos = stream.tell() + size
		while stream.tell() < maxpos:

			avail_bytes = maxpos - stream.tell()
			if avail_bytes == 32:
				padding = stream.read(32)
				# logger.info(f"padding: {padding} expexted{'\\xee'*32} ")
				if padding != '\xee'*32:
					pass
					# raise ValueError(f"invalid padding word: {padding} {len(padding)}")
				continue

			# logger.info(f"Read HCRU header at f{stream.tell()}, maxpos = {maxpos}")

			if self.hcruheader is None:
				if avail_bytes < TrdHalfCruHeader.header_size:
					raise ValueError("Insufficient data for Half-CRU header")

				self.hcruheader = TrdHalfCruHeader.read(stream)
				self.link = None
				self.unread = None
				logger.info("Read HCRU header")

			if self.link is None:
				self.link = 0
				self.unread = None

			if self.unread is None:
				self.unread = self.hcruheader.datasize[self.link]

			if self.unread > 0:
				avail = maxpos - stream.tell()
				readsize = self.unread if self.unread < avail else avail
				self.feeparser.read(stream,readsize)
				self.unread -= readsize

			if self.unread == 0:
				if self.link < 14:
					self.link += 1
					self.unread = None
				else:
					self.hcruheader = None
					self.link = None
					self.unread = None
				
			if self.hcruheader is None:
				logger.info("{maxpos - stream.tell()} padding bytes")
				stream.seek(maxpos-1)
			


				# self.feeparser.read

            # payload_size = rdh.datasize - TrdHalfCruHeader.header_size
            # if size < processed_bytes + payload_size:
            #     raise DataError("Insufficient data")
            # stream.seek(rdh.payload_size, 1)

	def parse(self, data, addr):
		hdrsize = 0x80
		offset = 0
		# while offset < len(data):
        # 	# read the RDH
		# 	if self.hcruheader is None:
		# 		self.hcruheader = TrdHalfCruHeader(data[offset:offset+hdrsize], addr)
		# 		offset += hdrsize

		# 	if self.link is None:
		# 		self.link = 0:

		# 		for self.link in range(15):
		# 			flags = self.hcruheader.errflags[i]
		# 			size = self.hcruheader.datasize[i]

		# 			if size == 0:
		# 				next

		# 			self.feeparser.parse(data[offset:offset+size], addr+offset)

		# 		offset += size

		# 	self.link = None
        #     # move to next RDH+data
        #     data = data[rdh.datasize:]
        #     addr += rdh.datasize



def check_dword(dword):

	ctx = dict()

	parsers = [ parse_tracklet, parse_eot, parse_eod,
	  parse_hc0, parse_hc1, parse_hc2, parse_hc3,
	  parse_mcmhdr, parse_adcmask, parse_adcdata(-1,-1) ]

	for p in parsers:
		try:
			p(ctx,dword)
		except AssertionError:
			continue

		# log.debug("Match:", p.__name__)
