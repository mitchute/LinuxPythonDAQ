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

class ChannelClass():

    def __init__(self):
        self.Channels = []
        # add any number of channels here
        self.Channels.append(AChannel("HXInletTemp", self.fTemperatureIn, "[F]"))
        self.Channels.append(AChannel("HXOutletTemp", self.fTemperatureOut, "[F]"))
        self.Channels.append(AChannel("HXFlowRate", self.fFlowRate, "[GPM]"))
        self.Channels.append(AChannel("HeaterAmps", self.fHeaterAmps, "[A]"))
        self.Channels.append(AChannel("HeaterVolts", self.fHeaterVolts, "[V]"))

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
        return 0.9 + 0.2*volts

    def fHeaterAmps(self, volts):
        # made up empirical correlation
        return 0.1 + 0.6*volts
        
    def fHeaterVolts(self, volts):
        # made up empirical correlation
        return 0.8 + 0.23*volts        

class AChannel():

    def __init__(self, ChannelName, fProcessor, Units):
        self.name = ChannelName
        self.processor = fProcessor
        self.units = Units
        self.initData()

    def initData(self):
        self.timeHistory = [float('nan')]
        self.valueHistory = [float('nan')]
        self.bits = float('nan')
        self.volts = float('nan')

    def Process(self, time, bits):
        if bits < config.minimumBits or bits > config.maximumBits:
            bits = float('nan')
            volts = float('nan')
            val = float('nan')
        else:
            volts = channels.digitalToAnalog(bits)
            val = self.processor(volts)
        self.timeHistory.append(time)
        self.bits = bits
        self.volts = volts
        self.valueHistory.append(val)

    #call this function anytime (like: for ch in channels.Channels: ch.Spew())
    def Spew(self):
        print "%s: (%s, %s, %s, %s)" % (self.name, self.timeHistory[-1], self.bits, self.volts, self.valueHistory[-1])

class Configuration():

    # 0: Set up the channel class:
    #   a) define the channels in the ChannelClass.__init__() function
    #   b) modify the digital to analog conversion function to give: volts=f(bits)
    #   c) add conversion functions for each channel to give a physical value from the volts

    # 1: set a base directory to store the data,
    #   the expanduser function is platform independent by itself, and the '~' gives the home dir
    def baseDir(self):
        return os.path.join(os.path.expanduser("~"), "dataAcq")

    # 2: define the time step, in seconds as a function of the current time
    #   this allows you to vary the sampling rate over the course of a test
    def getTimeStep(self, currentTime):
        if currentTime < 3:
            return 0.5
        elif currentTime < 8:
            return 0.8
        else:
            return 2

    # 3: define the data acquisition flag (the time to stop taking data)
    #   this allows you to easily stop the test after, say, 24 hours (86400s)
    #   perhaps this could also eventually be more sophisticated to check other things
    #   it would be easy enough to check the latest sample data for out-of-range
    def getContinueFlag(self, currentTime):
        if currentTime < 120:
            return True
        else:
            return False

    # 4: define the portName, these will vary based on OS
    def getPortName(self):
        if sys.platform.startswith('win32') or sys.platform.startswith('cygwin'):
            return 'COM1'
        elif sys.platform.startswith('linux'):
            return '/dev/ttyUSB0'

    # 5: define the resolution and scale of the digital converter, in mV/bit
    milliVoltsPerBit = 1  # not sure this is the right approach...
    minimumBits = 0  # just for reporting purposes to avoid plotting out-of-range data
    maximumBits = 5000  # just for reporting purposes to avoid plotting out-of-range data

class AInfo():

    def __init__(self, label, defaultvalue):
        self.label = label
        self.value = defaultvalue

    def set_val(self, newval):
        self.value = newval

class InfoClass():

    def __init__(self):
        self.name = AInfo('Client Name:', 'Anonymous')
        self.location = AInfo('Location:', 'Anywhere')
        self.date = AInfo('Test Date:', 'Today I guess')
        self.depth = AInfo('Borehole Depth:', 'Pretty Deep')
        self.diameter = AInfo('Borehole Diameter', 'Pretty Wide')
        self.loop = AInfo('Loop Description:', 'Loopy')
        self.grout = AInfo('Grout Type:', 'Grouty')
        self.cement = AInfo('Cement Seal Description:', 'Cementy')
        self.swl = AInfo('SWL:', 'I dont even know')
        self.tester = AInfo('Test Operator:', 'Me')
        self.witness = AInfo('Witness:', 'This other guy')

    def GetSummary(self):
        summary = ''
        for inf in [self.name, self.location, self.date, self.depth, self.diameter, self.loop,
                    self.grout, self.cement, self.swl, self.tester, self.witness]:
            summary += '%s %s\n' % (inf.label, inf.value)
        return summary

class IOStuff():

    def __init__(self):
        # put a base file path here
        baseDir = config.baseDir()
        self.make_sure_path_exists(baseDir)
        # get a filename
        now = datetime.now()
        date = now.strftime('%Y%m%d-%H%M%S')
        sfile = "data-%s.csv" % date
        path = os.path.join(baseDir, sfile)
        try:
            self.outFile = open(path, 'w')
        except:
            print "Couldn't open output file at the desired path (%s), something's wrong" % (path)
            sys.exit(1)

    def make_sure_path_exists(self, path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    def issueHeaderString(self):
        s = info.GetSummary()
        s += "ReadCount,TimeStamp,SecondsSinceStarting,LogarithmSeconds,"
        for ch in channels.Channels:
            s += "Bits_%s," % ch.name
        for ch in channels.Channels:
            s += "Volts_%s," % ch.name
        for ch in channels.Channels:
            s += "Processed_%s%s," % (ch.name, ch.units)
        self.outFile.write(s)
        self.outFile.write("\n") # is this cross-platform?

    def issueReportString(self, times):
        s_time = ",".join(times)
        s_bits = ",".join("%10.3f" % x.bits for x in channels.Channels)
        s_volts = ",".join("%10.3f" % x.volts for x in channels.Channels)
        s_vals = ",".join("%10.3f" % x.valueHistory[-1] for x in channels.Channels)
        s = ",".join([s_time, s_bits, s_volts, s_vals])
        self.outFile.write(s)
        self.outFile.write("\n") # is this cross platform?

class DataReader():

    def __init__(self):

        # for testing, you can enable this flag so it won't try to actually read data from the device
        #   instead it will just generate random values
        self.fakeDataSource = False

        # if we aren't faking the data, then open the serial port here
        if not self.fakeDataSource:

            # configure the serial connections
            self.ser = serial.Serial(port=config.getPortName(), baudrate=2400, timeout=0.025)

            # open the serial connection
            self.ser.open()

        # initialize a constant for convenience
        self.iZeroChar = ord('0') # should be 48, but this looks a bit nicer

    def DoOneIteration(self, curTime):

        # configure channels here, and transmit character
        numChannels = len(channels.Channels)
        maxChannel = numChannels - 1 # zero-based
        cMaxChannel = chr(self.iZeroChar + maxChannel)

        # send a transmit signal
        if not self.fakeDataSource:
            self.ser.write('!0RA' + cMaxChannel)
        # loop over all channels
        for ch in reversed(channels.Channels):
            if self.fakeDataSource:
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
            ch.Process(curTime, read)

class MainDataLooper():

    def __init__(self, allDoneCallbackFunction, statusCallbackFunction, writeData):

        # initialize the callbacks based on arguments
        self.allDoneCallbackFunction = allDoneCallbackFunction
        self.statusCallbackFunction = statusCallbackFunction

        # initialize the flag for whether or not we should actually write data
        self.writeData = writeData

        # tell all the channels to clear themselves for a fresh start
        for ch in channels.Channels:
            ch.initData()

        # initialize the flag that the GUI uses to force me to stop
        self.forceStop = False

    def run(self):

        # set up file IO if we are actually writing data
        if self.writeData:

            # instantiate the IO class, which will help with some formatting and file I/O operations
            io = IOStuff()

            # spew the header
            io.issueHeaderString()

        # instantiate the reader, passing in the channel class instance
        reader = DataReader()

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
            reader.DoOneIteration(currentTime)
            # send an update to the status callback
            gobject.idle_add(self.statusCallbackFunction, 'Sampling: Sample count = %s, Current time = %s [s]' % (readerCount, currentTime))
            # create string representations for each list (times are already strings...no need to cast)
            if self.writeData: io.issueReportString(times)
            # get a new time step value from the config routine
            thisTimeStep = config.getTimeStep(currentTime)
            # then pause for a moment
            time.sleep(thisTimeStep)
            # finally check the flag to see if we are done
            if not config.getContinueFlag(currentTime): break

        gobject.idle_add(self.statusCallbackFunction, 'Sampling Complete: Sample count = %s, Final time = %s [s]' % (readerCount, currentTime))

class InputWindow(gtk.Dialog):

    def __init__(self):
        gtk.Dialog.__init__(self)

        # make sure we understand we are modal so we block
        self.set_modal(True)

        # initialization
        self.set_title("Can I have some inputs?")
        self.set_border_width(10)

        # add all the entries, to keep things obvious we aren't doing a loop or anything
        self.entry_name = gtk.Entry()
        self.entry_name.set_text(info.name.value)
        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(gtk.Label(info.name.label))
        hbox.pack_start(self.entry_name)
        self.vbox.pack_start(hbox, False, False, 0)

        self.entry_location = gtk.Entry()
        self.entry_location.set_text(info.location.value)
        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(gtk.Label(info.location.label))
        hbox.pack_start(self.entry_location)
        self.vbox.pack_start(hbox, False, False, 0)

        self.entry_date = gtk.Entry()
        self.entry_date.set_text(info.date.value)
        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(gtk.Label(info.date.label))
        hbox.pack_start(self.entry_date)
        self.vbox.pack_start(hbox, False, False, 0)

        self.entry_depth = gtk.Entry()
        self.entry_depth.set_text(info.depth.value)
        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(gtk.Label(info.depth.label))
        hbox.pack_start(self.entry_depth)
        self.vbox.pack_start(hbox, False, False, 0)

        self.entry_diameter = gtk.Entry()
        self.entry_diameter.set_text(info.diameter.value)
        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(gtk.Label(info.diameter.label))
        hbox.pack_start(self.entry_diameter)
        self.vbox.pack_start(hbox, False, False, 0)

        self.entry_loop = gtk.Entry()
        self.entry_loop.set_text(info.loop.value)
        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(gtk.Label(info.loop.label))
        hbox.pack_start(self.entry_loop)
        self.vbox.pack_start(hbox, False, False, 0)

        self.entry_grout = gtk.Entry()
        self.entry_grout.set_text(info.grout.value)
        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(gtk.Label(info.grout.label))
        hbox.pack_start(self.entry_grout)
        self.vbox.pack_start(hbox, False, False, 0)

        self.entry_cement = gtk.Entry()
        self.entry_cement.set_text(info.cement.value)
        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(gtk.Label(info.cement.label))
        hbox.pack_start(self.entry_cement)
        self.vbox.pack_start(hbox, False, False, 0)

        self.entry_swl = gtk.Entry()
        self.entry_swl.set_text(info.swl.value)
        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(gtk.Label(info.swl.label))
        hbox.pack_start(self.entry_swl)
        self.vbox.pack_start(hbox, False, False, 0)

        self.entry_tester = gtk.Entry()
        self.entry_tester.set_text(info.tester.value)
        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(gtk.Label(info.tester.label))
        hbox.pack_start(self.entry_tester)
        self.vbox.pack_start(hbox, False, False, 0)

        self.entry_witness = gtk.Entry()
        self.entry_witness.set_text(info.witness.value)
        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(gtk.Label(info.witness.label))
        hbox.pack_start(self.entry_witness)
        self.vbox.pack_start(hbox, False, False, 0)

        # add the response buttons here
        self.add_button("OK", gtk.RESPONSE_OK)
        self.add_button("Cancel", gtk.RESPONSE_CANCEL)

        # show myself
        self.show_all()

class GUI(gtk.Window):

    def __init__(self):
        gtk.Window.__init__(self)
        self.connect("destroy", self.onClose)

        # GUI layout initialization
        self.initLayout()

        # center it on the screen
        self.set_position(gtk.WIN_POS_CENTER)

        # show the form
        self.show_all()

    def initLayout(self):

        # initialization
        self.set_title("Data Acquisition")
        self.set_border_width(10)

        # add snapshot reading outputs, a tree on the left and a plot on the right
        self.liststore = gtk.ListStore(str, float, float, str)

        # create the TreeView using liststore
        self.treeview = gtk.TreeView(self.liststore)

        # setup a row in the liststore for each channel
        for ch in channels.Channels:
            self.liststore.append([ch.name, float('nan'), float('nan'), ch.units])

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
        self.tvcolumn3 = gtk.TreeViewColumn('Value [units]')
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
        self.canvas.set_size_request(600,400)

        # create the hbox to hold this tree and the snapshot plot
        hbox_plot = gtk.HBox(spacing=6)
        hbox_plot.pack_start(self.treeview)
        hbox_plot.pack_start(self.canvas)

        # form buttons
        self.btnEditInfo = gtk.Button(label = "Edit Info")
        self.btnEditInfo.connect("clicked", self.onEdit)
        self.btnRunTest = gtk.Button(label = "Start (test)")
        self.btnRunTest.connect("clicked", self.onRunTest)
        self.btnRun = gtk.Button(label = "Start (write data)")
        self.btnRun.connect("clicked", self.onRun)
        self.btnStop = gtk.Button(label = "Stop")
        self.btnStop.connect("clicked", self.onStop)
        self.btnStop.set_sensitive(False)
        self.btnClose = gtk.Button(stock = gtk.STOCK_CLOSE)
        self.btnClose.connect("clicked", self.onClose)
        hbox_btns = gtk.HBox(spacing=6)
        hbox_btns.pack_start(self.btnEditInfo)
        hbox_btns.pack_start(self.btnRunTest)
        hbox_btns.pack_start(self.btnRun)
        hbox_btns.pack_start(self.btnStop)
        hbox_btns.pack_start(self.btnClose)

        # status bar
        self.sbar = gtk.Statusbar()
        self.context_id = self.sbar.get_context_id("Statusbar")
        self.sbar.push(self.context_id, "Program has been initialized!")
        self.sbar.show()
        hbox_status = gtk.HBox(spacing=6)
        hbox_status.pack_start(self.sbar)

        # vbox to hold everything
        vbox = gtk.VBox(spacing=6)
        vbox.pack_start(hbox_plot, False, False, 0)
        vbox.pack_start(hbox_btns, False, False, 0)
        vbox.pack_start(hbox_status)

        # store master container in the window
        self.add(vbox)

    def startThread(self, writeData = True):
        # instantiate the main data acquisition class
        self.DataAcquirer = MainDataLooper(gui.processIsComplete, gui.updateStatus, writeData)
        # start the data acquisition as a separate (background) thread
        Thread(target=self.DataAcquirer.run).start()

    def onRunTest(self, widget):
        for ch in channels.Channels:
            self.ax.plot(ch.timeHistory, ch.valueHistory, label=ch.name)
        self.startThread(writeData = False)
        self.btnRun.set_sensitive(False)
        self.btnRunTest.set_sensitive(False)
        self.btnEditInfo.set_sensitive(False)
        self.btnStop.set_sensitive(True)

    def onRun(self, widget):
        for ch in channels.Channels:
            self.ax.plot(ch.timeHistory, ch.valueHistory, label=ch.name)
        self.startThread()
        self.btnRun.set_sensitive(False)
        self.btnRunTest.set_sensitive(False)
        self.btnEditInfo.set_sensitive(False)
        self.btnStop.set_sensitive(True)

    def onStop(self, widget):
        self.DataAcquirer.forceStop = True
        self.btnRun.set_sensitive(True)
        self.btnRunTest.set_sensitive(True)
        self.btnEditInfo.set_sensitive(True)
        self.btnStop.set_sensitive(False)

    def onClose(self, widget):
        if hasattr(self, 'DataAcquirer'):
            self.DataAcquirer.forceStop = True
        gtk.main_quit()

    def onEdit(self, widget):

        # need to get project inputs first:
        InputWin = InputWindow()

        # this will block until the user clicks or destroys the form
        retVal = InputWin.run()

        # only continue if we surely got the OK response
        if retVal == gtk.RESPONSE_OK:
            # update the info class
            info.name.set_val(InputWin.entry_name.get_text())
            info.location.set_val(InputWin.entry_location.get_text())
            info.date.set_val(InputWin.entry_date.get_text())
            info.depth.set_val(InputWin.entry_depth.get_text())
            info.diameter.set_val(InputWin.entry_diameter.get_text())
            info.loop.set_val(InputWin.entry_loop.get_text())
            info.grout.set_val(InputWin.entry_grout.get_text())
            info.cement.set_val(InputWin.entry_cement.get_text())
            info.swl.set_val(InputWin.entry_swl.get_text())
            info.tester.set_val(InputWin.entry_tester.get_text())
            info.witness.set_val(InputWin.entry_witness.get_text())
            # update on the status bar
            self.sbar.push(self.context_id, "Project information was updated!")

        # of course we can destroy the window now
        InputWin.destroy()

    def updateTree(self):
        bits = []
        for ch in range(len(channels.Channels)):
            bits.append(channels.Channels[ch].bits)
            self.liststore[ch][1] = channels.Channels[ch].bits
            self.liststore[ch][2] = channels.Channels[ch].volts
            self.liststore[ch][3] = '%s %s' % (channels.Channels[ch].valueHistory[-1], channels.Channels[ch].units)

    def updatePlot(self):
        self.ax.clear()
        for ch in channels.Channels:
            self.ax.plot(ch.timeHistory, ch.valueHistory, label=ch.name)
        self.ax.xaxis.grid(True)
        self.ax.yaxis.grid(True)
        self.plt.legend(loc='upper left')
        self.canvas.draw()

    def updateStatus(self, msg):
        self.sbar.push(self.context_id, msg)
        self.updateTree()
        self.updatePlot()

    def processIsComplete(self):
        self.btnRun.set_sensitive(True)
        self.btnRunTest.set_sensitive(True)
        self.btnEditInfo.set_sensitive(True)
        self.btnStop.set_sensitive(False)
        # update on the status bar
        self.sbar.push(self.context_id, "Data Acquisition Process Complete!")

# instantiate the configuration globally, this is where most of the project-specific changes will go
config = Configuration()

# instantiate the info class
info = InfoClass()

# set up the channels
channels = ChannelClass()

# instantiate the GUI, it handles everything
gui = GUI()

# run
gtk.main()
