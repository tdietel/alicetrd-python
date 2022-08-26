import zmq
import time
import oscilloscopeRead.dso1kb as dso1kb
import struct


context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind('tcp://*:7740')
print('Socket connected on tcp://*:7740')

interface = dso1kb.getInterfaceName()
dso = dso1kb.Dso(f'/dev/{interface}')

print('Waiting for request...')

while True:
    received = socket.recv_string()
    print('Request received, checking...')

    if received == "read":
        dso.getRawData(True, 1)
        dso.getRawData(True, 2)
        dso.getRawData(True, 4)

        socket.send(dso.getByteData([1, 2, 4]))

        dso.resetChList()
