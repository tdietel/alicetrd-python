
import urwid
import pydim
import logging
from trdmon.dimwid import notify_urwid as uwnotify


# class servers(urwid.Pile):
class servers(urwid.Columns):
    def __init__(self, servers):

        # Create a dictionary with all servers that we want to monitor
        self.servers = dict()
        for svcname,disp in servers.items():
            self.servers[svcname] = dict(
                display=disp, up=False, widget=urwid.Text(disp)
            )

        # call the constructor of urwid.Pile
        super().__init__([ s['widget'] for s in self.servers.values() ])

        # Subscribe to the DIM service that announces all new/removed servers
        pydim.dic_info_service("DIS_DNS/SERVER_LIST", self.cb, timeout=30, default_value="")


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

        # tell Urwid that we have to refresh the screen
        uwnotify(self.refresh)

    def refresh(self):
        logger=logging.getLogger(__name__)

        for s in self.servers.values():
            logger.debug(f"line: {s['display']} {s['up']}")

            if s['up']:
                s['widget'].set_text(("fsm:ready", s['display']))
            else:
                s['widget'].set_text(("fsm:error", s['display']))
