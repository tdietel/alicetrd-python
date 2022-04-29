import numpy as np
from struct import unpack

from functools import wraps
from collections import namedtuple
import logging

from rawdata.tfreader import RawDataHeader

from .rawlogging import AddLocationFilter
from .constants import eodmarker,eotmarker,magicmarker
from .base import BaseHeader, BaseParser, DumpParser
from .bitstruct import BitStruct, HexDump

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

					except AssertionError:
						continue

					if not isinstance(result, dict):
						break

					if 'readlist' in result:
						self.readlist.extend(result['readlist'])

					break

				else:
					logger.error(logflt.where 
						+ "NO MATCH - expected {expected}")
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

					except AssertionError as ex:
						continue

					if not isinstance(result, dict):
						break

					if 'readlist' in result:
						self.readlist.extend(result['readlist'])

					break

				else:
					logger.error(logflt.where
						+ f"NO MATCH - expected {[x.__name__ for x in expected]} found {dword:X}")
					# check_dword(dword)

					# skip everything until EOD
					self.readlist.extend([[find_eod_mcmhdr]])
					continue


			except IndexError:
				logger.error(logflt.where + "extra data after end of readlist")
				break

	def dump_readlist(self):
		for j,l in enumerate(self.readlist):
			print( [ f.__name__ for f in self.readlist[j] ] )


@BitStruct(  # each line corresponds to a 64-bit word
    version=8, cru=12, stop=4, ep=4, evtype=4, res0=32, # word0
   	e00=8, e01=8, e02=8, e03=8, e04=8, e05=8, e06=8, e07=8,
   	e08=8, e09=8, e10=8, e11=8, e12=8, e13=8, e14=8, res1=8,
	res2=64,
	s00=16, s01=16, s02=16, s03=16, 
	s04=16, s05=16, s06=16, s07=16,
   	s08=16, s09=16, s10=16, s11=16, 
	s12=16, s13=16, s14=16, res3=16)
class TrdHalfCruHeader(BaseHeader):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# build tuples with error flags and data size for each link
		self.errflags = tuple(getattr(self,f"e{i:02}") for i in range(15))
		self.datasize = tuple(32*getattr(self,f"s{i:02}") for i in range(15))

		# calculate the expected offset for each link
		base = self._addr - RawDataHeader.header_size # RDH base address
		pagesize = 0x2000 - RawDataHeader.header_size # payload per RDH page

		rawoffset = self.header_size # link data starts after HCRU header
		offsets = list()
		for i, sz in enumerate(self.datasize):
			npages = rawoffset // pagesize
			# expect = base + 0x2000*npages + RawDataHeader.header_size + rawoffset%pagesize
			offsets.append(
				base # RDH base address
				+ 0x2000*npages # size of complete pages (header+payload)
				+ RawDataHeader.header_size # RDH of incomplete page
				+ rawoffset%pagesize # payload of incomplete page
			)
			# logger.info(f"Link {i} expected to start at 0x{expect:06x}")
			# HexDump.add_marker(expect, "HCRU: Link{02i}")
			rawoffset += sz

		self.offset = tuple(offsets)
		for i, off in enumerate(self.offset):
			logger.info(f"Link {i} expected to start at 0x{off:06x}")

		for i, desc in enumerate(self._hexdump_desc):
			self._hexdump_desc[i] = f"HCRU[{i//4}.{i%4}]  {desc}"
		# logger.info(self._hexdump_desc)


# class TrdHalfCruHeader(BaseHeader):

# 	header_size = 0x40 # 256 bits = 64 bytes

# 	""" TRD CRU Header"""
# 	def parse(self, data):
# 		fields = unpack("<L4x15B9x15H2x", data)
# 		# self.parse_hw0(fields[0])
# 		self.errflags = tuple(fields[1:16])
# 		self.datasize = tuple(fields[16:31])

# 		self.version = 42
# 		self.hdrsize = 99

# 	@describe("tttt : eeee : ssss : cccc : cccc : cccc : vvvv : vvvv")
# 	# TODO @assignattr(self, version="v", stopbit="s", bc="c", endpoint="e", evtype="t")
# 	def parse_hw0(self, data, fields):
# 		self.version = fields.v
# 		self.stopbit = fields.s
# 		self.bc = fields.c
# 		self.endpoint = fields.e
# 		self.evtype = t

# 	def describe_dword(self, i):
# 		dwi = f"HCRU[{i//4}.{i%2}]  "

# 		if i==0:
# 			return dwi + "bla"
# 		elif i==1:
# 			return dwi + "bla"
# 		elif i<=4:
# 			return dwi + " ".join(
# 				f"{j:x}:{self.errflags[j]:x}" for j in range(4*i-5,4*i-9,-1))
# 		elif i==5:
# 			return dwi + "    " + " ".join(
# 				f"{j:x}:{self.errflags[j]:x}" for j in range(4*i-6, 4*i-9, -1))
# 		elif i<8:
# 			return dwi
# 		elif i <= 14:
# 			return dwi + " ".join(
# 				f"{j:x}:{self.datasize[j]:04X}({self.errflags[j]:x})" 
# 				for j in range(2*i-15, 2*i-17, -1))
# 		else:
# 			return dwi

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

		hdump = HexDump()
		hdump._markers[0x00000000BB88] = ["here"]

		maxpos = stream.tell() + size
		while stream.tell() < maxpos:

			avail_bytes = maxpos - stream.tell()
			if avail_bytes == 32:
				padding = stream.read(32)
				if padding != '\xee'*32:
					pass
					# raise ValueError(f"invalid padding word: {padding} {len(padding)}")
				continue

			if self.hcruheader is None:
				if avail_bytes < TrdHalfCruHeader.header_size:
					hdump.fromfile(stream, avail_bytes)
				
					raise ValueError("Insufficient data for Half-CRU header")

				self.hcruheader = TrdHalfCruHeader.read(stream)
				self.link = None
				self.unread = None

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
				logger.info(f"{maxpos - stream.tell()} padding bytes")
				hdump.fromfile(stream, maxpos - stream.tell())
				# assert(False)
				# stream.seek(maxpos-1)
			


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

