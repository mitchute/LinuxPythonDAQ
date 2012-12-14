#!/usr/bin/python

import time
import serial
from datetime import datetime 

# configure the serial connections (the parameters differs on the device you are connecting to)
ser = serial.Serial(port='/dev/ttyUSB0',baudrate=9600)

ser.open()

channels = 8
num = 48 + channels 
while True:
	print datetime.now()
	ser.write('!0RA' + chr(num))
	x = channels
	while x >= 0:
		msb = ser.read(1)
		lsb = ser.read(1)
		read = (ord(msb)*256) + ord(lsb)
		print x, read	
		x = x - 1	
	time.sleep(1)
	
	
