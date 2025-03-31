### neopixel-thirty-bug-timedetector-11.py v1.0
### A program which reproduces the ZIP LED glitching on the micro:bit V2 with ZIP Halo HD and attempts to set a digital output and pause after one by detected by slow show()

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
from utime import ticks_ms, ticks_us, ticks_add, ticks_diff, sleep_ms
from utime import sleep as sleep_s

#import mcp7940


PROGRAM="R11"


gc.collect()

INSPECTION_PAUSE_S = 3600


### ZIP Halo HD has 60 RGB LEDs
ZIPCOUNT = 60
BLACK = (0, 0, 0)

### Estimate of minimum time for a good show() call (2175us for 60)
SHOW_MIN_US = round((ZIPCOUNT * 3 * 8 + 2 * 50) * 1.25 + ZIPCOUNT * 2 + 130)

display.clear()

zip_px = neopixel.NeoPixel(pin8, ZIPCOUNT)
zip_px.fill(BLACK)
zip_px.show()

start_pin = pin1
detected_pin = pin9
start_pin.write_digital(0)
detected_pin.write_digital(0)

def one_ping(pin):
    pin.write_digital(1)
    sleep_ms(1)
    pin.write_digital(0)


display_image = bytearray(5 * 5)

random.seed(1234)

BASE_R = 8
BASE_G = 4
BASE_B = 8
pattern = [(BASE_R, BASE_G + idx, BASE_B) for idx in list(range(0, 28 + 1)) + list(range(27, 1 - 1, -1))]
last_pat_t = 0
count = 0
normal_light_max = 0
start_us = ticks_us()
dur_us = 0
while True:
    for col in pattern:
        #zip_px.fill(BLACK)

        #time_us = utime.ticks_us()
        time_ms = ticks_ms()
        time_s = time_ms // 1000

        zip_px.fill(col)

        ### Make an independent copy
        ##zip_copy = [(r, g, b) for r, g, b in zip_px]  ### pylint: disable=unnecessary-comprehension

        display.show(Image(5, 5, display_image))
        one_ping(start_pin)
        start_us = ticks_us()
        zip_px.show()
        dur_us = ticks_diff(ticks_us(), start_us)
        if dur_us < SHOW_MIN_US:
            print(PROGRAM, "SLOW", dur_us)
            sleep_s(INSPECTION_PAUSE_S)

        #light_lvl_avg = sum([display.read_light_level() for i in range(20)]) / 20.0
        #if count > 500:
        #    if light_lvl_avg > normal_light_max:
        #        one_ping(detected_pin)
        #        print(PROGRAM, "FLSH", end=" ")
        #        ##for idx in range(len(zip_px)):
        #        ##    if zip_px[idx] != zip_copy[idx]:
        #        ##        print(idx, zip_px[idx], zip_copy[idx], end=" ")
        #        ##print()
        #        sleep_s(INSPECTION_PAUSE_S)  ### 1 hour sleep in case someone is around to look at device
        #elif count < 500:
        #    normal_light_max = max(normal_light_max, light_lvl_avg)
        #else:  ### exactly 500
        #    normal_light_max = min(255, round(normal_light_max * 1.25))
        #    print(PROGRAM, "AMBL", normal_light_max)

        ##discard = button_b.get_presses()
        #discard = button_a.get_presses()
        discard = pin_logo.is_touched()

        if time_s % 1800 == 123:
            gc.collect()
            print(PROGRAM, "GC  ", ticks_ms(), gc.mem_free())
            sleep_ms(1_000)
        elif time_s % 60 == 12:
            print(PROGRAM, "NOGC", ticks_ms(), gc.mem_free())
            sleep_ms(1_000)

        count += 1

