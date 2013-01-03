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

class Configuration():

    # 1: set a base directory to store the data,
    # !*!* include a trailing separator (slash) *!*!
    # the expanduser function is platform independent by itself, and gives the home dir
    def baseDir(self):
        return os.path.expanduser("~") + "/dataAcq/"

    # 2: setup the channels array and the correlation functions in the ChannelClass

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
        if currentTime < 12:
            return True
        else:
            return False

    # 5: define the portName, could be COM1, or /dev/TTYUSO0, or otherwise
    def portName(self):
        return '/dev/ttyUSB0'

    
    # for testing, you can enable this flag so it won't try to actually read data from the device
    def testMode(self):
        return True

class AChannel():
    
    def __init__(self, ChannelName, fProcessor):
        self.name = ChannelName
        self.processor = fProcessor
        self.rawHistory = []
        self.valueHistory = []
        self.value = -999999
        self.raw = -999999
        
    def Process(self, raw):
        if raw == -999999:
            val = -999999
        else:
            val = self.processor(raw)
        self.rawHistory.append(raw)
        self.valueHistory.append(val)
        self.raw = raw
        self.value = val
        return val 
                
class ChannelClass():

    def __init__(self):
        self.Channels = []
        # add any number of channels here
        self.Channels.append(AChannel("HXInletTemp", self.fTemperatureIn))
        self.Channels.append(AChannel("HXOutletTemp", self.fTemperatureOut))
        self.Channels.append(AChannel("HXOutletTemp3", self.fTemperatureOut))
        self.Channels.append(AChannel("HXOutletTemp4", self.fTemperatureOut))

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

    def issueHeaderString(self, channels):
        s = "ReadCount,TimeStamp,SecondsSinceStarting,LogarithmSeconds,"
        for ch in channels.Channels:
            s += "Raw%s," % ch.name
        for ch in channels.Channels:
            s += "Processed%s," % ch.name
        self.outFile.write(s)
        self.outFile.write("\n") # is this cross-platform?

    def issueReportString(self, times):
        s_time = ",".join(times)
        s_raw = ",".join("%10.3f" % x.raw for x in channels.Channels)
        s_vals = ",".join("%10.3f" % x.value for x in channels.Channels)
        s = ",".join([s_time, s_raw, s_vals])
        self.outFile.write(s)
        self.outFile.write("\n") # is this cross platform?

class DataReader():

    def __init__(self, channels):

        # accept the argument as the instantiated channel class
        self.channels = channels

        if not config.testMode(): 
            
            # configure the serial connections
            self.ser = serial.Serial(port=config.portName(), baudrate=2400, timeout=0.025)

            # open the serial connection
            self.ser.open()

        # initialize a constant for convenience
        self.iZeroChar = ord('0') # should be 48, but this looks a bit nicer

    def DoOneIteration(self):

        # configure channels here, and transmit character
        numChannels = len(self.channels.Channels)
        maxChannel = numChannels - 1 # zero-based
        cMaxChannel = chr(self.iZeroChar + maxChannel)

        # send a transmit signal
        if not config.testMode(): 
            self.ser.write('!0RA' + cMaxChannel)
        # loop over all channels
        for ch in self.channels.Channels:
            if config.testMode():
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
            # process this by the channel itself
            ch.Process(read)
                
class MainDataLooper():

    def __init__(self, guiCallbackFunction, allDoneCallbackFunction):

        # initialize the callbacks based on arguments
        self.guiCallbackFunction = guiCallbackFunction
        self.allDoneCallbackFunction = allDoneCallbackFunction

        # initialize the flag that the GUI uses to force me to stop
        self.forceStop = False

    def run(self):

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
            if self.forceStop: break
            readerCount += 1
            # clear and add integer count, timestamp, time-secs, log(time-secs)
            times = []
            times.append(str(readerCount))
            times.append(str(datetime.now()))
            currentTime = time.time() - startTime
            times.append(str(round(currentTime, 4)))
            times.append(str(round(math.log(currentTime), 4)))
            # get the raw and processed values
            reader.DoOneIteration()
            # send an update to the GUI callback
            gobject.idle_add(self.guiCallbackFunction, readerCount)
            # create string representations for each list (times are already strings...no need to cast)
            io.issueReportString(times)
            # get a new time step value from the config routine
            thisTimeStep = config.getTimeStep(currentTime)
            # then pause for a moment
            time.sleep(thisTimeStep)
            # finally check the flag
            ContinueLooping = config.getContinueFlag(currentTime)

        gobject.idle_add(self.allDoneCallbackFunction)

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

        # update frequency
        lblRead = gtk.Label()
        lblRead.set_label("Latest reading:")
        self.lblReadVal = gtk.Label()
        self.lblReadVal.set_label("...Initialized...")
        hbox_read = gtk.HBox(spacing=6)
        hbox_read.pack_start(lblRead)
        hbox_read.pack_start(self.lblReadVal)

        # add snapshot reading outputs, a tree on the left and a plot on the right
        self.liststore = gtk.ListStore(str, float)

        # create the TreeView using liststore
        self.treeview = gtk.TreeView(self.liststore)

        # setup a row in the liststore for each channel
        for ch in channels.Channels:
            self.liststore.append([ch.name, -999999])

        # create a channel name column
        self.tvcolumn = gtk.TreeViewColumn('Channel Name')
        self.cell = gtk.CellRendererText()
        self.tvcolumn.pack_start(self.cell, True)
        self.tvcolumn.set_attributes(self.cell, text=0)
        
        # create a channel value column
        self.tvcolumn1 = gtk.TreeViewColumn('Current Value')
        self.cell1 = gtk.CellRendererText()
        self.tvcolumn1.pack_start(self.cell1, True)
        self.tvcolumn1.set_attributes(self.cell1, text=1)
        
        # add columns to treeview
        self.treeview.append_column(self.tvcolumn)
        self.treeview.append_column(self.tvcolumn1)
        
        # create the plot and add it also
        labels = []
        for ch in channels.Channels:
            labels.append(ch.name)
        self.plot2xlocations = na.array(range(len(labels)))+0.5
        width = 0.35
        
        self.fig = matplotlib.pyplot.figure()
        self.ax = self.fig.add_subplot(1,1,1)
                
        self.ax.xaxis.set_ticks(self.plot2xlocations+ width/2, labels)
        #self.ax.xlim(0, xlocations[-1]+width*2)
        self.ax.xaxis.tick_bottom()
        
        self.canvas = Canvas(self.fig)
        self.ax.xaxis.grid(True)
        self.ax.yaxis.grid(True)
        self.ax.bar(self.plot2xlocations, height=[0,1,2,3], width=width)
        self.ax.yaxis.set_label('Current data readings')
        #self.ax.plot([0], [0], marker='*', linestyle="None")
        self.canvas.set_size_request(600,300)
        
        # create the hbox to hold this tree and the snapshot plot
        hbox_plot = gtk.HBox(spacing=6)
        hbox_plot.pack_start(self.treeview)
        hbox_plot.pack_start(self.canvas)

        # create the plot and add it also
        self.fig2 = matplotlib.pyplot.figure()
        self.ax2 = self.fig2.add_subplot(1,1,1)
        self.canvas2 = Canvas(self.fig2)
        self.ax2.xaxis.grid(True)
        self.ax2.yaxis.grid(True)
        self.ax2.plot([0],[0])
        self.canvas2.set_size_request(800,300)
        
        # create the hbox to hold this tree and the snapshot plot
        hbox_plot2 = gtk.HBox(spacing=6)
        hbox_plot2.pack_start(self.canvas2)
        
        # form buttons
        self.btnRun = gtk.Button(label = "Start")
        self.btnRun.connect("clicked", self.onRun)
        self.btnClose = gtk.Button(stock = gtk.STOCK_CLOSE)
        self.btnClose.connect("clicked", self.onClose)
        hbox_btns = gtk.HBox(spacing=6)
        hbox_btns.pack_start(self.btnRun)
        hbox_btns.pack_start(self.btnClose)

        # vbox to hold everything
        vbox = gtk.VBox(spacing=6)
        vbox.pack_start(hbox_read, False, False, 0)
        vbox.pack_start(hbox_plot, False, False, 0)
        vbox.pack_start(hbox_plot2, False, False, 0)
        vbox.pack_start(hbox_btns, False, False, 0)
        self.add(vbox)

    def startThread(self):
        # instantiate the main data acquisition class
        self.DataAcquirer = MainDataLooper(gui.updateForm, gui.processIsComplete)
        # start the data acquisition as a separate (background) thread
        Thread(target=self.DataAcquirer.run).start()

    def onRun(self, widget):
        if self.threadRunning:
            self.DataAcquirer.forceStop = True
            self.btnRun.set_label('Start')
        else:
            self.startThread()
            self.btnRun.set_label('Stop')
        self.threadRunning = not self.threadRunning

    def onClose(self, widget):
        if hasattr(self, 'DataAcquirer'):
            self.DataAcquirer.forceStop = True
        gtk.main_quit()

    def updateForm(self, latestIter):
        self.lblReadVal.set_label("Update count = %s" % latestIter)
        rawVals = []
        for ch in range(len(channels.Channels)):
            rawVals.append(channels.Channels[ch].raw)
            self.liststore[ch][1] = channels.Channels[ch].raw
        self.ax.clear()
        self.ax.bar(self.plot2xlocations, height=rawVals)
        
        #self.ax.plot(rawVals, marker='*', linestyle="None")
        self.canvas.draw()
        for ch in channels.Channels:
            self.ax2.plot(ch.valueHistory)
        self.canvas2.draw()

    def processIsComplete(self):
        print "All done"
        self.threadRunning = False
        self.btnRun.set_label('Start')

# instantiate the configuration globally, this is where most of the project-specific changes will go
config = Configuration()

# instantiate the channel class, which will create the channels.Channels array
channels = ChannelClass()

# instantiate the GUI, it handles everything
gui = GUI()

# run
gtk.main()
