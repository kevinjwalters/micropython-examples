### neopixel-thirty-bug-detector-10.py v1.0
### A program which reproduces the ZIP LED glitching on the micro:bit V2 with ZIP Halo HD and attempts to set a digital output and pause after one by detected reflected light

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

from microbit import Image, button_a, button_b, display, i2c, pin1, pin8, pin9, pin_logo, sleep, temperature
import neopixel
import utime

#import mcp7940


PROGRAM="R10"


gc.collect()

### ZIP Halo HD has 60 RGB LEDs
ZIPCOUNT = 60
BLACK = (0, 0, 0)

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
    sleep(1)
    pin.write_digital(0)


display_image = bytearray(5 * 5)

random.seed(1234)

BASE_R = 32
BASE_G = 4
BASE_B = 4
pattern = [(BASE_R + idx, BASE_G + idx, BASE_B + idx) for idx in list(range(0, 16 + 1)) + list(range(15, 1 - 1, -1))]
last_pat_t = 0
count = 0
normal_light_max = 0
while True:
    for col in pattern:
        #zip_px.fill(BLACK)

        #time_us = utime.ticks_us()
        time_ms = utime.ticks_ms()
        time_s = time_ms // 1000

        zip_px.fill(col)

        ### Make an independent copy
        ##zip_copy = [(r, g, b) for r, g, b in zip_px]  ### pylint: disable=unnecessary-comprehension

        display.show(Image(5, 5, display_image))
        one_ping(start_pin)
        zip_px.show()

        light_lvl_avg = sum([display.read_light_level() for i in range(20)]) / 20.0
        if count > 500:
            if light_lvl_avg > normal_light_max:
                one_ping(detected_pin)
                print(PROGRAM, "FLSH", end=" ")
                ##for idx in range(len(zip_px)):
                ##    if zip_px[idx] != zip_copy[idx]:
                ##        print(idx, zip_px[idx], zip_copy[idx], end=" ")
                ##print()
                utime.sleep(3600)  ### 1 hour sleep in case someone is around to look at device 
        elif count < 500:
            normal_light_max = max(normal_light_max, light_lvl_avg)
        else:  ### exactly 500
            normal_light_max = min(255, round(normal_light_max * 1.25))
            print(PROGRAM, "AMBL", normal_light_max)

        ##discard = button_b.get_presses()
        #discard = button_a.get_presses()
        discard = pin_logo.is_touched()

        if time_s % 1800 == 123:
            gc.collect()
            print(PROGRAM, "GC  ", utime.ticks_ms(), gc.mem_free())
            utime.sleep_ms(1_000)
        elif time_s % 60 == 12:
            print(PROGRAM, "NOGC", utime.ticks_ms(), gc.mem_free())
            utime.sleep_ms(1_000)

        count += 1

