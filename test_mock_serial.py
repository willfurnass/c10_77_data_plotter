import sys
from itertools import count
import mock

serial_buffer = None
counter = count()

def refill_serial_buffer():
    #(ints in hex separated by spaces)  
    # echo=Q bin1 bin2 bin3 bin4 bin5 bin6 bin7 bin8 cal alog1 alog2 alog3 
    int_data = (60, 11, 22, 33, 44, 55, 66, 77, 88, 128, 50, 60, 70)

    itr = counter.next()
    buf = list('echo=' + ' '.join([hex(min(i * itr, 1023))[2:] 
        for i in int_data]))
    buf.reverse()
    return buf

def read(_):
    global serial_buffer
    return serial_buffer.pop()

def inWaiting():
    global serial_buffer
    if serial_buffer is None:
        serial_buffer = refill_serial_buffer()
    if len(serial_buffer) < 1:
        # reset buffer for next dummy instrument poll
        serial_buffer = refill_serial_buffer()
        return 0
    else:
        return len(serial_buffer)

with mock.patch('serial.Serial') as MockSerial:
    instance = MockSerial.return_value
    instance.isOpen.return_value = True
    instance.write.return_value = None
    instance.read = read
    instance.inWaiting = inWaiting
    
    import part_count_logger
    part_count_logger.main(sys.argv)
