
import logging
import struct
# from pprint import pprint
# from termcolor import colored

# https://alexandra-zaharia.github.io/posts/make-your-own-custom-color-formatter-with-python-logging/

class ColorFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://stackoverflow.com/a/56944256/3638629"""

    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, fmt="%(levelname)-10s %(message)s"):
        super().__init__(fmt)
        # "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.reset + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset,
            # 21: self.blue + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

    # ch.setLevel(logging.DEBUG)

class AddLocationFilter(logging.Filter):
    """
    This is a filter which injects contextual information into the log.

    Rather than use actual contextual information, we just use random
    data in this demo.
    """

    def __init__(self, suppress=[]):
        self.where = ""
        self.suppress = suppress

    def set_location(self, where):
        self.where = where

    dword_types = {
      'HC0': { "prefix": '\033[1;37;104m' }, # white on blue
      'HC1': { "prefix": '\033[0;37;104m' }, # grey on blue
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

        # if rectype in self.suppress:
        #     return False

        if rectype not in self.dword_types:
            return True

        opt = self.dword_types[rectype]

        # if 'suppress' in opt and opt['suppress']:
        #     return False

        record.msg = f"{self.where}{opt['prefix']} {record.msg:45s}"

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


    # def colorize(fmts, first='\033[1;37;40m ', body='\033[0;37;100m '):
    #     if len(fmts) >= 1:
    #         fmts[0] = first + fmts[0]
    #     for i,f in enumerate(fmts[1:]):
    #         fmts[i+1] = body + f
    #     return fmts

