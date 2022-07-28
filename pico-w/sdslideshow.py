### sdslideshow.py v0.3
### Slide show of files on microsd card

### Tested with Inky Frame and Pimoroni MicroPython v1.19.3

### copy this file to Inky Frame as main.py

### MIT License

### Copyright (c) 2022 Kevin J. Walters

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
import re
import random
import time

import uos
from machine import Pin
import jpegdec
from picographics import PicoGraphics, DISPLAY_INKY_FRAME as DISPLAY

gc.collect()

graphics = PicoGraphics(DISPLAY)

SD_MOUNTPOINT = "/sd"
SLIDE_DIR = SD_MOUNTPOINT + "/slides"
JPEG_RE = re.compile(r".\.[jJ][pP][eE]?[gG]$")

import sdcard  # noqa: E402 - putting this at the top causes an MBEDTLS OOM error!?
sd_spi = SPI(0,
             sck=Pin(18, Pin.OUT),
             mosi=Pin(19, Pin.OUT),
             miso=Pin(16, Pin.OUT))
sd = sdcard.SDCard(sd_spi, Pin(22))
uos.mount(sd, SD_MOUNTPOINT)
gc.collect()

files = list(filter(JPEG_RE.search, uos.listdir(SLIDE_DIR)))
filename = files[0]

jpeg = jpegdec.JPEG(graphics)
gc.collect()

while True:
    for filename in files:
        graphics.set_pen(1)
        graphics.clear()

        jpeg.open_file(SLIDE_DIR + "/" + filename)
        jpeg.decode()

        gc.collect()
        print("START update()", gc.mem_free())
        graphics.update()
        print("END update()", gc.mem_free())

        time.sleep(300)

uos.unmount(SD_MOUNTPOINT)
