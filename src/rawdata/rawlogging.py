
import logging
import struct
import sys

class StdoutHandler(logging.StreamHandler):

    def __init__(self):
        super().__init__(sys.stdout)
        self.setFormatter(ColorFormatter())
        # It would be nice to open a pager directly...
        # self.pipe = os.pipe2(O_NONBLOCK | O_CLOEXEC)
        # self.pager = subprocess.run(["less", "-r"], stdin=sys.stdout)
        # self.setStream(sys.stdout)

    def handleError(self, record):
        t, v, tb = sys.exc_info()
        if t == BrokenPipeError:
            sys.stderr.write("bla")
            raise SystemExit(0)

        else:
            super().handleError(record)


# https://alexandra-zaharia.github.io/posts/make-your-own-custom-color-formatter-with-python-logging/
class ColorFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://stackoverflow.com/a/56944256/3638629"""

    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, default_format=None, hexdump_format=None):
        super().__init__(default_format)

        if default_format is None:
            default_format = "%(color)s%(message)s"+self.reset
        if hexdump_format is None:
            hexdump_format = "%(hexaddr)012x  %(hexdata)08x    %(color)s%(shortname)-4s %(message)-45s"+self.reset

        self.formatter_hexdump = logging.Formatter(hexdump_format)
        self.formatter_default = logging.Formatter(default_format)

    def format(self, record):            
        record.shortname = record.name.split(".")[-1]
        if not hasattr(record, 'color'):
            record.color = ""

        if hasattr(record, 'hexdata'):
            return self.formatter_hexdump.format(record)
        else:
            return self.formatter_default.format(record)
        

class TermColorFilter(logging.Filter):

    text_styles = dict(
        blue = '\033[30m',
        green = '\033[32m',
        red='\x1b[38;5;196m',
        grey='\033[90m',
        yellow='\x1b[38;5;226m', 
        bold_blue='\033[1;34m',
        bold_green='\033[1;36m',
        bold_red='\x1b[31;1m',
        reset = '\x1b[0m',
        white_on_blue='\033[1;37;104m',
        grey_on_blue = '\033[0;37;104m'
    )

    def __init__(self, color):
        if color in self.text_styles:
            self.color = self.text_styles[color]
        else:
            self.color = color

    def filter(self, record):
        if not hasattr(record, 'color'):
            record.color = self.color
        return True


class AddLocationFilter(logging.Filter):
    """
    This is a filter which injects contextual information into the log.

    Rather than use actual contextual information, we just use random
    data in this demo.
    """

    def __init__(self, suppress=[]):
        self.addr = None
        self.dword = None
        self.suppress = suppress

    def set_location(self, addr, dword):
        self.addr = addr
        self.dword = dword

    dword_types = {
    #   'HC0': { "prefix": '\033[1;37;104m' }, # white on blue
    #   'HC1': { "prefix": '\033[0;37;104m' }, # grey on blue
      'HC2': { "prefix": '\033[0;37;104m' },
      'HC3': { "prefix": '\033[0;37;104m' },
      'MCM': { "prefix": '\033[1;34m' }, # bold blue
      'MSK': { "prefix": '\033[30m', "suppress": False },
      'ADC': { "prefix": '\033[90m', "suppress": False },
      'TRK': { "prefix": '\033[0;32m' },
      'EOT': { "prefix": '\033[0;34m' },
      'EOD': { "prefix": '\033[0;34m' },
      'SKP': { "prefix": '\033[0;31m' },
    }

    def set_verbosity(self, verbosity):

        if verbosity < 5:
            self.dword_types['ADC']['suppress'] = True

        if verbosity < 4:
            self.dword_types['MSK']['suppress'] = True
            self.dword_types['TRK']['suppress'] = True

        if verbosity < 3:
            self.dword_types['MCM']['suppress'] = True
            self.dword_types['EOT']['suppress'] = True
            self.dword_types['EOD']['suppress'] = True

        if verbosity < 2:
            self.dword_types['HC1']['suppress'] = True
            self.dword_types['HC2']['suppress'] = True
            self.dword_types['HC3']['suppress'] = True

        if verbosity < 1:
            self.dword_types['HC0']['suppress'] = True


    def filter(self, record):

        rectype = record.msg[:3]

        if self.addr is not None and self.dword is not None:
            record.where = f"{self.addr:012X} {self.dword:08X}"
        else:
            record.where = " "*21


        if rectype not in self.dword_types:
            return True

        opt = self.dword_types[rectype]

        # if 'suppress' in opt and opt['suppress']:
        #     return False

        record.msg = f"{opt['prefix']} {record.msg:45s}"

        return True


class HexDump:

    _markers = dict()

    def __init__(self, bitwidth=32, logger_name="hexdump"):
        self.logger = logging.getLogger(logger_name)
        self.fmtchar = {32: "I"}[bitwidth]
        self.introfmt = {
            32: "{addr:012X} {word:08X}    "
        }[bitwidth]
        # self.desc_fmt
        self.bitwidth = 32

    def fromfile(self, stream, nbytes):
        addr = stream.tell()
        data = stream.read(nbytes)
        self.dump(data,addr)

    @classmethod
    def add_marker(cls, addr, message):
        if addr in cls._markers:
            cls._markers[addr].append(message)
        else:
            cls._markers[addr] = [message]

    def dump(self, data, addr, desc=None, fmt=tuple((""))):
        for i,words in enumerate(struct.iter_unpack(self.fmtchar,data)):
            if addr+4*i in self._markers:
                for m in self._markers[addr+4*i]:
                    self.logger.info(f"MARK: {m}")

            if desc is None:
                txt = ""
            elif len(fmt) == 1:
                txt = fmt[0] + desc[i]
            elif len(fmt) == 2:
                txt = (fmt[0] if i==0 else fmt[1]) + desc[i]
            else:
                txt = fmt[i] + desc[i]

            self.dump_dword(addr+4*i, words[0], txt)

    def dump_dword(self, addr, word, desc):
        text = self.introfmt.format(addr=addr, word=word) + desc
        self.logger.info(text)

    def __call__(self, *args):

        if len(args) == 1:
            # render all the descriptions
            desc = list(d.format(**vars(args[0])) for d in args[0]._hexdump_desc)

            # ensure we have the same width for all fields
            maxlen = max(len(x) for x in desc)
            for i,d in enumerate(desc):
                desc[i] += " "*(maxlen-len(d)+3)

            # check if we have a format (colors) for this object
            try:
                fmt = args[0]._hexdump_fmt
            except AttributeError:
                fmt = tuple([""])

            # call dump() to do the work
            self.dump(args[0]._data, args[0]._addr, desc, fmt)
        else:
            self.dump_dword(*args)
