
import click
import zmq
import struct
from time import sleep, time


class zmq_env:
    def __init__(self):

        self.context = zmq.Context()

        self.trdbox = self.context.socket(zmq.REQ)
        self.trdbox.connect('tcp://localhost:7766')

        self.sfp0 = self.context.socket(zmq.REQ)
        self.sfp0.connect('tcp://localhost:7750')

        self.sfp1 = self.context.socket(zmq.REQ)
        self.sfp1.connect('tcp://localhost:7751')

        self.dso0 = self.context.socket(zmq.REQ)
        self.dso0.connect('tcp://localhost:7740')


@click.group()
@click.pass_context
def minidaq(ctx):
    ctx.obj = zmq_env()

def get_pretrigger_count(trdbox):
    trdbox.send_string("read 0x102")
    cnt = int(trdbox.recv_string(), 16)
    # print(cnt)
    return cnt

def wait_for_pretrigger(trdbox, interval=0.1):
    cnt = get_pretrigger_count(trdbox)
    while get_pretrigger_count(trdbox) <= cnt:
        sleep(interval)

def gen_event_header(payloadsize):
    """Generate MiniDaq header"""
    ti = time()
    tis = int(ti)
    tin = ti-tis
    return struct.pack("<LBBBBBBHLL", 
        0xDA7AFEED, # magic
        1, 0, # equipment 1:0 is event
        0, 1, 0, # reserved / header version / reserved
        20, payloadsize, # header, payload sizes
        tis, int(tin) # time stamp
    )

@minidaq.command()
@click.option('--nevents','-n', default=2, help='Number of triggered events you want to read.')
@click.pass_context
def readevent(ctx, nevents=2):

    outfile = open("data.bin", "wb")

    for ievent in range(nevents):

        # -------------------------------------------------------------
        # trigger

        # ctx.obj.trdbox.send_string(f"write 0x08 1") # send trigger
        ctx.obj.trdbox.send_string(f"trg unblock") # send trigger
        print(ctx.obj.trdbox.recv_string())

        wait_for_pretrigger(ctx.obj.trdbox, 0.5)

        # -------------------------------------------------------------
        # readout

        # define the equipments that should be read out
        eqlist = [ctx.obj.sfp1, ctx.obj.sfp0, ctx.obj.dso0]

        # send query for data to all equipments
        for eq in eqlist:
            eq.send_string("read")

        # receive the data
        data = list(eq.recv() for eq in eqlist)

        # -------------------------------------------------------------
        # build event and write to file

        evdata = gen_event_header(payloadsize = sum(len(i) for i in data))
        for segment in data:
            evdata += segment
            # print(len(segment),outfile.tell())

        outfile.write(evdata)
        # print("total:", len(evdata))


    outfile.close()