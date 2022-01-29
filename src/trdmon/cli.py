
# from . import start as start_loop
# from . import start as start_loop

from . import dimwid
# from . import trdbox
from . import roc
from . import dim

import logging
import urwid
import os
import pwd
import asyncio

from collections import OrderedDict

# ===========================================================================

def cli():


    # set up logging to /tmp/trdmon-{username}.log
    username = pwd.getpwuid( os.getuid() )[ 0 ]
    logging.basicConfig(filename='/tmp/trdmon-%s.log' % username,
      level=logging.DEBUG,
      format='%(asctime)s %(levelname)s %(funcName)s: %(message)s')
    logger=logging.getLogger(__name__)


    # ----------------------------------------------------------------
    # create widgets
    # ----------------------------------------------------------------

    # widget to monitor DIM servers
    dimservers = urwid.LineBox(dim.servers(OrderedDict(
        ztt_dimfed_server='ICL', trdbox='TRDbox', ArdPower='PWR')))


    # ----------------------------------------------------------------
    # create layout
    # ----------------------------------------------------------------

    top_widget = urwid.Frame(
        header=urwid.Text(("bg", "HEADER")),
        body =
        urwid.AttrMap(urwid.Filler(urwid.Pile([
            # urwid.LineBox(trdbox.daq()),
            # urwid.LineBox(trdbox.trigger()),
            urwid.LineBox(roc.info(0,2,0)),
            # urwid.LineBox(dim.servers(dimservers)),
            dimservers,
        ])), 'bg'),
        focus_part='header')

    # ----------------------------------------------------------------
    # column layout
    # ----------------------------------------------------------------

    # top_widget = urwid.Frame(
    #     header=urwid.Text(("bg", "HEADER")),
    #     body =
    #     urwid.AttrMap(urwid.Filler(urwid.Columns([
    #         # urwid.Pile([
    #             urwid.LineBox(trdbox.daq()),
    #             urwid.LineBox(trdbox.trigger()),
    #         # ]),
    #         # urwid.Pile([
    #             # urwid.LineBox(trdmon.roc.state(0,2,0)),
    #             urwid.LineBox(roc.info(0,2,0)),
    #             urwid.LineBox(dim.servers()),
    #         # ]),
    #         # trdbox_daq2(),
    #         # trdbox_daq_run(),
    #         # trdbox_daq_bytes_read(),
    #     ])), 'bg'),
    #     focus_part='header')


    dimwid.run(top_widget)
