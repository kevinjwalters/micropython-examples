### serial-periodic-print-mcp9740 v1.1

### copy this file to BBC micro:bit V2 as main.py

### MIT License

### Copyright (c) 2025 Kevin J. Walters

### Permission is hereby granted, free of charge, to any person obtaining a copy
### of this software and associated documentation files (the "Software"), to deal
### in the Software without restriction, including without limitation the rights
### to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
### copies of the Software, and to permit persons to whom the Software is
### furnished to do so, subject to the following conditions:

### The above copyright notice and this permission notice shall be included in all
### copies or substantial portions of the Software.

### THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
### IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
### FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
### AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
### LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
### OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
### SOFTWARE.


import gc

import mcp7940

from microbit import i2c
from utime import ticks_us, ticks_diff, ticks_add

## PERIOD_US = 60 * 60 * 1000 * 1000
## PERIOD_US = 10 * 1000 * 1000
PERIOD_US = 1 * 1000 * 1000


class EnhancedI2C:
    def __init__(self, i2c):
        self._i2c = i2c

    def readfrom_mem(self, addr, memaddr, nbytes, *, addrsize=8):
        i2c.write(addr, bytes([memaddr]))
        return(i2c.read(addr, nbytes))

    def readfrom_mem_into(self, addr, memaddr, buf, *, addrsize=8):
        raise NotImplementedError
    
    def writeto_mem(self, addr, memaddr, buf, *, addrsize=8):
        i2c.write(addr, bytes([memaddr]) + buf)


ei2c = EnhancedI2C(i2c)
mcp = mcp7940.MCP7940(ei2c)
mcp.set_trim(0)
mcp.time = (2025, 1, 1, 00, 00, 00, 2, 1)
mcp.start()

last_print_us = None
timestamp_us = None
uncollected = True

gc.collect()
last_print_us = ticks_us()
while True:    
    timestamp_us = ticks_us()
    if ticks_diff(timestamp_us, last_print_us) >= PERIOD_US:
        print(timestamp_us, ticks_us(), *mcp.time, sep=",")
        ### Don't assign timestamp_us here in case it has slipped a little
        last_print_us = ticks_add(last_print_us, PERIOD_US)
        uncollected = True
    elif uncollected:
        gc.collect()
        uncollected = False
