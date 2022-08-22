
import urwid
import pydim
import logging
# from trdmon.dimwid import dimwid as dimwid
import trdmon.dimwid as dimwid

class info(urwid.Pile):
    def __init__(self, sm,stack,layer):

        super().__init__([
        urwid.Text("%02d_%d_%d" % (sm,stack,layer)),
        state(sm,stack,layer) ])


class state(urwid.AttrMap): #(urwid.Text("FOO"),"state")):

    def __init__(self, sm,stack,layer):
        self.textwidget = urwid.Text(("state", "SERVICE 2"))
        super().__init__(self.textwidget, {"state": "state"} )

        pydim.dic_info_service(f"trd-fee_{sm:02d}_{stack}_{layer}_STATE", "I", 
            dimwid.call(self.update), timeout=30, default_value=-1)

    statemap = { 
        -1:   ("fsm:off",    "off"), 
        0:    ("fsm:off",    "off"), 
        13:   ("fsm:error",  "ERROR"),
        99:   ("fsm:error",  "ERROR"),
        5:    ("fsm:static", "STANDBY"),
        43:   ("fsm:static", "STDBY_INIT"),
        3:    ("fsm:ready",  "CONFIGURED"),
        42:   ("fsm:trans",  "INITIALIZING"),
        45:   ("fsm:trans",  "TESTING"),
        44:   ("fsm:trans",  "CONFIGURING") 
    }

    def update(self, state):
        if state in self.statemap:
            self.textwidget.set_text(self.statemap[state])
        else:
            self.textwidget.set_text(("fsm:error", f"state:{state:02X}"))
