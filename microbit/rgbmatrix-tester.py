### Micro:bit 8x8 RGB WS2812B LED tester v1.0

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


### Button A restart the test sequence
### Button B changes mode
### (cycling tests, four RGB LEDs illuminated, all illuminated split colours)


import time

import neopixel
from microbit import button_a, button_b
from microbit import pin8


PIXEL_COUNT = 8 * 8
LONGTIME_S = 3600
PERIOD_S = 5
LEVELS = (0, 6, 22, 58, 255)
WORD_IDX = tuple(tuple(range(8,  8 + 4)) +
                 tuple(range(24, 24 + 2)) +
                 tuple(range(48, 48 + 7)))
BLACK = (0, 0, 0)
pixels = neopixel.NeoPixel(pin8, PIXEL_COUNT)


POWERTEST_MODE = 0
SPLIT_MODE = 1
FOURC_MODE = 2
MODE_COUNT = 3
mode = POWERTEST_MODE


def sleep_or_term(dur_s):
    start_ms = time.ticks_ms()
    dur_ms = dur_s * 1000.0
    while time.ticks_diff(time.ticks_ms(), start_ms) < dur_ms:
        if button_a.was_pressed() or button_b.is_pressed():
            return True

    return False


while True:
    restart = False

    if button_b.was_pressed():
        mode = (mode + 1) % MODE_COUNT

    if mode == POWERTEST_MODE:
        ### Set a few pixels to represent words
        ### at various brightness levels
        for level in LEVELS:
            print("Few", level)
            pixels.fill(BLACK)
            col = (level, level, level)
            for idx in WORD_IDX:
                pixels[idx] = col
            pixels.show()

            if sleep_or_term(PERIOD_S):
                restart = True
                break

        if restart:
            continue

        ### Set all pixels to various brightness levels
        for level in LEVELS:
            print("All", level)
            col = (level, level, level)
            pixels.fill(col)
            pixels.show()

            if sleep_or_term(PERIOD_S):
                restart = True
                break

    elif mode == SPLIT_MODE:
        for idx in range(PIXEL_COUNT // 2):
            pixels[idx] = (0, 87//8, 183//6)
            pixels[idx + PIXEL_COUNT // 2] = (255//10, 215//10, 0)
        pixels.show()

        sleep_or_term(LONGTIME_S)

    elif mode == FOURC_MODE:
        pixels.fill(BLACK)
        for idx in (12, 13, 21, 22):
            pixels[idx] = (100, 30, 0)
        pixels.show()
        sleep_or_term(LONGTIME_S)
