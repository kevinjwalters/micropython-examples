### sdslideshow.py v1.10
### Slide show of jpeg files on microSD card's slides directory

### Tested with Inky Frame and Pimoroni MicroPython v1.19.6 and v1.19.10

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


### Instructables article using this program
###
### https://www.instructables.com/Battery-Powered-Digital-Picture-Frame-Using-Pimoro/


### TODO - use button to select different modes
### TODO - acknowledge button presses with brief low power flash of LED
### TODO - check for button presses during pause on USB power
### TODO - add index file to order the slideshow
### TODO - add battery power detection and on-screen low batt warning
### TODO - work out if Inky Frame hardware is capable of running code
###        at battery power up if no rtc wakeup timer is configured
### TODO - alternate mode for using (8bit) spare register on rtc (PCF85063A)
###        for current slide number
### TODO - recursive slide image search?
### TODO - work out if Inky Frames have a consistent RTC clock speed error
### TODO - could put exceptions on display where possible
### TODO - offer text based instructions maybe via introduction.txt
### Pimoroni have their own slide show program
### https://github.com/pimoroni/pimoroni-pico/tree/main/micropython/examples/inky_frame/image_gallery

### Configuration

### 3.7 works for LiPo and probably 3 zinc-carbon/alkaline too
LOW_BATT_V = 3.7
##LOW_BATT_V = None  ### set to None to disable on-screen warning


### Inky Frame pins
IF_HOLD_VSYS_EN_PIN = 2
IF_I2C_SDA_PIN = 4
IF_I2C_SCL_PIN = 5
IF_LED_ACTIVITY = 6
IF_LED_CONNECT = 7
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

### Inky Frame display dimensions
IF_WIDTH = 600
IF_HEIGHT = 448

### Inky Frame colours
IF_BLACK = 0
IF_WHITE = 1
IF_GREEN = 2
IF_BLUE = 3
IF_RED = 4
IF_YELLOW = 5
IF_ORANGE = 6
IF_TAUPE = 7


from machine import Pin, SPI, PWM, ADC

### Set VSYS hold high to stay awake
hold_vsys_en_pin = Pin(IF_HOLD_VSYS_EN_PIN, Pin.OUT, value=True)

from pimoroni import ShiftRegister
### Button state appears in a shift register apparently
button_sr = ShiftRegister(IF_SR_CLOCK, IF_SR_LATCH, IF_SR_OUT)
previous_buttons = button_sr.read()

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

led_brightness = 0.4
leds_pwm = {IF_LED_ACTIVITY: PWM(Pin(IF_LED_ACTIVITY)),
            IF_LED_CONNECT: PWM(Pin(IF_LED_CONNECT)),
            IF_LED_A: PWM(Pin(IF_LED_A)),
            IF_LED_B: PWM(Pin(IF_LED_B)),
            IF_LED_C: PWM(Pin(IF_LED_C)),
            IF_LED_D: PWM(Pin(IF_LED_D)),
            IF_LED_E: PWM(Pin(IF_LED_E))}

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

debug = 0

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

def add_text(text, x=20, y=IF_HEIGHT-(8+2)*8, color=IF_WHITE, scale=8,
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
IF_BUTTON_A = 1 << 0
IF_BUTTON_B = 1 << 1
IF_BUTTON_C = 1 << 2
IF_BUTTON_D = 1 << 3
IF_BUTTON_E = 1 << 4
IF_BUTTONS = IF_BUTTON_A | IF_BUTTON_B | IF_BUTTON_C | IF_BUTTON_D | IF_BUTTON_E
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
        buttons = button_sr.read()
        if previous_buttons is not None:
            ### OR the button values with values at power up
            ### to try to catch brief button presses
            buttons |= previous_buttons
            previous_buttons = None

        if debug >= 1:
            print("SR", "0b{:08b}".format(buttons))

        button_ack = None
        if idx is None or buttons & IF_BUTTON_C:
            idx = 1
            button_ack = IF_LED_C
        elif buttons & IF_BUTTON_A:
            idx -= 1
            advance_forwards = False
            button_ack = IF_LED_A
        elif buttons & IF_BUTTON_E:
            show_intro = not show_intro  ### TODO fix this
            button_ack = IF_LED_E
        else:
            idx += 1  ### button B or time passes
            if buttons & IF_BUTTON_B:
                button_ack = IF_LED_B

        if not 1 <= idx <= num_images:
            idx = 1 if advance_forwards else num_images

        ### Give user some feedback that button press has registered
        if button_ack is not None:
            set_led(button_ack, led_brightness, 0.3)

        graphics.set_pen(IF_BLACK)
        graphics.clear()  ### clear is really a fill using set_pen() colour

        set_led(IF_LED_ACTIVITY, led_brightness / 3, 0, 20)
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

        set_led(IF_LED_ACTIVITY, 0, 0, 0)
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
        if  LOW_BATT_V is not None and volts <= LOW_BATT_V:
            add_text("Low batt: {:.2f}V".format(volts), color=IF_RED, outline=IF_BLACK)

        gc.collect()
        set_led(IF_LED_ACTIVITY, led_brightness / 4, 0, 8)
        if debug >=1:
            print("START update()", gc.mem_free(), idx)
        graphics.update()
        if debug >= 1:
            print("END update()", gc.mem_free(), idx)
        set_led(IF_LED_ACTIVITY, 0, 0, 0)

        ### Write idx of current image to a file on sd card
        set_led(IF_LED_ACTIVITY, led_brightness)
        try:
            with open(SLIDE_CURFILE, "wt") as fh:
                fh.write("{:d}\n".format(idx))
        except OSError:
            pass
        set_led(IF_LED_ACTIVITY, 0)

        ### Indicate going to sleep
        ##led_c.duty_u16(32768)

        ### Changes at 146 seconds for 3m and 55 at for 60s at 1/60Hz (on USB power)
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
        start_pause_ms = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_pause_ms) < IMAGE_PAUSE * 1000:
            previous_buttons = button_sr.read()
            if previous_buttons & (IF_BUTTONS | IF_EXTERNAL_TRIGGER):
                break

except Exception as ex:  ### pylint: disable=broad-except
##except IndexError as ex:
    print("Unexpected exception:", repr(ex))

uos.umount(SD_MOUNTPOINT)

### On battery power changing this pin to a read will shutdown RP2040
### This is required if there's an exception to avoid wasting battery
hold_vsys_en_pin.init(Pin.IN)
### Sleep to allow Inky Frame to go into deep sleep mode in case MicroPython
### does anything now or in the future with GPIO state when program finishes
time.sleep(2)
