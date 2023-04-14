### inkybuspower.py v1.1
### Indicate powering by Pico W's VBUS and supply voltage

### Tested with Inky Frame and Pimoroni Inky Frame specific MicroPython v1.19.16

### copy this file to Inky Frame as main.py

### MIT License

### Copyright (c) 2023 Kevin J. Walters

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

### The busy led is on for USB power and off for battery
### The five button leds are used as a bar graph for voltage
### Button a shows the data on the screen

### Discussed in https://forums.pimoroni.com/t/inky-frame-distinguishing-between-power-sources/19913

### TODO - test this with WiFi active & in-use


import inky_frame

import time
import gc
from machine import Pin, ADC

from picographics import PicoGraphics

IF_I2C_INT_PSRAM_CS_PIN = 3
IF_VSYS_DIV3 = 29
IF_VBUS = 'WL_GPIO2'


### Differentiate between Inky Frame 4, 5.7 and 7.3 based on a battle
### between 10k external pull-ups which differ on Inky Frames
### and the Pico's internal 50-80k pull down
### RFE in https://github.com/pimoroni/pimoroni-pico/issues/726

### Do a pull down test of I2C_INT / PSRAM_CS (GP3)
i2c_int_psram_cs_input = Pin(IF_I2C_INT_PSRAM_CS_PIN, Pin.IN, pull=Pin.PULL_DOWN)
i2c_int_psram_cs_state = i2c_int_psram_cs_input.value()
### Reset the pin to input for I2C_INT or to output for PSRAM_CS
if i2c_int_psram_cs_state:
    _ = Pin(IF_I2C_INT_PSRAM_CS_PIN, Pin.IN, pull=None)
else:
    _ = Pin(IF_I2C_INT_PSRAM_CS_PIN, Pin.OUT, value=0)

### Do a pull down test of SR_LATCH (GP9)
sr_latch_input = Pin(inky_frame.SR_LATCH, Pin.IN, pull=Pin.PULL_DOWN)
sr_latch_state = sr_latch_input.value()
### Reset the pin state to a low output
_ = Pin(inky_frame.SR_LATCH, Pin.OUT, value=0)

if sr_latch_state:
    from picographics import DISPLAY_INKY_FRAME_4 as DISPLAY  ### 4.0"
elif not i2c_int_psram_cs_state:
    from picographics import DISPLAY_INKY_FRAME_7 as DISPLAY  ### 7.3"
else:
    from picographics import DISPLAY_INKY_FRAME as DISPLAY    ### 5.7"

gc.collect()
graphics = PicoGraphics(DISPLAY)
gc.collect()

### Inky Frame display dimensions
IF_WIDTH, IF_HEIGHT = graphics.get_bounds()[:2]


batt_v_pin = Pin(IF_VSYS_DIV3)
batt_v_adc = ADC(IF_VSYS_DIV3)
def batt_v(samples=100):
    total = 0
    ### Trying half of suggestion from
    ### https://forums.raspberrypi.com/viewtopic.php?p=2063326
    batt_v_pin.init(Pin.IN)
    for _ in range(samples):
        total += batt_v_adc.read_u16()
    return total * (3 * 3.3 / 65535) / samples
vbus = Pin(IF_VBUS, Pin.IN)


def add_text(text, x=20, y=IF_HEIGHT-(8+2)*8, color=inky_frame.WHITE, scale=8,
             *,
             outline=None, font='bitmap8'):
    graphics.set_font(font)

    if outline is not None:
        graphics.set_pen(outline)
        for off_x, off_y in ((-scale, -scale), (0, -scale), (scale, -scale),
                             (-scale, 0), (scale, 0),
                             (-scale, scale), (0, scale), (scale, scale)):
            width = IF_WIDTH - 2 * (x + off_x)
            graphics.text(text, x + off_x, y + off_y, width, scale)
    graphics.set_pen(color)
    width = IF_WIDTH - 2 * x
    graphics.text(text, x, y, width, scale)


def button_led_bar_graph(value):
    """Show 0.0 to 5.0 values on the five buttons on Inky Frame."""

    remainder = value
    for button in (inky_frame.button_a,
                    inky_frame.button_b,
                    inky_frame.button_c,
                    inky_frame.button_d,
                    inky_frame.button_e):
        button.led_brightness(max(0.0, min(1.0, remainder)))
        remainder -= 1.0


### rtc is PCF85063A real time clock
inky_frame.rtc.reset()


while True:
    gc.collect()
    voltage = batt_v(samples=1)
    is_usb = bool(vbus.value())

    inky_frame.led_busy.brightness(1 if is_usb else 0)
    button_led_bar_graph(voltage)

    if inky_frame.button_a.is_pressed:
        graphics.set_pen(inky_frame.BLACK)
        graphics.clear()  ### clear is really a fill using set_pen() colour
        add_text(("USB" if is_usb else "BATT") + " {:.3f}V".format(voltage), y=IF_HEIGHT // 2, scale=6)
        graphics.update()

    time.sleep(0.1)
