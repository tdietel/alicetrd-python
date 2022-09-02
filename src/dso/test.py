import oscilloscopeRead.dso1kb as dso1kb
import zmq
import time

context = zmq.Context()
dso0 = context.socket(zmq.REQ)
dso0.connect('tcp://localhost:7740')

t1 = time.time()
dso0.send_string("read")
returned = dso0.recv()
t2 = time.time()

print(f'time taken: {t2-t1}')


# interface = dso1kb.getInterfaceName()
# dso = dso1kb.Dso(f'/dev/{interface}')
# dso.getRawData(True, 1)
# dso.getRawData(True, 2)
# dso.getRawData(True, 4)
# print(dso.getByteData([1, 2, 4]))