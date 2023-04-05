
import urwid
import pydim
import logging
import trdmon.dimwid as dimwid

class servers(urwid.Pile):
    def __init__(self, servers):

        # self.servers = OrderedDict(
        #   ztt_dimfed_server = dict(display='ICL'),
        #   # trdbox =  dict(display='TRDbox'),
        #   ArdPower =  dict(display='Power'),
        #   HV =  dict(display='HV'),
        # )

        self.servers = dict()
        for dimname,disp in servers.items():
            self.servers[dimname] = dict(display=disp)

        # create a widget for each DIM server
        for s in self.servers.values():
            s['up'] = False
            s['widget'] = urwid.Text(s['display'])

        # call the constructor of urwid.Pile
        super().__init__([ s['widget'] for s in self.servers.values() ])

        # Subscribe to the DIM service that announces all new/removed servers
        pydim.dic_info_service("DIS_DNS/SERVER_LIST", 
            dimwid.call(self.update), 
            timeout=30, default_value="")


    def update(self, *args):
        logger=logging.getLogger(__name__)

        data = args[0]
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

        for s in self.servers.values():
            # logger.debug(f"line: {s['display']} {s['up']}")
            if s['up']:
                s['widget'].set_text(("fsm:ready", s['display']))
            else:
                s['widget'].set_text(("fsm:error", s['display']))
