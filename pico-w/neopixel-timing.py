### neopixel-timing v1.0
### Test patterns with variation of processor clock speed and WS2812B timing

### copy this file to Pi Pico / Pi Pico 2 as main.py

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
### IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANholdTIES OF MERCHANTABILITY,
### FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
### AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
### LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
### OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
### SOFTWARE.

### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


import os
import time

import machine
import neopixel

PIXEL_COUNT = 8
PIXEL_PIN = 2

### This might be the right place to get the default from?
### https://github.com/micropython/micropython-lib/blob/master/micropython/drivers/led/neopixel/neopixel.py
### (400, 850, 800, 450)
DEFAULT_TIMING = (400, 850, 800, 450)
C_TIMING1 = [sum(x) for x in zip(DEFAULT_TIMING, (-50, +50 , 0, 0))]
REPEAT = 1

print("Machine:", os.uname().machine)
print("Release:", os.uname().machine)
print("Version:", os.uname().version)
print("Freq:", machine.freq(), f"({machine.freq()/1e6} MHz)")
print()


def pattern1(px, r_o=None, g_o = None, b_o = None):
    rgb_val = [0] * 3
    for idx in range(len(px)):
        rgb_val[0] = (idx * 8 + 1) % 256 if r_o is None else r_o
        rgb_val[1] = 0b0101010101 if g_o is None else g_o
        rgb_val[2] = 0 if b_o is None else b_o
        px[idx] = rgb_val


time.sleep(10)

while True:
    t_idx = 1

    for frequency in (125_000_000, 150_000_000, 160_000_000):
        machine.freq(frequency)

        print(f"Test {t_idx} default timing at clock {machine.freq()} MHz")
        pixels = neopixel.NeoPixel(machine.Pin(PIXEL_PIN), PIXEL_COUNT)
        pattern1(pixels, b_o=0)
        for _ in range(REPEAT):
            pixels.write()
            time.sleep_ms(1)
            pixels.write()
            time.sleep_ms(500)

        t_idx += 1
        print()
        time.sleep(10)

        print(f"Test {t_idx} custom timing ({C_TIMING1}) at clock {machine.freq()} MHz")
        pixels = neopixel.NeoPixel(machine.Pin(PIXEL_PIN), PIXEL_COUNT,
                                   timing=C_TIMING1)
        pattern1(pixels, b_o=32)
        for _ in range(REPEAT):
            pixels.write()
            time.sleep_ms(1)
            pixels.write()
            time.sleep_ms(500)

        t_idx += 1
        print()
        time.sleep(10)
