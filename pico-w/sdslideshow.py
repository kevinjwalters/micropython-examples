### sdslideshow.py v1.12
### Slide show of jpeg files on microSD card's slides directory

### Tested with Inky Frame and Pimoroni Inky Frame specific MicroPython v1.19.16

### Versions prior to v1.11 will work with
### older non Inky Frame specific Pimoroni Micropython versions

### copy this file to Inky Frame as main.py

### MIT License

### Copyright (c) 2022, 2023 Kevin J. Walters

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


### Instructables articles using this program
###
### https://www.instructables.com/Battery-Powered-Digital-Picture-Frame-Using-Pimoro/
### https://www.instructables.com/Pimoroni-Inky-Frame-Comparison-4-Inch-Vs-57-Inch/

### TODO - use button to select different modes
### TODO - check for button presses during pause on USB power
### TODO - add index file to order the slideshow
### TODO - alternate mode for using (8bit) spare register on rtc (PCF85063A)
###        for current slide number
### TODO - recursive slide image search?
### TODO - work out if Inky Frames have a consistent RTC clock speed error
### TODO - could put exceptions on display where possible
### TODO - offer text based instructions maybe via introduction.txt

### Pimoroni have their own slide show program
### https://github.com/pimoroni/pimoroni-pico/tree/main/micropython/examples/inky_frame/image_gallery

### Configuration

### 3.9 works for LiPo and probably 3 zinc-carbon/alkaline too
LOW_BATT_V = 3.9
##LOW_BATT_V = None  ### set to None to disable on-screen warning

### This module reads the shift register to get the button state near wakeup
### The Inky Frame specific version of Pimoroni MicroPython sets HOLD_VSYS_EN high
### as the interpreter starts

import inky_frame
buttons_at_startup = inky_frame.SHIFT_STATE

import gc
import re
import time
import uos
from machine import Pin, SPI, PWM, ADC

import jpegdec
from picographics import PicoGraphics

### Inky Frame pins
##IF_HOLD_VSYS_EN_PIN = 2
IF_I2C_INT_PSRAM_CS_PIN = 3
IF_MISO = 16
IF_CLK = 18
IF_MOSI = 19
IF_SD_CS = 22
IF_VSYS_DIV3 = 29
IF_VBUS = 'WL_GPIO2'


### Differentiate between Inky Frame 4, 5.7 and 7.3 based on a battle
### between 10k external pull-ups which differ on Inky Frames
### and the Pico's internal 50-80k pull down

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


### import ordering of sdcard seems to affect memory exceptions :(
gc.collect()
import sdcard
gc.collect()

debug = 2

led_brightness = 0.4
leds_pwm = {inky_frame.LED_BUSY: PWM(Pin(inky_frame.LED_BUSY)),
            inky_frame.LED_WIFI: PWM(Pin(inky_frame.LED_WIFI)),
            inky_frame.LED_A: PWM(Pin(inky_frame.LED_A)),
            inky_frame.LED_B: PWM(Pin(inky_frame.LED_B)),
            inky_frame.LED_C: PWM(Pin(inky_frame.LED_C)),
            inky_frame.LED_D: PWM(Pin(inky_frame.LED_D)),
            inky_frame.LED_E: PWM(Pin(inky_frame.LED_E))}


def set_led(led, brightness=1, duration=0, flicker=None):
    """Set led brightness with optional pause and flicker frequency."""

    ### led goes off with 65535 for some reason??
    leds_pwm[led].duty_u16(round(brightness * 65534))

    ### min frequency is 8Hz, 1907 is default
    if flicker is not None:
        leds_pwm[led].freq(max(8, flicker if flicker != 0 else 1907))

    if duration:
        time.sleep(duration)
        leds_pwm[led].duty_u16(0)

gc.collect()
graphics = PicoGraphics(DISPLAY)
gc.collect()

### Inky Frame display dimensions
IF_WIDTH, IF_HEIGHT = graphics.get_bounds()[:2]

if debug > 0:
    print("width x height:", IF_WIDTH, IF_HEIGHT)


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


IMAGE_PAUSE = 4 * 60 * 60
##IMAGE_PAUSE = 5 * 60

SD_MOUNTPOINT = "/sd"
SLIDE_DIR = SD_MOUNTPOINT + "/slides"
SLIDE_INTROFILE = SD_MOUNTPOINT + "/introduction.jpg"
SLIDE_CURFILE = SLIDE_DIR + "/slide.cur"
JPEG_RE = re.compile(r".\.[jJ][pP][eE]?[gG]$")

### Inky Frame bit mask for buttons and wake events
### Pimoroni's ShiftRegister.read returns opposite order and there's
### a lot of confusing discrepancies with ordering in library code
IF_BUTTON_A = 1 << 7
IF_BUTTON_B = 1 << 6
IF_BUTTON_C = 1 << 5
IF_BUTTON_D = 1 << 4
IF_BUTTON_E = 1 << 3
IF_BUTTONS = IF_BUTTON_A | IF_BUTTON_B | IF_BUTTON_C | IF_BUTTON_D | IF_BUTTON_E
IF_RTC_ALARM = 1 << 2
IF_EXTERNAL_TRIGGER = 1 << 1
IF_EINK_BUSY = 1 << 0

### This is dealing with issues related to
### https://github.com/pimoroni/pimoroni-pico/issues/719
def read_buttons():
    """Read value and re-order to match the ordering of wakeup.get_shift_state"""
    sr_buttons_a_lsb = inky_frame.sr.read()
    sr_buttons = 0
    for _ in range(8):
        sr_buttons <<= 1
        sr_buttons += (sr_buttons_a_lsb & 1)
        sr_buttons_a_lsb >>= 1
    return sr_buttons

### rtc is PCF85063A real time clock
inky_frame.rtc.reset()
inky_frame.rtc.enable_timer_interrupt(True)

sd_spi = SPI(0,
             sck=Pin(IF_CLK, Pin.OUT),
             mosi=Pin(IF_MOSI, Pin.OUT),
             miso=Pin(IF_MISO, Pin.OUT))
sd = None
last_exception = None
### First one often fails at power up
for _ in range(15):
    try:
        sd = sdcard.SDCard(sd_spi, Pin(IF_SD_CS))
        uos.mount(sd, SD_MOUNTPOINT)
        break
    except OSError as ex:
        last_exception = ex
    time.sleep(4)
if sd is None:
    raise last_exception
gc.collect()


def count_images(slide_dir):
    count = 0
    ### Iterating over filter + ilistdir results here in hope
    ### of using less memory than listdir approach
    for fileinfo in uos.ilistdir(slide_dir):
        if JPEG_RE.search(fileinfo[0]):
            count += 1
    return count


def image_filename(slide_dir, slide_idx, prefixed=True):
    s_idx = 1
    for fileinfo in uos.ilistdir(slide_dir):
        filename = fileinfo[0]
        if JPEG_RE.search(filename):
            if s_idx == slide_idx:
                return slide_dir + "/" + filename if prefixed else filename
            s_idx += 1
    return None


num_images = count_images(SLIDE_DIR)

idx = None
try:
    with open(SLIDE_CURFILE, "rt") as fh:
        idx = int(fh.readline())
        if not 1 <= idx <= num_images:
            idx = 1
except (OSError, ValueError) as ex:
    pass

jpeg = jpegdec.JPEG(graphics)
gc.collect()

show_intro = False
try:
    while True:
        advance_forwards = True
        buttons = read_buttons()
        if buttons_at_startup is not None:
            ### OR the button values with values at power up
            ### to try to catch brief button presses
            buttons |= buttons_at_startup
            buttons_at_startup = None

        if debug >= 1:
            print("SR", "0b{:08b}".format(buttons))

        button_ack = None
        if idx is None or buttons & IF_BUTTON_C:
            idx = 1
            button_ack = inky_frame.LED_C
        elif buttons & IF_BUTTON_A:
            idx -= 1
            advance_forwards = False
            button_ack = inky_frame.LED_A
        elif buttons & IF_BUTTON_E:
            show_intro = not show_intro  ### TODO fix this
            button_ack = inky_frame.LED_E
        else:
            idx += 1  ### button B or time passes
            if buttons & IF_BUTTON_B:
                button_ack = inky_frame.LED_B

        if not 1 <= idx <= num_images:
            idx = 1 if advance_forwards else num_images

        ### Give user some feedback that button press has registered
        if button_ack is not None:
            set_led(button_ack, led_brightness, 0.3)

        graphics.set_pen(inky_frame.BLACK)
        graphics.clear()  ### clear is really a fill using set_pen() colour

        set_led(inky_frame.LED_BUSY, led_brightness / 3, 0, 20)
        attempts = 0
        while attempts < num_images:
            ### TODO: something if this comes back None
            jpeg_filename = SLIDE_INTROFILE if show_intro else image_filename(SLIDE_DIR, idx)

            if debug >= 1:
                print("Decoding", jpeg_filename, idx, "of", num_images)

            try:
                jpeg.open_file(jpeg_filename)
                ### Progressive jpeg file throws
                ### RuntimeError: JPEG: could not read file/buffer.
                ### Also happens on a q98 jpeg but not the q92 version of it
                jpeg.decode()
            except RuntimeError as ex:
                print("Skipping", jpeg_filename,
                      "due to [", repr(ex),
                      "] this may be a progressive JPEG")
                if show_intro:
                    raise ex
                if advance_forwards:
                    idx += 1
                    if idx > num_images:
                        idx = 1
                else:
                    idx -= 1
                    if idx < 1:
                        idx = num_images
                attempts += 1
                continue

            break

        set_led(inky_frame.LED_BUSY, 0, 0, 0)
        show_intro = False

        ### https://gist.github.com/helgibbons/3ce1a3b6eb24ca6f27a66455caba9809
        ### vbus.value() is often wrong and it takes 1044-1090ms (?!)
        ##if debug >= 2:
        ##    debug_text_pos = (20, 360, 600 - 2 * 20, 6)
        ##    if vbus.value():
        ##        graphics.set_pen(IF_BLUE)
        ##        graphics.text('USB power', *debug_text_pos)
        ##    else:
        ##        graphics.set_pen(IF_GREEN)
        ##        graphics.text('{:.2f}'.format(batt_v()) + "v", *debug_text_pos)
        usb_power_iffy = vbus.value()
        volts = batt_v()
        if LOW_BATT_V is not None and volts <= LOW_BATT_V:
            add_text("Low batt: {:.2f}V".format(volts),
                     color=inky_frame.RED, outline=inky_frame.BLACK)

        gc.collect()
        set_led(inky_frame.LED_BUSY, led_brightness / 4, 0, 8)
        if debug >=1:
            print("START update()", gc.mem_free(), idx)
        graphics.update()
        if debug >= 1:
            print("END update()", gc.mem_free(), idx)
        set_led(inky_frame.LED_BUSY, 0, 0, 0)

        ### Write idx of current image to a file on sd card
        set_led(inky_frame.LED_BUSY, led_brightness)
        try:
            with open(SLIDE_CURFILE, "wt") as fh:
                fh.write("{:d}\n".format(idx))
        except OSError:
            pass
        set_led(inky_frame.LED_BUSY, 0)

        ### Indicate going to sleep
        ##led_c.duty_u16(32768)

        ### Changes at 146 seconds for 3m and 55 at for 60s at 1/60Hz (on USB power)
        if IMAGE_PAUSE <= 255:
            inky_frame.rtc.set_timer(IMAGE_PAUSE)   ### defaults to 1Hz
        else:
            inky_frame.rtc.set_timer(round(IMAGE_PAUSE / 60),
                                     ttp=inky_frame.rtc.TIMER_TICK_1_OVER_60HZ)

        ### On battery power shutdown RP2040 (set HOLD_VSYS_EN to low)
        ### and awake when timer fires or any button is pressed
        inky_frame.turn_off()

        ### five second pause experiment as forum discussion suggests
        ### time.sleep() interfers with Inky Frame sleep mode
        ### https://forums.pimoroni.com/t/inky-frame-deep-sleep-explanation/19965/3
        ### This does not look accurate/needed
        ##for _ in range(5 * 240 * 1000):
        ##    pass

        ### This will only be reached on USB power
        start_pause_ms = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_pause_ms) < IMAGE_PAUSE * 1000:
            buttons_at_startup = read_buttons()
            if buttons_at_startup & (IF_BUTTONS | IF_EXTERNAL_TRIGGER):
                break

except Exception as ex:  ### pylint: disable=broad-except
##except IndexError as ex:
    print("Unexpected exception:", repr(ex))

uos.umount(SD_MOUNTPOINT)

### On battery power shutdown RP2040 (set HOLD_VSYS_EN to low)
### This is required if there's an exception to avoid wasting battery
inky_frame.turn_off()
### Sleep to allow Inky Frame to go into deep sleep mode in case MicroPython
### does anything now or in the future with GPIO state when program finishes
time.sleep(2)
