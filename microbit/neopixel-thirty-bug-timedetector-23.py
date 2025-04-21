### neopixel-thirty-bug-timedetector-23.py v1.0
### ZIP LED glitching on the micro:bit V2 at different pixel counts with persistent way-too-fast show() issue

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


##import array
import gc
##import math
##import os
##import random

from microbit import Image, button_a, button_b, display, i2c, pin1, pin8, pin9, pin15, pin_logo, temperature
import neopixel
from utime import ticks_ms, ticks_us, ticks_add, ticks_diff, sleep_us, sleep_ms
from utime import sleep as sleep_s

#import mcp7940

##import radio
##radio.off()


PROGRAM="R23"


gc.collect()

INSPECTION_PAUSE_S = 3600


### ZIP Halo HD has 60 RGB LEDs
ZIPCOUNT = 60
##MIN_COUNT = 60
##MAX_COUNT = 67
#counts = (60, 61, 62, 63, 64, 65, 66, 67)

full_buf_count = []
oldbufs = 1
buf_size = 256
### This is trying to find maximum pixel count size for certain buffer
### sizes in the underlying WS2812B code
for c in range(1, 59 + 1):
    bytes_for_c = (c * 3 * 8 + 50 * 2) * 2
    bufs = (bytes_for_c - 1) // buf_size + 1
    if bufs != oldbufs:
        full_buf_count.append(c - 1)
        oldbufs = bufs
        if len(full_buf_count) == 7:
            break

counts = tuple(full_buf_count + [60, 63, 64])
print(PROGRAM, "COUNTS", counts)

##reps = 5 * 60 * 200
period_ms = 1 * 60 * 1000
### Try longer run to see if this picks up more problems although not all will be visual
##ZIPCOUNT = 92
##ZIPCOUNT = 95
##ZIPCOUNT = 191
##ZIPCOUNT = 239
BLACK = (0, 0, 0)

NEOPIXEL_PIN = pin8

##display.clear()
display.off()

init_px = neopixel.NeoPixel(NEOPIXEL_PIN, ZIPCOUNT)
init_px.fill(BLACK)
init_px.show()


### Using pin9 which is only free on the V2
start_pin = pin1
detected_pin = pin9
end_pin = pin15
start_pin.write_digital(0)
detected_pin.write_digital(0)
end_pin.write_digital(0)


### This takes about 442-445ms at 13_700
def some_maths(reps=13_700):
    number = 1.2345
    for _ in range(reps):
        number = number * 1.001 - 1.001

t1_us = ticks_us()
some_maths()
t2_us = ticks_us()
print(PROGRAM, "MATH", ticks_diff(t2_us, t1_us))


def calc_show_min_us(pix):
    ### Estimate of minimum time for a good show() call (2175us for 60)
    #SHOW_MIN_US = round((ZIPCOUNT * 3 * 8 + 2 * 50) * 1.25 + ZIPCOUNT * 2 + 95)
    ### This should be 1.25ms but 1.20 works better for some reason

    ### More hacks, for 10 183us is common and 313us is common,
    ### MicroPython timing iffy for these small amounts?
    if len(pix) <= 10:
        return 150

    return round((len(pix) * 3 * 8 + 2 * 50) * 1.20  + 190)

def set_ascending(pix):
    ### GRB is a common order in the wire protocol
    for idx in range(len(pix)):
        triple_idx = 3 * idx
        pix[idx] = ((triple_idx + 1) % 256, triple_idx % 256, (triple_idx + 2) % 256)


def pause_ms(p_ms, spin_cpu):
    if spin_cpu:
        sleep_us(p_ms * 1000)
    else:
        sleep_ms(p_ms)


count = 0
start_us = ticks_us()
dur_us = 0

baseline_us = [0] * 16

while True:
    for zipcount in counts:
        for spin in (False, True):
            #print(PROGRAM, "ZIPCOUNT", zipcount)
            zip_px = neopixel.NeoPixel(NEOPIXEL_PIN, zipcount)
            set_ascending(zip_px)
            show_min_us = calc_show_min_us(zip_px)

            for b_idx in range(len(baseline_us)):
                gc.collect()
                start_us = ticks_us()
                zip_px.show()
                ##t2_us = ticks_us(
                baseline_us[b_idx] = ticks_diff(ticks_us(), start_us)

            baseline_us.sort()
            ### 90% of (min(IQR) - 20us)
            show_min_us = round((min(baseline_us[4:12]) - 20) * 0.9)
            #print(PROGRAM, "SHMN", show_min_us, baseline_us)

            gc.collect()
            slowcount = 0
            totalcount = 0
            #for rep in range(reps):
            start_ms = ticks_ms()
            while ticks_diff(ticks_ms(), start_ms) < period_ms:
                pause_ms(2, spin)
                t1_us = ticks_us()
                zip_px.show()
                t2_us = ticks_us()
                pause_ms(2, spin)
                dur_us = ticks_diff(t2_us, t1_us)
                if dur_us < show_min_us:
                    if slowcount % 100_000 == 0:
                        pass
                        #print(PROGRAM, "SLOW", dur_us, "vs", show_min_us, "at", rep)
                    slowcount += 1
                elif dur_us < 200:
                    ### Somehow managed to get micro:bit into a very fast broken mode
                    ### where hitting reset button was required to fix MicroPython!
                    print(PROGRAM, "BGRD", dur_us)
                    t1_us = ticks_us()
                    some_maths()
                    t2_us = ticks_us()
                    print(PROGRAM, "MATH", ticks_diff(t2_us, t1_us))
                    sleep_s(3600)
                totalcount += 1

            gc.collect()
            init_px.show()  ### clear all 60 ZIP LEDs
            print(PROGRAM, "SUMM", zipcount, slowcount, totalcount, "sleep_us" if spin else "sleep_ms")

    count += 1
