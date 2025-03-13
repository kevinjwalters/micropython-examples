### neopixel-thirty-bug-repro-8.py v1.0
### A program which reproduces the ZIP LED glitching on the micro:bit V2 with ZIP Halo HD and attempts to pause after one by detected reflected light

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

### A bright flash is likely to happen every 5-60 minutes
### Place 3-4cm away from an A5 piece of paper which should reflect
### enough light back to get a reading between 30-120


import array
import gc
import math
import os
import random

from microbit import Image, button_a, button_b, display, i2c, pin8, pin_logo, sleep, temperature
import neopixel
import utime

#import mcp7940


PROGRAM="R8"


gc.collect()

### ZIP Halo HD has 60 RGB LEDs
ZIPCOUNT = 60
BLACK = (0, 0, 0)

display.clear()

zip_px = neopixel.NeoPixel(pin8, ZIPCOUNT)
zip_px.fill(BLACK)
zip_px.show()

display_image = bytearray(5 * 5)

random.seed(1234)

MAX_R = 40
MAX_G = 10
MAX_B = 15
pattern = [BLACK]
last_pat_t = 0
count = 0
normal_light_max = 0
while True:
    zip_px.fill(BLACK)

    time_us = utime.ticks_us()
    time_ms = utime.ticks_ms()
    time_s = time_ms // 1000

    if last_pat_t != time_ms:
        last_pat_t = time_ms
        _ = pattern.pop(0)

    chan = time_s % 3
    while len(pattern) < ZIPCOUNT:
        pattern.append((MAX_R,
                       MAX_G if chan == 1 else 0,
                       MAX_B if chan == 2 else 0))

    for idx in range(ZIPCOUNT):
        zip_px[idx] = pattern[idx]
        if idx < 25:
            display_image[idx] = zip_px[idx][0] % 10

    ### Make an independent copy
    zip_copy = [(r, g, b) for r, g, b in zip_px]  ### pylint: disable=unnecessary-comprehension

    display.show(Image(5, 5, display_image))
    zip_px.show()

    light_lvl_avg = sum([display.read_light_level() for i in range(20)]) / 20.0
    if count < 500:
        normal_light_max = max(normal_light_max, light_lvl_avg)
    elif count == 500:
        normal_light_max = min(255, round(normal_light_max * 1.25))
        print(PROGRAM, "AMBL", normal_light_max)
    else:
        if light_lvl_avg > normal_light_max:
            print(PROGRAM, "FLSH", end=" ")
            for idx in range(len(zip_px)):
                if zip_px[idx] != zip_copy[idx]:
                    print(idx, zip_px[idx], zip_copy[idx], end=" ")
            print()
            utime.sleep(3600)  ### 1 hour sleep in case someone is around to look at device

    discard = button_b.get_presses()
    discard = button_a.get_presses()
    discard = pin_logo.is_touched()

    if time_s % 1800 == 123:
        gc.collect()
        print(PROGRAM, "GC  ", utime.ticks_ms(), gc.mem_free())
        utime.sleep_ms(1_000)
    elif time_s % 60 == 12:
        print(PROGRAM, "NOGC", utime.ticks_ms(), gc.mem_free())
        utime.sleep_ms(1_000)

    count += 1

