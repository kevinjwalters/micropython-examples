### mb-soil-moisture.py v1.0
### Show soil moisture on micro:bit display using resistive and capacitive sensors

### Tested with BBC micro:bit v1.5 and MicroPython v1.9.2-34-gd64154c73

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


### This is a micro:bit version of
### https://github.com/kevinjwalters/circuitpython-examples/blob/master/pico/soil-moisture.py
### featured in
### https://www.instructables.com/Soil-Moisture-Sensing-With-the-Maker-Pi-Pico/

import utime
from microbit import display, pin0, pin1, sleep

RES_PIN = pin0
CAP_PIN = pin1

### Values for (dry, wet) based on values from CircuitPython version
RES_RANGE = (1023, 156)
CAP_RANGE = (593, 343)

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


def adc_to_moisture(raw_adc, arid_value, sodden_value):
    """Convert a micro:bit 0-1024 ADC value into a moisture percentage
       using crude linear model."""

    a_lower = min(arid_value, sodden_value)
    a_range = abs(sodden_value - arid_value)
    inverted = arid_value > sodden_value

    fraction = (raw_adc - a_lower) / a_range
    if inverted:
        fraction = 1.0 - fraction

    return min(100.0, max(0.0, fraction * 100.0))


def get_res_moisture():
    return adc_to_moisture(RES_PIN.read_analog(), *RES_RANGE)

def get_cap_moisture():
    return adc_to_moisture(CAP_PIN.read_analog(), *CAP_RANGE)


scroll_delay=250   ### default is 150ms

while True:
    ### Read both values and display them slowly
    res_perc = get_res_moisture()
    cap_perc = get_cap_moisture()
    display.scroll("R " + str(round(res_perc)),
                   delay=scroll_delay)
    sleep(2000)
    display.scroll("C " + str(round(cap_perc)),
                   delay=scroll_delay)
    sleep(2000)

    ### Now show both values on bar charts for 20 seconds
    ### but only read fresh capacitive values
    start_time_ms = utime.ticks_ms()
    while True:
        cap_perc = get_cap_moisture()
        bar_chart(res_perc, (0, 1))  ### Left two columns
        bar_chart(cap_perc, (3, 4))  ### Right two columns
        now_time_ms = utime.ticks_ms()
        if utime.ticks_diff(now_time_ms, start_time_ms) > 20000:
            break
        sleep(500)
