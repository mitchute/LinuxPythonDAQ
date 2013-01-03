#!/usr/bin/python

# import the gtk libraries, initialize the threads to alert that this will be multithreaded
import gtk, gobject
gtk.gdk.threads_init()

# OS interaction library imports
import sys
import os
import errno

# general math and date/time based library imports
import math
import time
from datetime import datetime
from random import randint

# for serial communication, we import the python-serial library
import serial

# for background threading we need to import the threading library
from threading import Thread

# for graphical plot need to install python-matplotlib
import matplotlib
matplotlib.use('GtkAgg')
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as Canvas
import pylab
import cairo
import numpy.numarray as na

class AChannel():

    def __init__(self, ChannelName, fProcessor):
        self.name = ChannelName
        self.processor = fProcessor
        self.initData()

    def initData(self):
        self.timeHistory = []
        self.rawHistory = []
        self.voltsHistory = []
        self.valueHistory = []
        self.value = -9999
        self.bits = -9999
        self.volts = -9999

    def Process(self, time, bits):
        if bits < 0 or bits > 20000:
            bits = float('nan')
            volts = float('nan')
            val = float('nan')
        else:
            volts = config.channels.digitalToAnalog(bits)
            val = self.processor(volts)
        self.timeHistory.append(time)
        self.rawHistory.append(bits)
        self.voltsHistory.append(volts)
        self.valueHistory.append(val)
        self.bits = bits
        self.volts = volts
        self.value = val

    def Spew(self):
        print "%s: (%s, %s, %s, %s)" % (self.name, self.timeHistory[-1], self.bits, self.volts, self.value)

class ChannelClass():

    def __init__(self):
        self.Channels = []
        # add any number of channels here
        self.Channels.append(AChannel("HXInletTemp", self.fTemperatureIn))
        self.Channels.append(AChannel("HXOutletTemp", self.fTemperatureOut))
        self.Channels.append(AChannel("HXFlowRate", self.fFlowRate))

    def digitalToAnalog(self, bits):
        # made up conversion
        milliVoltPerBit = 1.2
        return (milliVoltPerBit / 1000.0) * bits

    def fTemperatureIn(self, volts):
        # made up empirical correlation
        return 0.2 + 0.3*volts

    def fTemperatureOut(self, volts):
        # made up empirical correlation
        return 0.6 + 0.1*volts

    def fFlowRate(self, volts):
        # made up empirical correlation
        return 0.4 + 0.2*volts

class Configuration():

    # 1: set a base directory to store the data,
    # !*!* include a trailing separator (slash) *!*!
    # the expanduser function is platform independent by itself, and gives the home dir
    def baseDir(self):
        return os.path.expanduser("~") + "/dataAcq/"

    # 2: setup the channels array and the correlation functions in the ChannelClass
    # instantiate the channel class, which will create the channels.Channels array
    channels = ChannelClass()

    # 3: define the time step, in seconds
    def getTimeStep(self, currentTime):
        if currentTime < 3:
            return 0.25
        elif currentTime < 8:
            return 0.5
        else:
            return 1

    # 4: define the data acquisition flag (the time to stop taking data)
    def getContinueFlag(self, currentTime):
        if currentTime < 120:
            return True
        else:
            return False

    # 5: define the portName, could be COM1, or /dev/TTYUSO0, or otherwise
    portName = '/dev/ttyUSB0'

    # 6: define the skip time at the beginning to avoid the strange initial results
    warmupTime = 2 # seconds

    # 7: define the resolution of the digital converter, in mV/bit
    milliVoltsPerBit = 1

    # for testing, you can enable this flag so it won't try to actually read data from the device
    testMode = False

class IOStuff():

    def __init__(self):
        # put a base file path here
        baseDir = config.baseDir()
        self.make_sure_path_exists(baseDir)
        # get a filename
        now = datetime.now()
        date = now.strftime('%Y%m%d-%H%M%S')
        sfile = "data-%s.csv" % date
        try:
            self.outFile = open(baseDir + sfile, 'w')
        except:
            print "Couldn't open output file at the desired path (%s), something's wrong" % (baseDir + sfile)
            sys.exit(1)

    def make_sure_path_exists(self, path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    def issueHeaderString(self):
        s = "ReadCount,TimeStamp,SecondsSinceStarting,LogarithmSeconds,"
        for ch in config.channels.Channels:
            s += "Bits_%s," % ch.name
        for ch in config.channels.Channels:
            s += "Volts_%s," % ch.name
        for ch in config.channels.Channels:
            s += "Processed_%s," % ch.name
        self.outFile.write(s)
        self.outFile.write("\n") # is this cross-platform?

    def issueReportString(self, times):
        s_time = ",".join(times)
        s_bits = ",".join("%10.3f" % x.bits for x in config.channels.Channels)
        s_volts = ",".join("%10.3f" % x.volts for x in config.channels.Channels)
        s_vals = ",".join("%10.3f" % x.value for x in config.channels.Channels)
        s = ",".join([s_time, s_bits, s_volts, s_vals])
        self.outFile.write(s)
        self.outFile.write("\n") # is this cross platform?

class DataReader():

    def __init__(self):

        if not config.testMode:

            # configure the serial connections
            self.ser = serial.Serial(port=config.portName, baudrate=2400, timeout=0.025)

            # open the serial connection
            self.ser.open()

        # initialize a constant for convenience
        self.iZeroChar = ord('0') # should be 48, but this looks a bit nicer

    def DoOneIteration(self, initialize, curTime):

        # configure channels here, and transmit character
        numChannels = len(config.channels.Channels)
        maxChannel = numChannels - 1 # zero-based
        cMaxChannel = chr(self.iZeroChar + maxChannel)

        # send a transmit signal
        if not config.testMode:
            self.ser.write('!0RA' + cMaxChannel)
        # loop over all channels
        for ch in config.channels.Channels:
            if config.testMode:
                msb = chr(randint(18,20))
                lsb = chr(randint(1,3))
            else:
                # read msb and lsb bytes
                msb = self.ser.read(1)
                lsb = self.ser.read(1)
            # check for errors
            if msb == '' or lsb == '':
                # could not receive data
                read = -999999
            else:
                # calculate a reading value
                read = (ord(msb)*256) + ord(lsb)
            if not initialize:
                # process this by the channel itself
                ch.Process(curTime, read)

class MainDataLooper():

    def __init__(self, allDoneCallbackFunction, statusCallbackFunction):

        # initialize the callbacks based on arguments
        self.allDoneCallbackFunction = allDoneCallbackFunction
        self.statusCallbackFunction = statusCallbackFunction

        # tell all the channels to clear themselves for a fresh start
        for ch in config.channels.Channels:
            ch.initData()

        # initialize the flag that the GUI uses to force me to stop
        self.forceStop = False

    def run(self):

        # instantiate the IO class, which will help with some formatting and file I/O operations
        io = IOStuff()

        # spew the header
        io.issueHeaderString()

        # instantiate the reader, passing in the channel class instance
        reader = DataReader()

        ####### this block does an initial set of samples to 'warm-up' or something the data logger
        # initialize the starting time
        startTime = time.time()
        while True:
            if self.forceStop: break
            # use an init flag of True to 'warm-up' the data logger?
            reader.DoOneIteration(True, 0)
            # determine if we should be done
            currentTime = time.time() - startTime
            if currentTime > config.warmupTime: break
            gobject.idle_add(self.statusCallbackFunction, 'Warming up: Current time = %s [s], Warmup ends at time = %s [s]' % (currentTime, config.warmupTime))

        # initialize the loop counter
        readerCount = 0

        # re-initialize the start time before we start doing real stuff
        startTime = time.time()

        # infinite loop while we read and spew data
        while True:
            if self.forceStop: break
            readerCount += 1
            # clear and add integer count, timestamp, time-secs, log(time-secs)
            times = []
            times.append(str(readerCount))
            times.append(str(datetime.now()))
            currentTime = time.time() - startTime
            times.append(str(round(currentTime, 4)))
            times.append(str(round(math.log(currentTime), 4)))
            # get the bits and processed values
            reader.DoOneIteration(False, currentTime)
            # send an update to the status callback
            gobject.idle_add(self.statusCallbackFunction, 'Sampling: Sample count = %s, Current time = %s [s]' % (readerCount, currentTime))
            # create string representations for each list (times are already strings...no need to cast)
            io.issueReportString(times)
            # get a new time step value from the config routine
            thisTimeStep = config.getTimeStep(currentTime)
            # then pause for a moment
            time.sleep(thisTimeStep)
            # finally check the flag to see if we are done
            if not config.getContinueFlag(currentTime): break
            #for ch in config.channels.Channels: ch.Spew()

        gobject.idle_add(self.statusCallbackFunction, 'Sampling Complete: Sample count = %s, Final time = %s [s]' % (readerCount, currentTime))

class GUI(gtk.Window):

    def __init__(self):
        gtk.Window.__init__(self)

        # GUI layout initialization
        self.initLayout()

        # set a flag saying whether something is running
        self.threadRunning = False

        # show the form
        self.show_all()

    def initLayout(self):

        # initialization
        self.set_title("Data Acquisition")
        self.set_border_width(10)

        # add snapshot reading outputs, a tree on the left and a plot on the right
        self.liststore = gtk.ListStore(str, float, float, float)

        # create the TreeView using liststore
        self.treeview = gtk.TreeView(self.liststore)

        # setup a row in the liststore for each channel
        for ch in config.channels.Channels:
            self.liststore.append([ch.name, float('nan'), float('nan'), float('nan')])

        # create a channel name column
        self.tvcolumn = gtk.TreeViewColumn('Channel Name')
        self.cell = gtk.CellRendererText()
        self.tvcolumn.pack_start(self.cell, True)
        self.tvcolumn.set_attributes(self.cell, text=0)

        # create a channel bits column
        self.tvcolumn1 = gtk.TreeViewColumn('Digital Bits')
        self.cell1 = gtk.CellRendererText()
        self.tvcolumn1.pack_start(self.cell1, True)
        self.tvcolumn1.set_attributes(self.cell1, text=1)

        # create a channel analog voltage column
        self.tvcolumn2 = gtk.TreeViewColumn('Analog Voltage')
        self.cell2 = gtk.CellRendererText()
        self.tvcolumn2.pack_start(self.cell2, True)
        self.tvcolumn2.set_attributes(self.cell2, text=2)

        # create a channel analog voltage column
        self.tvcolumn3 = gtk.TreeViewColumn('Value')
        self.cell3 = gtk.CellRendererText()
        self.tvcolumn3.pack_start(self.cell3, True)
        self.tvcolumn3.set_attributes(self.cell3, text=3)

        # add columns to treeview
        self.treeview.append_column(self.tvcolumn)
        self.treeview.append_column(self.tvcolumn1)
        self.treeview.append_column(self.tvcolumn2)
        self.treeview.append_column(self.tvcolumn3)

        # create the plot and add it also
        self.plt = matplotlib.pyplot
        self.fig = self.plt.figure()
        self.ax = self.fig.add_subplot(1,1,1)
        self.canvas = Canvas(self.fig)
        self.ax.xaxis.grid(True)
        self.ax.yaxis.grid(True)
        self.ax.plot([0],[0])
        self.canvas.set_size_request(600,300)

        # create the hbox to hold this tree and the snapshot plot
        hbox_plot = gtk.HBox(spacing=6)
        hbox_plot.pack_start(self.treeview)
        hbox_plot.pack_start(self.canvas)

        # form buttons
        self.btnRun = gtk.Button(label = "Start")
        self.btnRun.connect("clicked", self.onRun)
        self.btnClose = gtk.Button(stock = gtk.STOCK_CLOSE)
        self.btnClose.connect("clicked", self.onClose)
        hbox_btns = gtk.HBox(spacing=6)
        hbox_btns.pack_start(self.btnRun)
        hbox_btns.pack_start(self.btnClose)

        # status bar
        self.sbar = gtk.Statusbar()
        self.context_id = self.sbar.get_context_id("Statusbar")
        self.sbar.push(self.context_id, "Hey")
        self.sbar.show()
        hbox_status = gtk.HBox(spacing=6)
        hbox_status.pack_start(self.sbar)

        # vbox to hold everything
        vbox = gtk.VBox(spacing=6)
        vbox.pack_start(hbox_plot, False, False, 0)
        vbox.pack_start(hbox_btns, False, False, 0)
        vbox.pack_start(hbox_status)
        self.add(vbox)

    def startThread(self):
        # instantiate the main data acquisition class
        self.DataAcquirer = MainDataLooper(gui.processIsComplete, gui.updateStatus)
        # start the data acquisition as a separate (background) thread
        Thread(target=self.DataAcquirer.run).start()

    def onRun(self, widget):
        if self.threadRunning:
            self.DataAcquirer.forceStop = True
            self.btnRun.set_label('Start')
        else:
            self.ax.clear()
            for ch in config.channels.Channels:
                self.ax.plot(ch.timeHistory, ch.valueHistory, label=ch.name)
            self.ax.xaxis.grid(True)
            self.ax.yaxis.grid(True)
            self.plt.legend()
            self.startThread()
            self.btnRun.set_label('Stop')
        self.threadRunning = not self.threadRunning

    def onClose(self, widget):
        if hasattr(self, 'DataAcquirer'):
            self.DataAcquirer.forceStop = True
        gtk.main_quit()

    def updatePlot(self):
        bits = []
        for ch in range(len(config.channels.Channels)):
            bits.append(config.channels.Channels[ch].bits)
            self.liststore[ch][1] = config.channels.Channels[ch].bits
            self.liststore[ch][2] = config.channels.Channels[ch].volts
            self.liststore[ch][3] = config.channels.Channels[ch].value
        for ch in config.channels.Channels:
            self.ax.plot(ch.timeHistory, ch.valueHistory, label=ch.name)
        self.ax.xaxis.grid(True)
        self.ax.yaxis.grid(True)
        self.canvas.draw()

    def updateStatus(self, msg):
        self.sbar.push(self.context_id, msg)
        self.updatePlot()

    def processIsComplete(self):
        print "All done"
        self.threadRunning = False
        self.btnRun.set_label('Start')

# instantiate the configuration globally, this is where most of the project-specific changes will go
config = Configuration()

# instantiate the GUI, it handles everything
gui = GUI()

# run
gtk.main()
