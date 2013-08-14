#!/usr/bin/env python

import ConfigParser
import csv
from datetime import datetime
import dateutil.parser
import os
from PyQt4 import Qt
import PyQt4.Qwt5 as Qwt
from PyQt4.Qwt5.anynumpy import *
import serial
import sys
import time
import win32com.shell.shell as shell

ASADMIN = 'asadmin'
if sys.platform == 'win32' and sys.argv[-1] != ASADMIN:
    # Re-run script with elev prileges when started by ordinary user
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([script] + sys.argv[1:] + [ASADMIN])
    shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=params)
    sys.exit(0)

class PartCountLogger(Qwt.QwtPlot):
    def __init__(self, *args):
        Qwt.QwtPlot.__init__(self, *args)

        # Prompt the user for a CSV file to save data to then
        # create a CSV and write a header to it if it didn't previously exist
        self.csv_filename = Qt.QFileDialog.getSaveFileName(self,
                            'File to save data to', 'C:\\')
        self.size_bin_names = ">2um >3um >5um >7um >10um >15um >20um >200um".split()
        self.write_csv_header()

        # Load software config from .cfg file
        self.load_config()

        # Open the serial port
        try:
            self.open_serial(self.port)
        except serial.SerialException, e:
            Qt.QMessageBox.about(self, "Error", "Could not open serial connection using {}".format(self.port))
            sys.exit(-1)

        # Initialise timestamp and counter used to determine when to 
        # stop reading data from the particle counter
        self.last_read = None
        self.records_read = 0

        # Create lists for storing data from particle counter
        self.tstamps = list()
        self.size_bins = [list() for i in self.size_bin_names]
        self.flows = list()
        self.cal = list()
        self.analog_inputs = list()

        # Initialise the plot
        self.setCanvasBackground(Qt.Qt.white)

        # Set plot title
        self.setTitle("Particle counts")
        self.insertLegend(Qwt.QwtLegend(), Qwt.QwtPlot.BottomLegend)

        # Curves to plot
        self.curves = list()
        color_names = "blue red cyan darkCyan green magenta yellow darkGreen".split()
        for bin_name, color_name in zip(self.size_bin_names, color_names):
            curve = Qwt.QwtPlotCurve(bin_name)
            curve.setPen(Qt.QPen(getattr(Qt.Qt, color_name)))
            curve.attach(self)
            self.curves.append(curve)

        # Axis labels
        self.setAxisTitle(Qwt.QwtPlot.xBottom, "Time")
        self.setAxisTitle(Qwt.QwtPlot.yLeft, "Particle counts per ml")

        # Enable axis autoscaling
        self.setAxisAutoScale(Qwt.QwtPlot.xBottom)
        self.setAxisAutoScale(Qwt.QwtPlot.yLeft)

        # Legend
        legend = Qwt.QwtLegend()
        legend.setFrameStyle(Qt.QFrame.Box | Qt.QFrame.Sunken)
        legend.setItemMode(Qwt.QwtLegend.ClickableItem)
        self.insertLegend(legend, Qwt.QwtPlot.BottomLegend)

        # Grid
        self.grid = Qwt.QwtPlotGrid()
        self.grid.enableXMin(True)
        self.grid.setMajPen(Qt.QPen(Qt.Qt.gray, 0, Qt.Qt.DotLine))
        self.grid.setMinPen(Qt.QPen(Qt.Qt.gray, 0, Qt.Qt.DotLine))
        self.grid.attach(self)

        # Event loop period
        self.startTimer(100)

    def load_config(self, cfg='part_count_logger.cfg'):
        """Read in the software config from a file"""
        config = ConfigParser.ConfigParser()
        config.read(cfg)

        # Port could be e.g. 'COM1' or "/dev/ttyUSB0"
        self.port = config.get('PartCountLogger', 'port')
        # Read in as an integer the frequency to read from the instrument
        # 8s seems to be the minimum here
        self.dt = config.getint('PartCountLogger', 'dt')
        # Read in as a string the timestamp we should log until (optional)
        log_until_str = config.get('PartCountLogger', 'log_until')
        # then try convert it to a datetime object
        try:
            self.log_until = dateutil.parser.parse(log_until_str) \
                    if log_until_str != '' else None
        except ValueError, e:
            raise ValueError("Could not interpret the value for 'log_until' in the config file")
        # Read in as an integer the maximum number of records we should generate (optional)
        max_records_str = config.get('PartCountLogger', 'max_records')
        self.max_records = int(max_records_str) if max_records_str != '' else None
        return

    def open_serial(self, port):
        """Establish a serial connection to the particle counter"""
        self.port = port
        self.ser = serial.Serial(port=port, baudrate=9600, bytesize=8, 
                   parity='N', stopbits=1, timeout=5)
        return self.ser.isOpen()

    def write_csv_header(self, overwrite=False):
        """Write a header to the output CSV file

           Do this only if it does not already exist
           or if overwrite is True

        """
        if overwrite or not os.path.exists(self.csv_filename):
            with open(self.csv_filename, 'w') as f:
                csv.writer(f).writerow(['tstamp', 'flowrate'] + \
                        self.size_bin_names + ['cal', 'alog1', 'alog2', 'alog3'])

    def captureData(self):
        """Prod the particle counter over RS242 and append recived data to instance attr lists"""
        self.ser.write("S\r\n")
        time.sleep(1)
        bytes_read = ""

        while self.ser.inWaiting() > 0:
            bytes_read += self.ser.read(1)
        if bytes_read == '':
            raise Exception("Device did not respond to prompt")

        # Separate echoed input from output by splitting on '=',
        # split the output on whitespace
        # then convert each element in the resulting list from a hex string to an int
        data = [int(i, 16) for i in bytes_read.partition('=')[2].split()]

        # Split data into various components
        self.tstamps.append(datetime.now())
        # Flowrate should be fixed at 60 ml/min
        self.flowrates.append(data[0]) 
        # size_bins are >2um,>3um,>5um,>7um,>10um,>15um,>20um,>200um
        for count, size_bin in zip(data[1:9], self.size_bins):
            size_bin.append(count)
        # Should be fixed at 80H
        self.cal.append(data[9])
        # 4-20mA inputs w/ 12-bit ADC (i.e. in range 0-4096)
        for analog_value, analog_input in zip(data[10:13], self.analog_inputs):
            analog_input.append(analog_value)

    def write_csv(self):
        """Append most recently read data to CSV"""
        with open(self.csv_filename, 'a') as f:
            csv.writer(f).writerow(self.tstamps[-1:].strftime("%Y-%m-%d %H:%M:%S") + \
                                   self.flowrates[-1:] + \
                                   [size_bin[-1] for size_bin in self.size_bins] + \
                                   self.cal[-1:] + \
                                   [an_inp[-1] for an_inp in self.analog_inputs])

    def update_curves(self):
        """Link the plot curves to lists containing updated data"""
        for counts, curve in zip(self.size_bins, self.curves):
            curve.setData(self.tstamps, counts)

    def timerEvent(self, e):
        if (self.log_until is not None and self.log_until < datetime.now()) or \
               (self.max_records is not None and self.records_read > self.max_records) or \
               (self.last_read is not None and now - self.last_read < self.dt):
            self.replot()
            return
        self.captureData()
        self.write_csv()
        self.update_curves()
        self.records_read += 1
        self.last_read = datetime.now()
        self.replot()

def make():
    demo = PartCountLogger()
    demo.resize(500, 300)
    demo.show()
    return demo


def main(args):
    app = Qt.QApplication(args)
    demo = make()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main(sys.argv)
