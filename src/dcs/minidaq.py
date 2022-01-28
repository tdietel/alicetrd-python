
import click
import zmq

class zmq_env:
    def __init__(self):

        self.context = zmq.Context()

        self.trdbox = self.context.socket(zmq.REQ)
        self.trdbox.connect('tcp://localhost:7766')

        self.sfp0 = self.context.socket(zmq.REQ)
        self.sfp0.connect('tcp://localhost:7750')

        self.sfp1 = self.context.socket(zmq.REQ)
        self.sfp1.connect('tcp://localhost:7751')


@click.group()
@click.pass_context
def minidaq(ctx):
    ctx.obj = zmq_env()


@minidaq.command()
@click.pass_context
def readevent(ctx):

    ctx.obj.trdbox.send_string(f"write 0x08 1") # send trigger
    print(ctx.obj.trdbox.recv_string())

    ctx.obj.sfp0.send_string("read")
    data = ctx.obj.sfp0.recv()
    print(len(data))
