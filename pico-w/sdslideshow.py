### sdslideshow.py v1.5
### Slide show of jpeg files on microSD card's slides directory

### Tested with Inky Frame and Pimoroni MicroPython v1.19.6

### copy this file to Inky Frame as main.py

### MIT License

### Copyright (c) 2022 Kevin J. Walters

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

### TODO - use button to select different modes
### TODO - acknowledge button presses with brief low power flash of LED
### TODO - check for button presses during pause on USB power
### TODO - add index file to order the slideshow
### TODO - add battery power detection and on-screen low batt warning
### TODO - work out if Inky Frame hardware is capable of running code
###        at battery power up if no rtc wakeup timer is configured
### TODO - are there any risks with leaving sd card mounted?
###        any write caching?
### TODO - alternate mode for using (8bit) spare register on rtc (PCF85063A)
###        for current slide number OR perhaps this could be used to
###        determine device is still battery powered and on when reawakening
### TODO - make SLIDE_INTROFILE optional and display a text version without it

### Pimoroni have their own slide show program
### https://github.com/pimoroni/pimoroni-pico/tree/main/micropython/examples/inky_frame/image_gallery

### Inky Frame pins
IF_HOLD_VSYS_EN_PIN = 2
IF_I2C_SDA_PIN = 4
IF_I2C_SCL_PIN = 5
IF_SR_CLOCK = 8
IF_SR_LATCH = 9
IF_SR_OUT = 10
IF_LED_A = 11
IF_LED_B = 12
IF_LED_C = 13
IF_LED_D = 14
IF_LED_E = 15
IF_VSYS_DIV3 = 29
IF_VBUS = 'WL_GPIO2'

from machine import Pin, SPI, PWM, ADC

### Set VSYS hold high to stay awake
### It may be beneficial (??) to set this as early as possible in the code
### https://forums.pimoroni.com/t/inky-frame-deep-sleep-explanation/19965
hold_vsys_en_pin = Pin(IF_HOLD_VSYS_EN_PIN, Pin.OUT, value=True)

from pimoroni import ShiftRegister
### Button state appears in a shift register apparently
button_sr = ShiftRegister(IF_SR_CLOCK, IF_SR_LATCH, IF_SR_OUT)
poweron_buttons = button_sr.read()

##led_a = PWM(Pin(IF_LED_A))
##led_a.freq(8)
##led_a.duty_u16(32768)

##led_b = PWM(Pin(IF_LED_B))
###led_b.freq(1000)
##led_b.duty_u16(65535)

##led_c = PWM(Pin(IF_LED_C))
##led_c.freq(8)

import gc
import re
import time
import uos

import jpegdec
from picographics import PicoGraphics, DISPLAY_INKY_FRAME as DISPLAY

from pimoroni_i2c import PimoroniI2C
from pcf85063a import PCF85063A

import sdcard

gc.collect()
graphics = PicoGraphics(DISPLAY)
gc.collect()

debug = 0

batt_v_adc = ADC(IF_VSYS_DIV3)
def batt_v():
    return batt_v_adc.read_u16() * (3 * 3.3 / 65535)
vbus = Pin(IF_VBUS, Pin.IN)


IMAGE_PAUSE = 4 * 60 * 60
##IMAGE_PAUSE = 5 * 60

SD_MOUNTPOINT = "/sd"
SLIDE_DIR = SD_MOUNTPOINT + "/slides"
SLIDE_INTROFILE = SD_MOUNTPOINT + "/introduction.jpg"
SLIDE_CURFILE = SLIDE_DIR + "/slide.cur"
JPEG_RE = re.compile(r".\.[jJ][pP][eE]?[gG]$")


### Inky Frame colours
IF_BLACK = 0
IF_WHITE = 1
IF_GREEN = 2
IF_BLUE = 3
IF_RED = 4
IF_YELLOW = 5
IF_ORANGE = 6
IF_TAUPE = 7

### Inky Frame bit mask for buttons and wake events
IF_BUTTON_A = 1 << 0
IF_BUTTON_B = 1 << 1
IF_BUTTON_C = 1 << 2
IF_BUTTON_D = 1 << 3
IF_BUTTON_E = 1 << 4
IF_RTC_ALARM = 1 << 5
IF_EXTERNAL_TRIGGER = 1 << 6
IF_EINK_BUSY = 1 << 7

### PCF85063A real time clock
i2c = PimoroniI2C(IF_I2C_SDA_PIN, IF_I2C_SCL_PIN, 100 * 1000)
rtc = PCF85063A(i2c)
rtc.reset()
rtc.enable_timer_interrupt(True)

sd_spi = SPI(0,
             sck=Pin(18, Pin.OUT),
             mosi=Pin(19, Pin.OUT),
             miso=Pin(16, Pin.OUT))
sd = None
last_exception = None
### First one often fails at power up
for _ in range(15):
    try:
        sd = sdcard.SDCard(sd_spi, Pin(22))
        uos.mount(sd, SD_MOUNTPOINT)
        break
    except OSError as ex:
        last_exception = ex
    time.sleep(4)
if sd is None:
    raise last_exception
gc.collect()

files = list(filter(JPEG_RE.search, uos.listdir(SLIDE_DIR)))
num_images = len(files)

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
        ##led_c.duty_u16(0)

        buttons = button_sr.read()
        if poweron_buttons is not None:
            ### OR the button values with values at power up
            ### to try to catch brief button presses
            buttons |= poweron_buttons
            poweron_buttons = None

        if debug >= 1:
            print("SR", "0b{:08b}".format(buttons))

        if idx is None or buttons & IF_BUTTON_C:
            idx = 1
        elif buttons & IF_BUTTON_A:
            idx -= 1
        elif buttons & IF_BUTTON_E:
            show_intro = True
        else:
            idx += 1  ### button B or time passes

        if not 1 <= idx <= num_images:
            idx = 1

        filename = SLIDE_INTROFILE if show_intro else SLIDE_DIR + "/" + files[idx - 1]

        graphics.set_pen(IF_BLACK)
        graphics.clear()  ### clear is really a fill using set_pen() colour

        jpeg.open_file(filename)
        jpeg.decode()

        show_intro = False

        ### https://gist.github.com/helgibbons/3ce1a3b6eb24ca6f27a66455caba9809
        if debug >= 2:
            debug_text_pos = (20, 360, 600 - 2 * 20, 6)
            if vbus.value():
                graphics.set_pen(IF_BLUE)
                graphics.text('USB power', *debug_text_pos)
            else:
                graphics.set_pen(IF_GREEN)
                graphics.text('{:.2f}'.format(batt_v()) + "v", *debug_text_pos)

        gc.collect()
        if debug >=1:
            print("START update()", gc.mem_free(), idx)
        graphics.update()
        if debug >= 1:
            print("END update()", gc.mem_free(), idx)

        ### Write idx of current image to a file on sd card
        try:
            with open(SLIDE_CURFILE, "wt") as fh:
                fh.write("{:d}\n".format(idx))
        except OSError:
            pass

        ### Indicate going to sleep
        ##led_c.duty_u16(32768)

        ### Changes at 146 seconds for 3 and 55 at for at 1/60Hz (on USB power)
        if IMAGE_PAUSE <= 255:
            rtc.set_timer(IMAGE_PAUSE)   ### defaults to 1Hz
        else:
            rtc.set_timer(round(IMAGE_PAUSE / 60), ttp=PCF85063A.TIMER_TICK_1_OVER_60HZ)

        ### On battery power changing this pin to a read will shutdown RP2040
        ### and awake when timer fires or any button is pressed
        hold_vsys_en_pin.init(Pin.IN)

        ### five second pause experiment as forum discussion suggests
        ### time.sleep() interfers with Inky Frame sleep mode
        ### https://forums.pimoroni.com/t/inky-frame-deep-sleep-explanation/19965/3
        ### This does not look accurate/needed
        ##for _ in range(5 * 240 * 1000):
        ##    pass

        ### This will only be reached on USB power
        time.sleep(IMAGE_PAUSE)
except Exception as ex:  ### pylint: disable=broad-except
    print("Unexpected exception:", repr(ex))

uos.umount(SD_MOUNTPOINT)
