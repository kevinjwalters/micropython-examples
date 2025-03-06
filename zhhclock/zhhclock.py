### zhhlocky.py v1.0
### A clock and stopwatch with many backgrounds for Kitronik ZIP Halo HD

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

### TODO store (magic number, background, mode) in the SRAM of RTC?

### Controls
### logo to change mode, this seems obvious.
### changing mode could leave things running, like stopwatch
### short logo press to change to new mode
### long press to change background?


import gc
import os

from microbit import Image, button_a, button_b, display, i2c, pin8, pin_logo, sleep, temperature
from micropython import const
import neopixel
import utime

import mcp7940

from zc_comboclock import ComboClock
from zc_bg import HaloBackground
from zc_bg_blank import Blank
from zc_bg_flag import Flag
#from zc_bg_rotatingrainbow import RotatingRainbow
from zc_bg_fallingrainbow import FallingRainbow
#from zc_bg_digitalrain  import DigitalRain
from zc_bg_pendulum  import Pendulum
#from zc_bg_brightnesstest import BrightnessTest
#from zc_bg_larsonscanner import LarsonScanner
#from zc_bg_temperature import Temperature
from zc_utils import HOUR, MINUTE, SECOND


try:
    os.size("config.py")  ### For absent file this will OSError: [Errno 2] ENOENT
    import config
except OSError:
    pass
try:
    THIS_MICROBIT_CLOCK_PPM = config.THIS_MICROBIT_CLOCK_PPM
except (NameError, AttributeError):
    THIS_MICROBIT_CLOCK_PPM = 0
try:
    THIS_ZHH_RTC_PPM = config.THIS_ZHH_RTC_PPM
except (NameError, AttributeError):
    THIS_ZHH_RTC_PPM = 0

### MCP7940 fine trim is multiples of 2 cycles per minute for 32.768kHz crystal
PPM_TO_TRIM_CONV = 32768 * 60 / (2 * 1000 * 1000)

### Zip Halo HD has 60 RGB LEDs
ZIPCOUNT = 60
BLACK = (0, 0, 0)
MCP_POR_TIME = (2000, 1, 1, 0, 0, 0, 0, 0)

VERY_LONG_PRESS_DURATION_MS = 2000
LONG_PRESS_DURATION_MS = 1000
SHORT_PRESS_DURATION_MS = 175
PAUSE_AFTER_BUTTON_MS = 200

### MicroPython on micro:bit does not have these methods used by MCP7940
class EnhancedI2C:
    def __init__(self, i2c_):
        self._i2c = i2c_

    ### pylint: disable=
    def readfrom_mem(self, addr, memaddr, nbytes, *, addrsize=8):
        self._i2c.write(addr, bytes([memaddr]))
        return self._i2c.read(addr, nbytes)

    ##def readfrom_mem_into(self, addr, memaddr, buf, *, addrsize=8):
    ##    raise NotImplementedError

    def writeto_mem(self, addr, memaddr, buf, *, addrsize=8):
        self._i2c.write(addr, bytes([memaddr]) + buf)


ei2c = EnhancedI2C(i2c)
mcp = mcp7940.MCP7940(ei2c)
print("MCP", mcp.time)

zip_px = neopixel.NeoPixel(pin8, ZIPCOUNT)
zip_px.fill(BLACK)
zip_px.show()

if False:
    sleep(35 * 1000)

display_image = [0] * (5 * 5)

microbit_bri_conv = 9.0 / 255.0
ORD_ZERO = ord("0")
def show_display_image():
    ### This converts integer (0..255) array into the MicroPython
    ### text representation of an image
    img = ":".join(["".join([chr(ORD_ZERO
                                 + round(x * microbit_bri_conv))
                             for x in display_image[0+offset:5+offset]]) for offset in range(0, 25, 5)])
    display.show(Image(img))

show_display_image()

gc.collect()

### Remove the current_time setting
clock = ComboClock(mcp,
                   rtc_clock_drift_ppm=THIS_ZHH_RTC_PPM,
                   rtc_trim_conv=PPM_TO_TRIM_CONV,
                   mp_clock_drift_ppm=THIS_MICROBIT_CLOCK_PPM,
                   current_time=(2025, 2, 26,  9, 30, 0,  2, 57))

stopwatch_hmsms = [0, 0, 0, 0.0]

mode_idx = 0
mode = (("clock",
         "stopwatch",
         "time set"))
ROTATE_MODES = 2
MODE_CLOCK = const(0)
MODE_STOPWATCH = const(1)
MODE_TIME_SET = const(2)



background_idx = 1
background = (Blank(zip_px, display_image),
              Flag(zip_px, display_image),
              #RotatingRainbow(zip_px, display_image),
              FallingRainbow(zip_px, display_image),
              #DigitalRain(zip_px, display_image),
              Pendulum(zip_px, display_image),
              #BrightnessTest(zip_px, display_image),
              #LarsonScanner(zip_px, display_image),
              #Temperature(zip_px, display_image, {"function": temperature})
              )
gc.collect()

counter = 0
bg = background[background_idx]
bg.start(*clock.time_with_ms_and_ticks)
bg_displayed = bg.displayed
updates = 0
time_set_change = 0  ### 3-6 for hour minute second and 10 for am/pm
while True:
    if mode_idx != MODE_STOPWATCH:
        for idx in range(len(display_image)):
            display_image[idx] = 0
    zip_px.fill(BLACK)

    ### TODO - this is resyncing for RTC clock changes
    ### how can i inhibit that but retain ms for flashing? ticks ?
    rtc_time, ss_ms, ticks_ms = clock.time_with_ms_and_ticks
    if mode_idx == MODE_CLOCK:
        updates = bg.render(rtc_time, ss_ms, ticks_ms)

    h_idx = m_idx = s_idx = ms_idx = None
    display_char = None
    if mode_idx == MODE_STOPWATCH:
        time_ms = clock.stopwatch_time_ms()
        stopwatch_hmsms[:] = [time_ms // 3600000,
                              time_ms // 60000 % 60,
                              time_ms // 1000 % 60,
                              time_ms % 1000]
        h_idx = int(stopwatch_hmsms[0]) * ZIPCOUNT // 12 % ZIPCOUNT
        m_idx = int(stopwatch_hmsms[1]) * ZIPCOUNT // 60
        s_idx = int(stopwatch_hmsms[2]) * ZIPCOUNT // 60
        ms_idx = int(stopwatch_hmsms[3] * ZIPCOUNT // 1000)
    elif mode_idx == MODE_CLOCK:
        ### pylint: disable=superfluous-parens
        if not (bg_displayed & (1 << HOUR)):
            h_idx = rtc_time[HOUR] * ZIPCOUNT // 12 % ZIPCOUNT
        if not (bg_displayed & (1 << MINUTE)):
            m_idx = rtc_time[MINUTE] * ZIPCOUNT // 60
        if not (bg_displayed & (1 << SECOND)):
            s_idx = rtc_time[SECOND] * ZIPCOUNT // 60
    elif mode_idx == MODE_TIME_SET:
        flash_on = ss_ms > 500.0
        if time_set_change != HOUR or flash_on:
            h_idx = rtc_time[HOUR] * ZIPCOUNT // 12 % ZIPCOUNT
        display_char = ("p" if rtc_time[HOUR] >= 12 else "a")
        if time_set_change != MINUTE or flash_on:
            m_idx = rtc_time[MINUTE] * ZIPCOUNT // 60
        if time_set_change != SECOND or flash_on:
            s_idx = rtc_time[SECOND] * ZIPCOUNT // 60

    if h_idx is not None:
        bri = min(255, zip_px[h_idx][0] + 16) if zip_px[h_idx][0] < 8 else 0
        zip_px[h_idx] = (bri, zip_px[h_idx][1], zip_px[h_idx][2])
    if m_idx is not None:
        bri = min(255, zip_px[m_idx][1] + 16) if zip_px[m_idx][1] < 8 else 0
        zip_px[m_idx] = (zip_px[m_idx][0], bri, zip_px[m_idx][2])
    if s_idx is not None:
        bri = min(255, zip_px[s_idx][2] + 16) if zip_px[s_idx][2] < 8 else 0
        zip_px[s_idx] = (zip_px[s_idx][0], zip_px[s_idx][1], bri)
    if ms_idx is not None:
        bri = (min(255, zip_px[ms_idx][0] + 32 if clock.stopwatch_running else 24) if zip_px[ms_idx][0] < 8 else 0)
        zip_px[ms_idx] = (bri, zip_px[ms_idx][1], zip_px[ms_idx][2])
    updates |= HaloBackground.HALO_CHANGED

    if display_char is not None:
        display.show(display_char)
    elif mode_idx == MODE_CLOCK:
        show_display_image()
    zip_px.show()

    if button_b.get_presses():
        wait = False
        if mode_idx == MODE_STOPWATCH and not clock.stopwatch_running:
            clock.stopwatch_reset()
            wait = True
        elif mode_idx == MODE_TIME_SET:
            time_set_change += 1
            if time_set_change > SECOND:
                time_set_change = HOUR
            print(time_set_change)
            wait = True
        if wait:
            while button_b.is_pressed():
                pass

    if button_a.get_presses():
        wait = False
        if mode_idx == MODE_STOPWATCH:
            if clock.stopwatch_running:
                clock.stopwatch_stop()
            else:
                clock.stopwatch_start()
            wait = True
        elif mode_idx == MODE_TIME_SET:
            wrap = 24 if time_set_change == HOUR else 60
            rtc_time, ss_ms, ticks_ms = clock.time_with_ms_and_ticks
            upd_rtc_time = list(rtc_time)
            upd_rtc_time[time_set_change] = (rtc_time[time_set_change] + 1) % wrap
            clock.set_rtc(upd_rtc_time)
            wait = True
        if wait:
            while button_a.is_pressed():
                pass

    if pin_logo.is_touched():
        d_char = ""
        new_char = ""
        t1_ms = t2_ms = utime.ticks_ms()
        threshold = 1.0
        while threshold > 0.5:
            if mode_idx != MODE_TIME_SET:
                if utime.ticks_diff(t2_ms, t1_ms) > VERY_LONG_PRESS_DURATION_MS:
                    new_char = "t"
                elif utime.ticks_diff(t2_ms, t1_ms) > LONG_PRESS_DURATION_MS:
                    new_char = mode[(mode_idx + 1 ) % len(mode)][0]
                elif utime.ticks_diff(t2_ms, t1_ms) > SHORT_PRESS_DURATION_MS:
                    new_char = "b"  ### next background

            if new_char != d_char:
                display.show(new_char)
                d_char = new_char
            sleep(25)
            t2_ms = utime.ticks_ms()
            threshold = threshold * 0.9 + 0.1 * int(pin_logo.is_touched())

        if mode_idx == MODE_TIME_SET:
            clock.sync_clocks()
            mode_idx = MODE_CLOCK
        elif utime.ticks_diff(t2_ms, t1_ms) < LONG_PRESS_DURATION_MS:
            background_idx = (background_idx + 1 ) % len(background)
            print("NEWBACKGROUND", background_idx)  ### TODO remove
            bg.stop()
            gc.collect()
            bg = background[background_idx]
            bg.start(rtc_time, ss_ms, ticks_ms)
            bg_displayed = bg.displayed
        elif utime.ticks_diff(t2_ms, t1_ms) < VERY_LONG_PRESS_DURATION_MS:
            mode_idx = (mode_idx + 1 ) % ROTATE_MODES
            print("NEWMODE", mode_idx)  ### TODO remove
        else:
            mode_idx = MODE_TIME_SET
            time_set_change = HOUR

        ### TODO - is this still needed?
        #sleep(PAUSE_AFTER_BUTTON_MS)  ### 200ms to stop another subsequent mode change

    ### TODO - do i need a min loop time?
    ## sleep(180)

    counter = counter + 1
