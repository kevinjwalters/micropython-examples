### neopixel-thirty-bug-colourcycle-26.py v1.0
### cycle through colours slowly to allow for visual check - buttons for sync

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

### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT

### Uses https://github.com/salty-muffin/micropython-mcp7940/blob/master/mcp7940.py

### This is to explore the issue raised in
### https://github.com/microbit-foundation/micropython-microbit-v2/issues/227
### and
### https://github.com/lancaster-university/codal-microbit-v2/issues/475
### and perhaps dramatically reduced ("fixed") by
### https://github.com/lancaster-university/codal-nrf52/issues/59

### This cycles through colours - it is intended to be used on several devices simultaneously
### with the buttons allowing for the sequences to be synchronised
### Any visual anomalies will hopefully be obvious to a casual viewer.

##import array
import gc
##import math
import os
import sys
##import random

from microbit import Image, button_a, button_b, display, i2c, pin1, pin8, pin9, pin15, pin_logo, temperature
import neopixel
from utime import ticks_ms, ticks_us, ticks_add, ticks_diff, sleep_us, sleep_ms
from utime import sleep as sleep_s

#import mcp7940

### Radio uses interrupts
import radio

PROGRAM="R26"

gc.collect()
sleep_s(20)   ### allow some time to catch it in case it crashes interpreter

### ZIP Halo HD has 60 RGB LEDs
ZIPCOUNT = 60
BLACK = (0, 0, 0)
NEOPIXEL_PIN = pin8
BUTTON_SHIFT_MS = 50
INSPECTION_PAUSE_S = 3600

### ZX Spectrum order
colours = (( 0, 0, 16),
           (10, 0,  0),
           ( 7, 0, 12),
           ( 0, 8,  0),
           ( 0, 7, 12),
           ( 9, 7,  0),
           ( 6, 6,  6),
           ( 0, 0,  0))
counts = (1, 7, 54, 55, 60, 256)
period_ms = 5 * 1000   ### two seconds



### Display uses interrupts
display.on()
display.show(Image("00011\n22233\n44455\n66677\n88899"))


neopixel.NeoPixel(NEOPIXEL_PIN, ZIPCOUNT)

init_px = neopixel.NeoPixel(NEOPIXEL_PIN, ZIPCOUNT)
init_px.fill(BLACK)
init_px.show()

print(PROGRAM, "SVMP", sys.version)

### Look for the zero byte file which identifies different ZIP Halo HDs
print(PROGRAM, "KZHH", *[s for s in os.listdir() if s.startswith("zhh-")])

### This takes about 442-445ms at 13_700 on a V2 if everything is okay
def some_maths(reps=13_700):
    number = 1.2345
    for _ in range(reps):
        number = number * 1.001 - 1.001

t1_us = ticks_us()
some_maths()
t2_us = ticks_us()
print(PROGRAM, "MATH", ticks_diff(t2_us, t1_us), "us")


### not in use
def calc_show_min_us(pix):
    ### Estimate of minimum time for a good show() call based
    ### on WS2812B using 128 sample buffers, minimum 2
    bufcnt = max(2,
                 math.ceil((len(pix) * 3 * 8 + 2 * 50) / 128))
    return bufcnt * 128 * 1.25


totalcount = 0
while True:
    for zipcount in counts:
        for colour in colours:
            zip_px = neopixel.NeoPixel(NEOPIXEL_PIN, zipcount)
            zip_px.fill(colour)
            zip_px.show()
            start_ms = ticks_ms()
            adjust_ms = 0
            while ticks_diff(ticks_ms(), start_ms) < period_ms + adjust_ms:
                ap = button_a.get_presses()
                bp = button_b.get_presses()
                adjust_ms += bp * BUTTON_SHIFT_MS - ap * BUTTON_SHIFT_MS
                if pin_logo.was_touched():
                    print(PROGRAM, "PAWS")
                    sleep_s(INSPECTION_PAUSE_S)
            totalcount += 1
