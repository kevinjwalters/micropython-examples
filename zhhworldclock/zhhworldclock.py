### zhhworldclock.py v1.2
### A clock and stopwatch for multiple clocks synchronised with radio with many backgrounds for Kitronik ZIP Halo HD

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
### Logo (press)
###   short press to change background, longer press to switch back and forth
###   to stopwatch, very long press to set the time
### Button A (left)
###   start/stop stopwatch, increment value in time set mode
### Button B (right)
###   reset stopwatch, alter next parameter in time set mode


### First clock numbered 1 will be master and will still allow time to be set
### It will broadcast at startup for a minute and then on the hour
### Slaved clocks will listen at startup for a minute and then near the hour for updates and
### not allow local times changes
### if clock time needs changing then best way is to change it and then power cycle rest via switches

### Useful summary of MicroPython timezone blues https://github.com/orgs/micropython/discussions/12378

### TODO look at logo presses for getting out of stopwatch mode
### - background changes aren't needed/feasible there

### TODO fix up all the backgrounds to fit in with new variable brightness regime


import gc


from microbit import Image, button_a, button_b, display, i2c, pin1, pin8, pin_logo, temperature
import microbit
import neopixel
import radio
from utime import ticks_ms, ticks_us, ticks_diff, ticks_add, sleep_ms

from mcp7940_tiny import MCP7940

from datecalc import DateCalc

from zc_comboclock import ComboClock
from zc_clockcomms import ClockComms, MsgTimeWms

from zc_bg_blank import Blank
from zc_bg_milliseconds import Milliseconds
#from zc_bg_digitalrain  import DigitalRain
#from zc_bg_pendulum  import Pendulum
#from zc_bg_fallingrainbow import FallingRainbow
#from zc_bg_rotatingrainbow import RotatingRainbow
#from zc_bg_brightnesstest import BrightnessTest
from zc_bg_larsonscanner import LarsonScanner
#from zc_bg_temperature import Temperature
from zc_bg_flag import Flag

from zc_utils import YEAR, MONTH, MDAY, HOUR, MINUTE, SECOND, WEEKDAY

radio.off()   ### the import turns it on

DAY_NAME = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
BASE_YEAR = 2000


### Any TZ offsets are positive for west and negative for east
### BRIGHTNESS is the normal value for room
### ADAPTIVE is additional amount scaled based on measured sunlight
### PIR is pin name for presence triggered brightness
cfg = {"CLOCK_PPM": 0.0,
       "RTC_PPM": 0.0,
       "NUMBER": 0,
       "COUNT": 1,
       "BRIGHTNESS": "0.1:0.018",
       "ADAPTIVE": 0.9,
       "NIGHT": "20:7",
       "PIR": "",
       "TZ": "GMT"}

### Optional variables in optional config.py
### THIS_MICROBIT_CLOCK_PPM
### THIS_ZHH_RTC_PPM
### THIS_CLOCK_NUMBER
### THIS_CLOCK_COUNT
### TZ
try:
    import config
    for im_var in dir(config):
        for cfg_var in cfg:  ### pylint: disable=consider-using-dict-items
            if im_var == cfg_var or im_var.endswith("_" + cfg_var):
                cls = type(cfg[cfg_var])
                try:
                    cfg[cfg_var] = cls(getattr(config, im_var))  ### pylint: disable=modified-iterating-dict
                except ValueError:
                    pass
except (ImportError, SyntaxError):
    pass

MASTER = cfg["NUMBER"] == 1 if cfg["NUMBER"] >= 1 else None

BRI_STD = [float(x) for x in cfg["BRIGHTNESS"].split(":")]
if len(BRI_STD) == 1:
    BRI_STD.append(BRI_STD[0])
dusk, dawn = [int(x) for x in cfg["NIGHT"].split(":")] if cfg["NIGHT"].find(":") >= 0 else (None, None)
adapt_bri = cfg["ADAPTIVE"]
light_level = 0.0

presence_pin = getattr(microbit, cfg["PIR"]) if cfg["PIR"] else None
PRESENCE_TIME_S = 600
presence_gone_t = None

print("NUMBER", cfg["NUMBER"])
display.scroll("TZ=" + cfg["TZ"])

### MCP7940 fine trim is multiples of 2 cycles per minute for 32.768kHz crystal
PPM_TO_TRIM_CONV = 32768 * 60 / (2 * 1000 * 1000)

### ZIP Halo HD has 60 RGB LEDs
ZIPCOUNT = 60
BLACK = (0, 0, 0)
##MCP_POR_TIME = (2000, 1, 1, 0, 0, 0, 0, 0)

VERY_LONG_DUR_MS = 2000 if MASTER else 8000
LONG_DUR_MS = 1000
SHORT_DUR_MS = 175

RADIO_TX_MS = 3  ### A guess at time taken to transmit


def calc_brightness(md_idx, r_ltime, light_lvl, humans):
    global presence_gone_t  ### pylint: disable=global-statement

    value = BRI_STD[0]  ### day level
    if adapt_bri:
        ### Quantize value to mostly stop this changing with tiny light level changes
        value += round(light_lvl / 16.0) / 16.0 * adapt_bri

    ### Dim value for clock mode and if it's either night time
    ### or a human has not been detected by presence sensor recently
    if md_idx != CLOCK or BRI_STD[0] == BRI_STD[1]:
        pass
    elif dusk is not None and (r_ltime[HOUR] >= dusk or r_ltime[HOUR] < dawn):
        value = BRI_STD[1]  ### dim night level
    elif humans is not None:
        if humans:
            presence_gone_t = list(r_ltime)
            DateCalc.add(presence_gone_t, PRESENCE_TIME_S)

        if DateCalc.cmp(r_ltime, presence_gone_t) > 0:
            value = BRI_STD[1]  ### dim night value

    return value

pin1.set_touch_mode(pin1.CAPACITIVE)

### MicroPython on micro:bit does not have these methods used by MCP7940
class EnhancedI2C:
    def __init__(self, i2c_):
        self._i2c = i2c_

    ### pylint: disable=unused-argument
    def readfrom_mem(self, addr, memaddr, nbytes, *, addrsize=8):
        self._i2c.write(addr, bytes([memaddr]))
        return self._i2c.read(addr, nbytes)

    ##def readfrom_mem_into(self, addr, memaddr, buf, *, addrsize=8):
    ##    raise NotImplementedError

    def writeto_mem(self, addr, memaddr, buf, *, addrsize=8):
        self._i2c.write(addr, bytes([memaddr]) + buf)


ei2c = EnhancedI2C(i2c)
mcp = MCP7940(ei2c)

### From https://github.com/microbit-foundation/micropython-microbit-v2/issues/83
##def set_high_drive(port_id, pin_id):
##    addr = 0x5000_0000 + port_id * 0x300 + 0x700 + pin_id * 4
##    machine.mem32[addr] = (machine.mem32[addr] & 0xffff_f8ff) | 3 << 8
##    print("DRIVE STRENGTH HIGH", port_id, pin_id)

zip_px = neopixel.NeoPixel(pin8, ZIPCOUNT)
zip_px.fill(BLACK)
zip_px.show()

### pin8 switch pin8 into high drive strength to see if it fixes
### https://github.com/microbit-foundation/micropython-microbit-v2/issues/227
### pin mapping https://tech.microbit.org/hardware/edgeconnector/#pins-and-signals
### SADLY IT DOES NOT
##set_high_drive(0, 10)  ### pin8 is P0.10/NFC2

display_image = bytearray(25)   ### values are 0..9
def show_display_image():
    display.show(Image(5, 5, display_image))

show_display_image()
gc.collect()

clock = ComboClock(mcp,
                   rtc_clock_drift_ppm=cfg["RTC_PPM"],
                   rtc_trim_conv=PPM_TO_TRIM_CONV,
                   mp_clock_drift_ppm=cfg["CLOCK_PPM"],
                   tz=cfg["TZ"]
                   )

comms = ClockComms(radio, cfg["NUMBER"])

stopwatch_hmsms = [0, 0, 0, 0.0]

mode_idx = 0
mode = "cst"   ### first character of each mode
ROTATE_MODES = 2
CLOCK = 0
STOPWATCH = 1
TIME_SET = 2


def zip_map(z_idx, count=60):
    """Map to a ZIP pixel position, idx can be a float."""
    return int(z_idx * ZIPCOUNT // count)

background_idx = 0
bri = BRI_STD[0]
background = (Blank(zip_px, display_image, bri),
              Milliseconds(zip_px, display_image, bri),
              #DigitalRain(zip_px, display_image, bri),
              #Pendulum(zip_px, display_image, bri),
              #FallingRainbow(zip_px, display_image, bri),
              #RotatingRainbow(zip_px, display_image, bri),
              Flag(zip_px, display_image, bri, {"flag": "ukraine wales poland"}),
              #BrightnessTest(zip_px, display_image, bri),
              LarsonScanner(zip_px, display_image, bri),
              #Temperature(zip_px, display_image, bri, {"function": temperature})
              )
gc.collect()

bg = background[background_idx]
bg.start(*clock.localtime_with_ms_and_ticks)
bg_displayed = bg.displayed
updates = 0
time_set_change = 0  ### 3-6 for hour minute second and 10 for am/pm
FIRST_TX_DUR_TMS = clock.s_to_ts(61_000)
TX_PERIOD_TMS = clock.s_to_ts(9_900)
SYNC_PERIOD_TMS = clock.s_to_ts(57 * 60_000)
clock_start_tms = ticks_ms()
last_tx_tms = ticks_add(clock_start_tms, 0 - TX_PERIOD_TMS)
last_sync_tms = ticks_add(clock_start_tms, 0 - SYNC_PERIOD_TMS)
new_sec = True
last_ss = None
first_comms_done = False
r_bri = g_bri = b_bri = None

### TODO there are many global variables and creating new ones in loop
### can cause MemoryException as the dict that stores them is enlarged
incrdecr = base = wrap = 0
t1_ms = t2_ms = ticks_ms()

gc.collect()
while True:
    if mode_idx != STOPWATCH:
        ### clear micro:bit display
        for idx in range(len(display_image)):
            display_image[idx] = 0
    zip_px.fill(BLACK)

    rtc_localtime, rtc_utctime, ss_ms, now_tms = clock.localandutctime_with_ms_and_ticks
    if mode_idx == CLOCK:
        updates = bg.render(rtc_localtime, ss_ms, now_tms)

    new_sec = rtc_localtime[SECOND] != last_ss
    last_ss = rtc_localtime[SECOND]
    if new_sec:
        bri = calc_brightness(mode_idx,
                                  rtc_localtime,
                                  light_level,
                                  presence_pin.read_digital() if presence_pin else None)
        if bri != bg.brightness or r_bri is None:
            bg.brightness = bri
            r_bri = bg.z_bri_norm(0.79, bri)
            g_bri = bg.z_bri_norm(0.62, bri)
            b_bri = bg.z_bri_norm(0.90, bri)

    h_idx = m_idx = s_idx = ms_idx = None
    display_char = None
    if mode_idx == STOPWATCH:
        time_ms = clock.stopwatch_time_ms()
        stopwatch_hmsms[:] = [time_ms // 3600000,
                              time_ms // 60000 % 60,
                              time_ms // 1000 % 60,
                              time_ms % 1000]
        h_idx = zip_map(stopwatch_hmsms[0], 12) % ZIPCOUNT
        m_idx = zip_map(stopwatch_hmsms[1])
        s_idx = zip_map(stopwatch_hmsms[2])
        ms_idx = zip_map(stopwatch_hmsms[3], 1000)
    elif mode_idx == CLOCK:
        ### pylint: disable=superfluous-parens
        if not (bg_displayed & (1 << HOUR)):
            h_idx = zip_map(rtc_localtime[HOUR], 12) % ZIPCOUNT
        if not (bg_displayed & (1 << MINUTE)):
            m_idx = zip_map(rtc_localtime[MINUTE])
        if not (bg_displayed & (1 << SECOND)):
            s_idx = zip_map(rtc_localtime[SECOND])
    elif mode_idx == TIME_SET:
        if time_set_change in (HOUR, MINUTE, SECOND):
            flash_on = (now_tms % 1000) > 300.0
            if time_set_change != HOUR or flash_on:
                h_idx = zip_map(rtc_localtime[HOUR], 12) % ZIPCOUNT
            display_char = ("p" if rtc_localtime[HOUR] >= 12 else "a")
            if time_set_change != MINUTE or flash_on:
                m_idx = zip_map(rtc_localtime[MINUTE])
            if time_set_change != SECOND or flash_on:
                s_idx = zip_map(rtc_localtime[SECOND])
        else:
            if time_set_change == YEAR:  ### Yellow
                h_idx = m_idx = zip_map(rtc_localtime[YEAR] - BASE_YEAR)
                print(rtc_localtime[YEAR])
                display_char = "y"
            elif time_set_change == MONTH:  ### Magenta
                h_idx = s_idx = zip_map(rtc_localtime[MONTH])  ### starts at 1
                display_char = "m"
            elif time_set_change == MDAY:  ### Cyan
                b_idx = s_idx = zip_map(rtc_localtime[MDAY])  ### starts at 1
                display_char = "d"
            elif time_set_change == WEEKDAY:
                h_idx = m_idx = s_idx = rtc_localtime[WEEKDAY]
                display_char = DAY_NAME[rtc_localtime[WEEKDAY]][:2]

    if h_idx is not None:
        bri = min(255, zip_px[h_idx][0] + r_bri) if zip_px[h_idx][0] < r_bri >> 1 else 0
        zip_px[h_idx] = (bri, zip_px[h_idx][1], zip_px[h_idx][2])
    if m_idx is not None:
        bri = min(255, zip_px[m_idx][1] + g_bri) if zip_px[m_idx][1] < g_bri >> 1 else 0
        zip_px[m_idx] = (zip_px[m_idx][0], bri, zip_px[m_idx][2])
    if s_idx is not None:
        bri = min(255, zip_px[s_idx][2] + b_bri) if zip_px[s_idx][2] < b_bri >> 1 else 0
        zip_px[s_idx] = (zip_px[s_idx][0], zip_px[s_idx][1], bri)
    if ms_idx is not None:
        bri = (min(255, zip_px[ms_idx][0] + r_bri * 2
               if clock.stopwatch_running
               else r_bri * 3 // 2) if zip_px[ms_idx][0] < r_bri >> 1 else 0)
        zip_px[ms_idx] = (bri, zip_px[ms_idx][1], zip_px[ms_idx][2])
    ##updates |= HaloBackground.HALO_CHANGED

    if display_char is not None:
        if len(display_char) == 1:
            display.show(display_char)
        else:
            ### TODO This would be better if it was set once and
            ### loop'd without wait'ing
            display.scroll(display_char)
    elif mode_idx == CLOCK:
        show_display_image()
    zip_px.show()

    ### Check for button and logo presses
    b_pressed = button_b.get_presses()
    if b_pressed:
        wait = False
        if mode_idx == STOPWATCH and not clock.stopwatch_running:
            clock.stopwatch_reset()
            wait = True

        if wait:
            while button_b.is_pressed():
                pass

    a_pressed = button_a.get_presses()
    if a_pressed:
        wait = False
        if mode_idx == STOPWATCH:
            if clock.stopwatch_running:
                clock.stopwatch_stop()
            else:
                clock.stopwatch_start()
            wait = True

        if wait:
            while button_a.is_pressed():
                pass

    if mode_idx == TIME_SET:
        if b_pressed:
            time_set_change += 1
            if time_set_change > WEEKDAY:
                time_set_change = YEAR
        elif a_pressed or pin1.is_touched():
            incrdecr = 1 if a_pressed else -1
            base = 0
            wrap = 60
            if time_set_change == HOUR:
                wrap = 24
            elif time_set_change == YEAR:
                base = BASE_YEAR
            elif time_set_change == MONTH:
                base = 1
                wrap = 12
            elif time_set_change == MDAY:
                base = 1
                wrap = DateCalc.days_in_month(rtc_localtime[MONTH], rtc_localtime[YEAR])
            elif time_set_change == WEEKDAY:
                wrap = 7

            rtc_localtime, rtc_utctime, ss_ms, now_tms = clock.localandutctime_with_ms_and_ticks
            ### This does not work around the DST change
            upd_localtime = list(rtc_localtime)
            upd_localtime[time_set_change] = (base
                                              + (upd_localtime[time_set_change] - base + incrdecr) % wrap)
            clock.set_rtc_local(upd_localtime)

        while button_a.is_pressed() or button_b.is_pressed() or pin1.is_touched():
            pass

    if pin_logo.is_touched():
        d_char = ""
        new_char = ""
        t1_ms = t2_ms = ticks_ms()
        threshold = 1.0
        while threshold > 0.5:
            if mode_idx != TIME_SET:
                if ticks_diff(t2_ms, t1_ms) > VERY_LONG_DUR_MS:
                    new_char = "t"  ### [t]ime set
                elif ticks_diff(t2_ms, t1_ms) > LONG_DUR_MS:
                    new_char = mode[(mode_idx + 1 ) % ROTATE_MODES][0]
                elif ticks_diff(t2_ms, t1_ms) > SHORT_DUR_MS:
                    new_char = "b"  ### next [b]ackground

            if new_char != d_char:
                display.show(new_char)
                d_char = new_char

            ### This threshold is a crude form of filtering to clean up the
            ### capacitive touch output on logo like switch debouncing
            sleep_ms(25)
            t2_ms = ticks_ms()
            threshold = threshold * 0.9 + 0.1 * int(pin_logo.is_touched())

        if mode_idx == TIME_SET:
            ### Exit time set mode
            clock.resync_enabled = True
            clock.sync_clocks()
            mode_idx = CLOCK
        elif ticks_diff(t2_ms, t1_ms) < LONG_DUR_MS:
            background_idx = (background_idx + 1) % len(background)
            bg.stop()
            gc.collect()
            bg = background[background_idx]
            bg.start(rtc_localtime, ss_ms, now_tms)
            bg_displayed = bg.displayed
        elif ticks_diff(t2_ms, t1_ms) < VERY_LONG_DUR_MS:
            mode_idx = (mode_idx + 1 ) % ROTATE_MODES
            gc.collect()
        else:
            mode_idx = TIME_SET
            time_set_change = HOUR
            clock.resync_enabled = False

    ### Calculate a filtered light level to smooth/slow changes
    if adapt_bri and new_sec:
        light_level = display.read_light_level() * 0.125 + light_level * 0.875

    ### Skip communication (over radio) if not needed
    ### Important to use UTC time here as not all timezones's hours start at same time
    if first_comms_done and 1 <= rtc_utctime[MINUTE] < 59:
        comms.off()
        continue

    comms.on()
    if not first_comms_done:
        since_start_tms = ticks_diff(now_tms, clock_start_tms)
        first_comms_done = since_start_tms > FIRST_TX_DUR_TMS

    if MASTER:
        ### Get fresh time and broadcast it
        rtc_utc_time, ss_ms, now_tms = clock.utctime_with_ms_and_ticks
        if ticks_diff(now_tms, last_tx_tms) >= TX_PERIOD_TMS:
            comms.broadcast_msg(MsgTimeWms(rtc_utc_time, ss_ms))
            last_tx_tms = now_tms
    else:
        msgandhdr = comms.receive_msg_full()
        ### Process time messsages if not recently synchronised
        if msgandhdr is not None and ticks_diff(now_tms, last_sync_tms) > SYNC_PERIOD_TMS:
            if isinstance(msgandhdr[0], MsgTimeWms):
                msg, rssi, rx_tus, src, dst = msgandhdr
                delay_us = ticks_diff(ticks_us(), rx_tus)
                if clock.set_utctime(msg.rtc_time,
                                     msg.ss_ms,
                                     RADIO_TX_MS + delay_us // 1000):
                    last_sync_tms = now_tms
