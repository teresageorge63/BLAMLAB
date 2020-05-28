import serial
from serial.tools import list_ports
import struct

def init_ser(self):
	#CONNECT TO HAPTIC DEVICE
	ports = list_ports.comports()
	mydev = next((p.device for p in ports if p.pid == 1155))
	self.ser = serial.Serial(mydev,9600,timeout=.1)

def sendsig(self,finger,direction):
    #would read from table, but table not available yet
    dur_int = [1,0]
    for i in range(20):
        if i == finger:
            dur_int.append(100)
        else:
            dur_int.append(0)
    data = struct.pack('22B',*dur_int)
    self.ser.write(data)