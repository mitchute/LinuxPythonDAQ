#!/usr/bin/python

import gtk, gobject
gtk.gdk.threads_init()

import sys
import os
import errno
import math
import time
import serial
from datetime import datetime
from threading import Thread

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

    def __init__(self, guiCallbackFunction, allDoneCallbackFunction):

        # initialize the callbacks based on arguments
        self.guiCallbackFunction = guiCallbackFunction
        self.allDoneCallbackFunction = allDoneCallbackFunction

        # initialize the flag that the GUI uses to force me to stop
        self.forceStop = False

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
            if self.forceStop:
                break
            readerCount += 1
            # send an update to the GUI callback
            gobject.idle_add(self.guiCallbackFunction, readerCount)
            # clear and add integer count, timestamp, time-secs, log(time-secs)
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

        gobject.idle_add(self.allDoneCallbackFunction)

# this is the main GUI for the program
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

        ## site selection
        #lblSite = gtk.Label()
        #lblSite.set_label("Choose a Mesonet Site:")
        #meso_site_combo = gtk.ComboBox(model=meso_site_store)
        #meso_site_combo.connect("changed", self.on_name_combo_changed)
        #meso_site_combo.set_active(initIndex)
        #cell = gtk.CellRendererText()
        #meso_site_combo.pack_start(cell, True)
        #meso_site_combo.add_attribute(cell, "text", 1)
        #hbox_site = gtk.HBox(spacing=6)
        #hbox_site.pack_start(lblSite)
        #hbox_site.pack_start(meso_site_combo)

        # update frequency
        lblRead = gtk.Label()
        lblRead.set_label("Latest reading:")
        self.lblReadVal = gtk.Label()
        self.lblReadVal.set_label("...Initializing...")
        hbox_read = gtk.HBox(spacing=6)
        hbox_read.pack_start(lblRead)
        hbox_read.pack_start(self.lblReadVal)

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
        #vbox.pack_start(hbox_freq, False, False, 0)
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
        self.DataAcquirer.forceStop = True
        gtk.main_quit()

    def updateForm(self, latestIter):
        self.lblReadVal.set_label("Update count = %s" % latestIter)

    def processIsComplete(self):
        print "All done"
        self.threadRunning = False
        self.btnRun.set_label('Start')

# instantiate the configuration, this is where most of the project-specific changes will go
config = Configuration()

# instantiate the GUI, it handles pretty much everything
gui = GUI()

# process the GUI
gtk.main()
