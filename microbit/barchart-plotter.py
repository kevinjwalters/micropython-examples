### bargraph-plotter.py v1.0
### Plot analogue inputs on the micro:bit display

### Tested with BBC micro:bit v1.5 and MicroPython v1.9.2-34-gd64154c73
### on a Cytron Edu:bit

### MIT License

### Copyright (c) 2021 Kevin J. Walters

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


import utime
from microbit import display, pin1

### The BBC micro:bit 5x5 LED display can show ten
### brightness levels in MicroPython 0-9
### (The underlying DAL supports a wider range 0-255)
MAX_BRIGHTNESS = 9


def bar_chart(value,
              columns=(0, 1, 2, 3, 4),
              *, max_value=100):
    """Draw a vertical bar chart based on percentage value
       using variable brightness levels on display."""

    ### Nine brightness levels on 5x5 LED matrix equates
    ### to 45 pixel steps - start at bottow row (no 4) and
    ### light pixels until value px_steps value is reached
    px_steps = round(value * 45 / max_value)
    for y in range(4, -1, -1):
        for x in columns:
            ### The min/max here limit values from 0 to 9
            display.set_pixel(x, y,
                              min(MAX_BRIGHTNESS, max(0, px_steps)))
        px_steps -= MAX_BRIGHTNESS


def screen_scroll(direction="left"):
    if direction == "left":
        src_disp_x = 1
        col_range = range(0, 4)
    elif direction == "right":
        src_disp_x = -1
        col_range = range(4, 0, -1)
    else:
        raise ValueError("direction must be left or right: " + direction)

    for x in col_range:
        for y in range(5):
            brightness = display.get_pixel(x + src_disp_x, y)
            display.set_pixel(x, y, brightness)

total = 0
samples = 1

while True:
    ### Set far right column to average value (total/samples)
    bar_chart(total, columns=(4,), max_value=1023 * samples)

    ### Collect analogue values for 100 milliseconds ensuring
    ### at least one is collected
    total = 0
    samples = 0
    start_time_ms = utime.ticks_ms()
    while True:
        total += pin1.read_analog()
        samples += 1
        if utime.ticks_diff(utime.ticks_ms(), start_time_ms) > 100:
            break

    ### Scroll pixels to the left
    screen_scroll()
