### sdslideshow.py v1.0
### Slide show of jpeg files on microSD card

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

### TODO - go into low power mode for the sleep between images
### TODO - use two buttons to jump forward and back
### TODO - use button to select different modes
### TODO - add index file to order the slideshow

import gc
import re
import time

import uos
from machine import Pin, SPI
import jpegdec
from picographics import PicoGraphics, DISPLAY_INKY_FRAME as DISPLAY

import sdcard


gc.collect()
graphics = PicoGraphics(DISPLAY)

IMAGE_PAUSE = 300

IF_BLACK = 0
IF_WHITE = 1
IF_GREEN = 2
IF_BLUE = 3
IF_RED = 4
IF_YELLOW = 5
IF_ORANGE = 6
IF_TAUPE = 7

SD_MOUNTPOINT = "/sd"
SLIDE_DIR = SD_MOUNTPOINT + "/slides"
JPEG_RE = re.compile(r".\.[jJ][pP][eE]?[gG]$")

sd_spi = SPI(0,
             sck=Pin(18, Pin.OUT),
             mosi=Pin(19, Pin.OUT),
             miso=Pin(16, Pin.OUT))
sd = sdcard.SDCard(sd_spi, Pin(22))
uos.mount(sd, SD_MOUNTPOINT)
gc.collect()

files = list(filter(JPEG_RE.search, uos.listdir(SLIDE_DIR)))

jpeg = jpegdec.JPEG(graphics)
gc.collect()

try:
    while True:
        for filename in files:
            graphics.set_pen(IF_BLACK)
            graphics.clear()

            jpeg.open_file(SLIDE_DIR + "/" + filename)
            jpeg.decode()

            gc.collect()
            print("START update()", gc.mem_free())
            graphics.update()
            print("END update()", gc.mem_free())

            time.sleep(IMAGE_PAUSE)
except Exception as ex:  ### pylint: disable=broad-except
    print("Unexpected exception:", repr(ex))

uos.unmount(SD_MOUNTPOINT)
