### neopixel-thirty-bug-timedetector-13.py v1.0
### A program which reproduces the ZIP LED glitching on the micro:bit V2 with ZIP Halo HD with numerically ascending channgel values and sets a digital output and pause after one by detected by slow show()

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
### A bright flash is likely to happen every 5-60 minutes
### An A5 white piece of paper made into a crude cone should reflect
### enough light back to get a reading between 30-120


import array
import gc
import math
import os
import random

from microbit import Image, button_a, button_b, display, i2c, pin1, pin8, pin9, pin_logo, temperature
import neopixel
from utime import ticks_ms, ticks_us, ticks_add, ticks_diff, sleep_us, sleep_ms
from utime import sleep as sleep_s

#import mcp7940


PROGRAM="R13"


gc.collect()

INSPECTION_PAUSE_S = 3600


### ZIP Halo HD has 60 RGB LEDs
ZIPCOUNT = 60
MIN_COUNT = 60
MAX_COUNT = 67
### Try longer run to see if this picks up more problems although not all will be visual
##ZIPCOUNT = 92
##ZIPCOUNT = 95
##ZIPCOUNT = 191
##ZIPCOUNT = 239
BLACK = (0, 0, 0)

NEOPIXEL_PIN = pin8
print(PROGRAM, "ZIPCOUNT", ZIPCOUNT)

display.clear()

zip_px = neopixel.NeoPixel(NEOPIXEL_PIN, ZIPCOUNT)
zip_px.fill(BLACK)
zip_px.show()

start_pin = pin1
detected_pin = pin9
start_pin.write_digital(0)
detected_pin.write_digital(0)


def calc_show_min_us(pix):
    ### Estimate of minimum time for a good show() call (2175us for 60)
    #SHOW_MIN_US = round((ZIPCOUNT * 3 * 8 + 2 * 50) * 1.25 + ZIPCOUNT * 2 + 95)
    ### This should be 1.25ms but 1.20 works better for some reason
    return round((len(pix) * 3 * 8 + 2 * 50) * 1.20  + 190)

def set_ascending(pix):
    ### GRB is a common order in the wire protocol
    for idx in range(len(pix)):
        triple_idx = 3 * idx
        pix[idx] = ((triple_idx + 1) % 256, triple_idx % 256, (triple_idx + 2) % 256)


def one_ping(pin):
    pin.write_digital(1)
    sleep_us(400)
    pin.write_digital(0)


display_image = bytearray(5 * 5)

count = 0
normal_light_max = 0
start_us = ticks_us()
dur_us = 0
last_d_idx = -1
show_min_us = calc_show_min_us(zip_px)
set_ascending(zip_px)

while True:
    time_ms = ticks_ms()
    time_s = time_ms // 1000
    d_idx = time_s % 25
    if d_idx != last_d_idx:
        display_image[d_idx] = 7
        display_image[(d_idx - 1) % 25] = 0
        last_d_idx = d_idx
        display.show(Image(5, 5, display_image))

    one_ping(start_pin)
    start_us = ticks_us()
    zip_px.show()
    dur_us = ticks_diff(ticks_us(), start_us)
    if dur_us < show_min_us:
        one_ping(detected_pin)
        print(PROGRAM, "SLOW", dur_us)
        sleep_s(INSPECTION_PAUSE_S)

    ### Logo changes the number of pixels
    if pin_logo.is_touched():
        new_count = len(zip_px) + 1
        if new_count > MAX_COUNT:
            new_count = MIN_COUNT
        print(PROGRAM, "PXCT", new_count)
        display.scroll(new_count)
        zip_px = neopixel.NeoPixel(pin8, new_count)
        show_min_us = calc_show_min_us(zip_px)
        set_ascending(zip_px)

    #if time_s % 1800 == 123:
    #    gc.collect()
    #    print(PROGRAM, "GC  ", ticks_ms(), gc.mem_free())
    #    sleep_ms(1_000)
    #elif time_s % 60 == 12:
    #    print(PROGRAM, "NOGC", ticks_ms(), gc.mem_free())
    #    sleep_ms(1_000)
    #elif time_s % 60 == 42:
    #    sleep_ms(random.randint(1, 66))

    count += 1
