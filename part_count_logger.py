import serial
import time
from datetime import datetime
import csv
import ConfigParser
import dateutil.parser
import signal
import sys

# Allow use of ctrl-c (SIGINT) to kill program
def signal_handler(signal, frame):
        print 'Exiting'
        sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

# Read config file
config = ConfigParser.ConfigParser()
config.read('part_count_logger.cfg')

# Example config file:
#
#     [PartCountLogger]
#     port = /dev/ttyUSB1
#     dt = 10
#     log_until = 
#     max_records = 

port = config.get('PartCountLogger', 'port') # e.g. 'COM1' or "/dev/ttyUSB0"

dt = config.getint('PartCountLogger', 'dt') # seconds

log_until_str = config.get('PartCountLogger', 'log_until')
try:
    log_until = dateutil.parser.parse(log_until_str) if log_until_str != '' else None
except ValueError, e:
    raise ValueError("Could not interpret the value for 'log_until' in the config file")

max_records = config.get('PartCountLogger', 'max_records')
max_records = int(max_records) if max_records != '' else None

# Open serial connection
ser = serial.Serial(port = port, baudrate = 9600, bytesize = 8, parity = 'N', stopbits = 1, timeout = 5)
ser.isOpen()

# Open CSV and write CSV header
csv_created_at = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
col_names = "tstamp flowrate >2um >3um >5um >7um >10um >15um >20um >200um cal alog1 alog2 alog3".split()
csv_name = 'part_count_logger_{}.csv'.format(csv_created_at)
with open(csv_name, 'w') as f:
        writer = csv.writer(f)
        msg = "Logging data to {} every {}s".format(csv_name, dt)
        if log_until:
            msg += "\n until {}".format(log_until)
        if max_records:
            msg += "\n until {} records have been written".format(max_records)
        print msg
        writer.writerow(col_names)

records = 0
while True:
    ser.write("S\r\n")
    time.sleep(1)
    out = ""
    tstamp = datetime.now()
    
    while ser.inWaiting() > 0:
        out += ser.read(1)
    if out == '':
        raise Exception("Device did not respond to prompt")
        
    # Separate echoed input from output by splitting on '=',
    # split the output on whitespace
    # then convert each element in the resulting list from a hex string to an int
    data = [int(i, 16) for i in out.partition('=')[2].split()]
    
    # Split data into various components
    flowrate = data[0] # fixed at 60 ml/min
    bins = data[1:9] # >2um,>3um,>5um,>7um,>10um,>15um,>20um,>200um
    cal = data[9] # fixed at 80H
    analog_inputs = data[10:13] # 4-20mA inputs w/ 12-bit ADC (i.e. in range 0-4096)
    
    # Log data to CSV
    with open(csv_name, 'a') as f:
        writer = csv.writer(f)
        formatted_data = [tstamp.strftime("%Y-%m-%d %H:%M:%S"), flowrate] + bins + [cal] + analog_inputs
        print formatted_data
        writer.writerow(formatted_data)
    
    # Check to see if we should stop logging
    if max_records and records >= max_records:
        print "Max records reached"
        break
    if log_until and datetime.now() >= log_until:
        print "Max logging time reached"
        break
    
    time.sleep(dt - 1)
    records += 1 

