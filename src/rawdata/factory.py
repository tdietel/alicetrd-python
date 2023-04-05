
from .o32reader import o32reader
from .tfreader import TimeFrameReader, RdhStreamParser
from .zmqreader import zmqreader
from .minidaqreader import MiniDaqReader


def make_reader(source):

    # Instantiate the reader that will get events and subevents from the source
    if source.endswith(".o32") or source.endswith(".o32.bz2"):
        return o32reader(source)

    # TODO: timeframe readers temporarily disabled
    elif source.endswith(".tf") or source.endswith(".lnk"):
        return TimeFrameReader(source)
        # reader.log_header = lambda x: x.hexdump()

    elif source.endswith('.bin'):
        return MiniDaqReader(source)
        # reader.hexdump = hdump
        # reader.parsers[0x10] = trdfeeparser

    # elif source.startswith('tcp://'):
    #     reader = zmqreader(source)

    else:
        raise ValueError(f"unknown source type: {source}")
