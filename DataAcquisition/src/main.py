#!/usr/bin/python

import time
import serial
from datetime import datetime 

# configure the serial connections 
ser = serial.Serial(port='/dev/ttyUSB0', baudrate=2400, timeout=0.1)

# open the serial connection
ser.open()

# initialize a constant for convenience
iZeroChar = ord('0') # should be 48, but this looks a bit nicer
print iZeroChar

# configure channels here, and transmit character
numChannels = 4
maxChannel = numChannels - 1 # zero-based
cMaxChannel = chr(iZeroChar + maxChannel)

# infinite loop while we read and spew data
while True:	
	# send a transmit signal
	ser.write('!0RA' + cMaxChannel)
	# re-initialize the values list
	values = []
	# loop over all channels
	for x in range(numChannels):
		# read msb and lsb bytes
		msb = ser.read(1)
		lsb = ser.read(1)
		# check for errors
		if msb == '' or lsb == '':
			print "Could not receive data"
			values.append(-9999)
		else:
			# calculate a reading value
			read = (ord(msb)*256) + ord(lsb)
			# store it in the list
			values.append(read)
	# spew
	print "%s" % datetime.now(), values
	# pause
	time.sleep(0.25)
	
	
