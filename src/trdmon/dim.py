
import urwid
import pydim
import logging
from trdmon.dimwid import dimwid as dimwid

from collections import OrderedDict

class servers(urwid.Pile):
    def __init__(self):

        self.servers = OrderedDict(
          ztt_dimfed_server = dict(display='ICL'),
          # trdbox =  dict(display='TRDbox'),
          ArdPower =  dict(display='Power'),
          HV =  dict(display='HV'),
        )

        # create a widget for each DIM server
        for s in self.servers.values():
            s['up'] = False
            s['widget'] = urwid.Text(s['display'])

        # call the constructor of urwid.Pile
        super().__init__([ s['widget'] for s in self.servers.values() ])


        pydim.dic_info_service("DIS_DNS/SERVER_LIST", self.cb, timeout=30)

        dimwid.register_callback(self)


    def cb(self, data):
        logger=logging.getLogger(__name__)

        logger.debug(f"DIM servers: received {data}")
        for s in data.split('|'):
            parts = s.split('@')

            if len(parts)==2:
                if parts[0].startswith('+'):
                    up = True
                    srv = parts[0][1:]
                elif parts[0].startswith('-'):
                    up = False
                    srv = parts[0][1:]
                else:
                    up = True
                    srv = parts[0]

                if srv in self.servers:
                    self.servers[srv]['up'] = up

                # logger.debug(f"line: {s} {srv} {up}")


        dimwid.request_callback(self)

    def refresh(self):
        logger=logging.getLogger(__name__)

        for s in self.servers.values():
            logger.debug(f"line: {s['display']} {s['up']}")

            if s['up']:
                s['widget'].set_text(("fsm:ready", s['display']))
            else:
                s['widget'].set_text(("fsm:error", s['display']))
