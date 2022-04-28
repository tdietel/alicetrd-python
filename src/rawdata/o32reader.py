
import numpy
import re
import subprocess
from datetime import datetime
from typing import NamedTuple
#from collections.abc import Iterable

class event_t(NamedTuple):
    timestamp: datetime
    subevents: tuple

class subevent_t(NamedTuple):
    # timestamp: datetime
    equipment_type: int
    equipment_id: int
    #payload: Iterable[int]
    payload: numpy.ndarray


class o32reader:
    """Reader class for files in the .o32 format.

    The constructor takes a file name as input. If the if filename ends in
    '.o32' it is read as a normal text file. If it ends in '.o32.bz2' it is
    assumed to be bzip2-compressed, and it is decompressed with bzcat before
    parsing.

    The class can be used as an iterator over events in the file.

    o32 is a simple, text-based format for TRD data that was inspired by older
    formats used during the early commissioning. It contains the detector data
    as 32-bit hexadecimal data words with one word per line. Event headers are
    marked with a single hash mark at the beginning of the line (`/^## /`), and
    sub-event headers for data from a single optical link or half-chamber with
    a double hash mark (`/^## /`). Event and sub-event headers contain
    clear-text data fields."""


    #Initial state variables:
    def __init__(self,file_name):

        self.filename = file_name
        self.line_number=0
        self.linebuf = None

    def __iter__(self):

        # I don't remember why I'm opening the file in the iterator and not in
        # the constructor. Maybe to ensure that you can read the file several
        # times with the same o32reader, although I'm not sure this is needed.

        if self.filename.endswith('.o32'):
            self.infile=open(self.filename, 'r')

        elif self.filename.endswith('.o32.bz2'):
            self.proc = subprocess.Popen(["bzcat", self.filename],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            self.infile = self.proc.stdout

        else:
            raise ValueError(f"invalid file extension of input file {self.filename}")

        return self

    #Create dictionary
    def __next__(self):

        header = self.read_event_header()

        subevents = tuple([self.read_subevent() for i in range(header['data blocks'])])

        return event_t(header['time stamp'], subevents)

    def process(self, skip_events=0):
        """This method will handle the reading process.
        
        It is meant as a replacement for the lecacy iterator interface."""

        # Loop through events and subevents
        for evno, event in enumerate(self):
            if evno < skip_events:
                continue

            for subevent in event.subevents:
                self.trd_fee_parser.process(subevent.payload)

    def set_trd_fee_parser(self, p):
        self.trd_fee_parser = p


    def read_event_header(self):

        hdr = dict()

        line = self.read_line()
        if not line:
            raise StopIteration

        if line != '# EVENT':
            print(line)
            raise Exception('file format', 'invalid file format')

        # Extract header version number (should always be 1.0)
        m = re.search('# *format version: *(.*)', self.read_line())
        hdr['version'] = m.group(1)

        # The header version determines the names and order of the fields
        # in the header
        if hdr['version'] == '1.0':
            hdrfields = ('time stamp', 'data blocks')

        else:
            raise Exception('file format', 'unknown format version')


        for h in hdrfields:

            if h == 'time stamp':
                m = re.search('# *time stamp: *(.*)', self.read_line())

                hdr['time stamp'] = datetime.strptime( m.group(1),
                                                           '%Y-%m-%dT%H:%M:%S.%f')

            elif h == 'data blocks':
                m = re.search('# *data blocks: *(.*)', self.read_line())
                hdr['data blocks'] = int(m.group(1))

            else:
                raise Exception('FATAL', 'unknown header field')

        return hdr


    def read_subevent(self):

        subevent = dict()

        if self.read_line() != '## DATA SEGMENT':
            raise Exception('file format', 'invalid file format')

        m = re.match('## *sfp: *(.*)', self.read_line())
        equipment_type = 0x10
        equipment_id = int(m.group(1))

        m = re.search('## *size: *(.*)', self.read_line())
        payload_size = int(m.group(1))

        payload = numpy.zeros(payload_size, dtype=numpy.uint32)
        for i in range(payload_size):
            payload[i] = numpy.uint32(int(self.read_line(),0))

        return subevent_t(equipment_type, equipment_id, payload)



    def read_line(self):

        # This function seems to support partial reading of lines, although
        # I don't remember why and how.
        if self.linebuf is not None:
            tmp = self.linebuf
            self.linebuf = None
            return tmp

        # The actual reader code
        self.line_number+=1
        self.lastline = self.infile.readline().rstrip()

        # subprocess pipes return bytes, need to decode to string
        if isinstance(self.lastline, bytes):
            self.lastline = self.lastline.decode()
        return self.lastline


