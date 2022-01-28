
import click
import zmq

su704_pre_base = 0x100
su736_dis_base = 0x280
su738_sfp0_base = 0x400
su738_sfp1_base = 0x500
su707_scsn_base = 0x000

class TrdboxCommand:
    def __init__(self, connect):

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(connect)

    def exec(self, cmd):
        self.socket.send_string(cmd)
        return self.socket.recv_string()


@click.group()
@click.option('-c', '--connect', default='tcp://localhost:7766')
@click.pass_context
def trdbox(ctx, connect):
    ctx.obj = TrdboxCommand(connect)

@trdbox.command()
@click.pass_context
def status(ctx):

    # from: lbox_addr.h
    #define SU736_BASE          0x280
    #define SU738_BASE_A        0x400
    #define SU738_BASE_B        0x500
    #define SU704_PRE_BASE_A    0x100
    #define SU707_SCSN_BASE_A   0x000


    registers = list((
      dict( name='pre_conf', addr=su704_pre_base+0),
      dict( name='pre_dgg',  addr=su704_pre_base+1),
      dict( name='pre_cnt',  addr=su704_pre_base+2),
      dict( name='pre_stat', addr=su704_pre_base+3),

      # dict( name='dis_dac',  addr=su736_dis_base+0x08), # reads CONF
      # dict( name='dis_led',  addr=su736_dis_base+0x0c), # reads CONF
      dict( name='dis_conf', addr=su736_dis_base+0x0d),
      dict( name='dis_freq0', addr=su736_dis_base+0x00),
      dict( name='dis_freq1', addr=su736_dis_base+0x01),
      dict( name='dis_time0', addr=su736_dis_base+0x04),
      dict( name='dis_time1', addr=su736_dis_base+0x05),
    ))

    for r in registers:
        rd = int(ctx.obj.exec(f"read {r['addr']}"),16)
        print(f"{r['name']:<10} [0x{r['addr']:03x}]: 0x{rd:08x} = {rd}")

@trdbox.command()
@click.pass_context
def unblock(ctx):
    ctx.obj.exec(f"write {su704_pre_base+3} 1")

@trdbox.command()
@click.argument('ch', callback=lambda c,p,x: int(x,0))
@click.argument('thresh', callback=lambda c,p,x: int(x,0))
@click.pass_context
def dis_thr(ctx, ch, thresh):
    value = ( (ch&1) << 14 ) | ( thresh & 0xFFF )
    ctx.obj.exec(f"write {su736_dis_base+0x08} {value}")

@trdbox.command()
@click.argument('conf', callback=lambda c,p,x: int(x,0))
@click.pass_context
def dis_conf(ctx, conf):
    ctx.obj.exec(f"write {su736_dis_base+0x0d} {conf}")

@trdbox.command()
@click.argument('cmd', default=1)
@click.pass_context
def pretrigger(ctx, cmd):
    ctx.obj.exec(f"write 0x08 {cmd}")

@trdbox.command()
@click.argument('sfp')
@click.argument('cmd')
@click.pass_context
def sfp(ctx, sfp, cmd):
    ctx.obj.exec(f"sfp{sfp} {cmd}")

@trdbox.command()
@click.argument('sfp')
@click.pass_context
def dump(ctx, sfp, cmd):
    ctx.obj.exec(f"dump sfp{sfp}")

@trdbox.command()
@click.argument('address', callback=lambda c,p,x: int(x,0))
@click.pass_context
def read(ctx, address):
    rd = int(ctx.obj.exec(f"read {address}"),16)
    print(f"Read from 0x{address:04x}: {rd} = 0x{rd:08x}")

@trdbox.command()
@click.argument('address', callback=lambda c,p,x: int(x,0))
@click.argument('data', callback=lambda c,p,x: int(x,0))
@click.pass_context
def write(ctx, address, data):
    ctx.obj.exec(f"write {address} {data}")
