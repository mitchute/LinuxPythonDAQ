#!/usr/bin/python

import os
import errno
import math
import time
import serial
from datetime import datetime 

class Configuration():

	# 1: set a base directory to store the data, 
	# !*!* include a trailing separator (slash) *!*!
	def baseDir(self):
		return "/home/edwin/dataAcq/"

	# 2: setup the channels array and the correlation functions in the ChannelClass

	# 3: define the time step, in seconds
	def getTimeStep(self, currentTime):
		if currentTime < 10:
			return 0.25
		elif currentTime < 30:
			return 0.5
		else:
			return 1
		
	# 4: define the data acquisition flag (the time to stop taking data)
	def getContinueFlag(self, currentTime):
		if currentTime < 60:
			return True
		else:
			return False
		
class ChannelClass():
		
	def __init__(self):
		self.Channels = []
		# add any number of channels here
		self.Channels.append(["HXInletTemp", self.fTemperatureIn])	
		self.Channels.append(["HXOutletTemp", self.fTemperatureOut])
					
	def fTemperatureIn(self, volts):
		# made up empirical correlation
		return 0.2 + 0.3*volts
		
	def fTemperatureOut(self, volts):
		# made up empirical correlation
		return 1.2 + 0.1*volts

class IOStuff():
		
	def __init__(self):
		# put a base file path here
		baseDir = config.baseDir()
		self.make_sure_path_exists(baseDir)
		# get a filename
		now = datetime.now()
		date = now.strftime('%Y%m%d-%H%M%S')
		sfile = "data-%s.csv" % date
		self.outFile = open(baseDir + sfile, 'w')
		
	def make_sure_path_exists(self, path):
		try:
			os.makedirs(path)
		except OSError as exception:
			if exception.errno != errno.EEXIST:
				raise
	
	def issueHeaderString(self, channels):
		s = "ReadCount,TimeStamp,SecondsSinceStarting,LogarithmSeconds,"
		for ch in channels.Channels:
			s += "Raw%s," % ch[0]
		for ch in channels.Channels:
			s += "Processed%s," % ch[0]
		self.outFile.write(s)
		self.outFile.write("\n") # is this cross-platform?
	
	def issueReportString(self, times, raw, vals):
		s_time = ",".join(times) 
		s_raw = ",".join("%10.3f" % x for x in raw)
		s_vals = ",".join("%10.3f" % x for x in vals)
		s = ",".join([s_time, s_raw, s_vals])
		self.outFile.write(s)
		self.outFile.write("\n") # is this cross platform?
	
class DataReader():
		
	def __init__(self, channels):
		
		# accept the argument as the instantiated channel class 
		self.channels = channels
		
		# configure the serial connections 
		self.ser = serial.Serial(port='/dev/ttyUSB0', baudrate=2400, timeout=0.025)

		# open the serial connection
		self.ser.open()
				
		# initialize a constant for convenience
		self.iZeroChar = ord('0') # should be 48, but this looks a bit nicer
									
	def DoOneIteration(self):

		# configure channels here, and transmit character
		numChannels = len(self.channels.Channels)
		maxChannel = numChannels - 1 # zero-based
		cMaxChannel = chr(self.iZeroChar + maxChannel)

		# clean/prepare
		raw = []
		values = []

		# send a transmit signal
		self.ser.write('!0RA' + cMaxChannel)
		# loop over all channels
		for ch in self.channels.Channels:
			# read msb and lsb bytes
			msb = self.ser.read(1)
			lsb = self.ser.read(1)
			# check for errors
			if msb == '' or lsb == '':
				# could not receive data
				raw.append(-9999)
				values.append(-9999)
			else:
				# calculate a reading value
				read = (ord(msb)*256) + ord(lsb)
				# store the raw value in the list
				raw.append(read)
				# then process it into meaningful value
				values.append(ch[1](read))
		# return whatever we got
		return raw, values

class MainDataLooper():
	
	def run(self):
	
		# instantiate the channel class, which will create the channels.Channels array
		channels = ChannelClass()
		
		# instantiate the IO class, which will help with some formatting and file I/O operations
		io = IOStuff()
		
		# spew the header
		io.issueHeaderString(channels)
		
		# instantiate the reader, passing in the channel class instance
		reader = DataReader(channels)
		
		# initialize the looping flag
		ContinueLooping = True
				
		# initialize the starting time 
		startTime = time.time()
		
		# initialize the loop counter
		readerCount = 0
		
		# infinite loop while we read and spew data
		while ContinueLooping:	
			readerCount += 1
			print "Starting a new iteration, count # " + str(readerCount)
			# clear and integer count, timestamp, time-secs, log(time-secs)
			times = []
			times.append(str(readerCount))
			times.append(str(datetime.now()))
			currentTime = time.time() - startTime
			times.append(str(round(currentTime, 4)))
			times.append(str(round(math.log(currentTime), 4)))
			# get the raw and processed values
			raw, vals = reader.DoOneIteration()
			# create string representations for each list (times are already strings...no need to cast)
			io.issueReportString(times, raw, vals)
			# get a new time step value from the config routine
			thisTimeStep = config.getTimeStep(currentTime)
			# then pause for a moment
			time.sleep(thisTimeStep)
			# finally check the flag
			ContinueLooping = config.getContinueFlag(currentTime)

# this is the module's executable code, create the config instance and start running the main program
config = Configuration()
MainDataLooper().run()
