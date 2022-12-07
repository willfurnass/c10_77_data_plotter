# ATI C10-77 particle count logger data plotter

Plot live data from one of these instruments, with data being read over a serial connection.  Blurb on the instruments:

> ATI’s Model C10/77 Particle Sensor is designed to provide valuable particle data by continuously monitoring particle counts in raw water, filter influent, or filter effluent. Based on a laser light blocking principle, this sensor will provide particle count data over size ranges from 2 to 400 microns, with three 4-20 mA analog outputs and an RS-232/485 digital output supplied as standard. The scaling of the three 4-20 mA outputs is selectable by use of DIP switches mounted on the counter circuit board, and can be set from 0-127 up to 0-32,000 counts per ml., with one channel proportional to total particles, one channel proportional to particles in the range of 3-5 microns, and one channel proportional to particles in the range of 7-10 microns. The digital output provides actual particle counts for particle sizes 2, 3, 5, 7, 10, 15, 20, and 200 microns. This data can be used for computerized calculations of filter removal efficiencies as well as trending of particle data.

Code abandoned early in development as decided against using the instrument for a particular experiment.

Dependencies:

 - Python 2.7
 - dateutil
 - pyserial
 - PyQt4 and Qwt5
 - mock (for testing)
