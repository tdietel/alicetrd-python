
import urwid
import pydim
import logging
# from trdmon.dimwid import dimwid as dimwid
from trdmon.dimwid import notify_urwid as uwnotify

class info(urwid.Pile):
    def __init__(self, sm,stack,layer):

        super().__init__([
        urwid.Text("%02d_%d_%d" % (sm,stack,layer)),
        state(sm,stack,layer) ])


class state(urwid.AttrMap): #(urwid.Text("FOO"),"state")):

    def __init__(self, sm,stack,layer):
        self.textwidget = urwid.Text(("state", "SERVICE 2"))
        super().__init__(self.textwidget, {"state": "state"} )

        self.state = -999

        svcname = f"trd-fee_{sm:02d}_{stack}_{layer}_STATE"
        pydim.dic_info_service(svcname, "I", self.dimcb, timeout=30)


    def dimcb(self, s):
        self.state = s
        uwnotify(self.refresh)
        # dimwid.request_callback(self)

    statemap = { 
        -999: "off", 0: "off", 
        13: "ERROR", 99: "ERROR",
        5: "STANDBY", 43: "STDBY_INIT", 3: "CONFIGURED",
        42: "INITIALIZING", 45: "TESTING", 44: "CONFIGURING" 
    }

    def refresh(self):

        if self.state in statemap:
            txt = statemap[self.state]

            if txt=='off':
                self.textwidget.set_text(("fsm:off", txt))

            elif txt=='ERROR':
                self.textwidget.set_text(("fsm:error", txt))

            elif txt in ("STANDBY","STANDBY_INIT"):
                self.textwidget.set_text(("fsm:static", txt))

            elif txt=="CONFIGURED":
                self.textwidget.set_text(("fsm:ready", txt))

            elif txt in ("INITIALIZING", "TESTING", "CONFIGURING"):
                self.textwidget.set_text(("fsm:trans", txt))

        else:
            self.textwidget.set_text(("fsm:error", f"state:{state:02X}"))
