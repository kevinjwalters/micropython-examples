### edubit-halloween v1.0
### Play audio samples triggered by IR with servo motion on Cytron edu:bit

### Halloween scene on Cytron edu:bit using micro:bit V1
### Play audio sample while S1 servo moves, fade-up RGB pixels
### and pulse two micro:bit LEDs while other audio samples play

### Tested with BBC micro:bit V1 and MicroPython v1.9.2-34-gd64154c73

### MIT License

### Copyright (c) 2021 Kevin J. Walters
### Copyright (c) 2020 Cytron Technologies (edubit.py)

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

import gc

import audio
from neopixel import NeoPixel


### Angles for door open/closed - these are likely to need tuning
DOOR_CLOSED = 35
DOOR_OPEN = 140

DOOR_DELAY = int(2400 / abs(DOOR_OPEN - DOOR_CLOSED + 1))

DOORCREAK_4 = "doorcreak4.raw"
LAUGH_1A = "laugh1a.raw"
LAUGH_1B = "laugh1b.raw"

### Start of trimmed edubit.py
### inlined due to Memoryerror issues on micro:bit V1
from microbit import *
from utime import sleep_ms

I2C_ADDRESS = 0x08

REG_ADD_SERVO_1 = 1
REG_ADD_SERVO_2 = 2
REG_ADD_SERVO_3 = 3
REG_ADD_PWR_STATE = 12

S1 = REG_ADD_SERVO_1
S2 = REG_ADD_SERVO_2
S3 = REG_ADD_SERVO_3
All = 1000

IR_BIT_PIN = pin8

flag = 0

def limit(value,min,max):
    if value < min:
        value = min
    elif value > max:
        value = max
    return value

def i2cRead(register):
    buf = bytearray(1)
    buf[0] = register
    value = 0
    i2c.write(I2C_ADDRESS,buf,True)
    value = i2c.read(I2C_ADDRESS,1)
    return value[0]

def i2cWrite(register,data):
    buffer = bytearray(2)
    buffer[0] = register
    buffer[1] = data
    i2c.write(I2C_ADDRESS,buffer)

def init():
    global flag
    global oldPowerState

    if flag == 0:
        oldPowerState = is_power_on()
        flag = 1

    if is_power_on():
        if oldPowerState == False:
            disable_servo(S1)
            disable_servo(S2)
            disable_servo(S3)
        oldPowerState = True
    else:
        oldPowerState = False
    sleep_ms(200)

def is_power_on():
    if i2cRead(REG_ADD_PWR_STATE) != 0:
        return True
    else:
        return False

def sets_servo_position(servo,position):
    position = limit(position,0,180)

    pulseWidth = int(position * 20 / 18 + 50)
    if servo == All:
        i2cWrite(S1,pulseWidth)
        i2cWrite(S2,pulseWidth)
        i2cWrite(S3,pulseWidth)
    else:
        i2cWrite(servo,pulseWidth)

def disable_servo(servo):
    if servo == All:
        i2cWrite(S1,0)
        i2cWrite(S2,0)
        i2cWrite(S3,0)
    else:
        i2cWrite(servo,0)

def read_IR_sensor():
    return IR_BIT_PIN.read_digital()

def is_IR_sensor_triggered():
    if IR_BIT_PIN.read_digital() != 0:
        return True
    else:
        return False

### End of trimmed edubit.py


FRAME_SIZE = 32

def frames_from_file(snd_file, aframe, duplicate=1):
    while snd_file.readinto(aframe, FRAME_SIZE // duplicate) > 0:
        if duplicate > 1:
            for idx in range(FRAME_SIZE - 1, 0, -1):
                aframe[idx] = aframe[idx // duplicate]
        yield aframe

### Initialise the edubit library
init()

### Four RGB pixels on RGB Bit
pixels = NeoPixel(pin13, 4)

def fill_pixels(pix, col):
    for idx in range(len(pix)):
        pix[idx] = col
    pix.show()

### External speaker on P0 + V2 one together!
try:
    speaker.on()
except NameError:
    pass  ### speaker-less V1

BLACK = (0, 0, 0)

### 255 is very bright!
SLOW_FADE_UP = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11,
                12, 15, 17, 20, 22, 25, 27,
                30, 40, 50, 60, 70, 80)

while True:
    gc.collect()
    if is_IR_sensor_triggered():
        ### Open the door with creaking sound played at half-speed
        filename = DOORCREAK_4
        frame = audio.AudioFrame()
        with open(filename, "rb") as sndfile:
            audio.play(frames_from_file(sndfile, frame, duplicate=2),
                       wait=False)
            for angle in range(DOOR_CLOSED, DOOR_OPEN + 1, 1):
                sets_servo_position(S1, angle)
                sleep(DOOR_DELAY)
            while audio.is_playing():
                pass

        ### Fade up RGB pixels to green slowly
        for green in SLOW_FADE_UP:
            colour = (0, green, 0)
            fill_pixels(pixels, colour)
            sleep(30)

        ### Laugh six times with two micro:bit LEDs pulsing for eyes
        for _ in range(2):
            for _ in range(2):
                filename = LAUGH_1A
                with open(filename, "rb") as sndfile:
                    audio.play(frames_from_file(sndfile, frame),
                               wait=False)
                    for bri in range(0, 10):
                        display.set_pixel(1, 1, bri)
                        display.set_pixel(3, 1, bri)
                        sleep(15)
                    while audio.is_playing():
                        pass

            filename = LAUGH_1B
            with open(filename, "rb") as sndfile:
                audio.play(frames_from_file(sndfile, frame),
                           wait=False)
                for bri in range(9, -1, -1):
                    display.set_pixel(1, 1, bri)
                    display.set_pixel(3, 1, bri)
                    sleep(30)
                while audio.is_playing():
                    pass

        filename = DOORCREAK_4
        with open(filename, "rb") as sndfile:
            audio.play(frames_from_file(sndfile, frame),
                       wait=False)

            ### Close door faster than it opened
            for angle in range(DOOR_OPEN, DOOR_CLOSED - 1, -2):
                sets_servo_position(S1, angle)
                sleep(DOOR_DELAY // 2)

            while audio.is_playing() :
                pass

        ### Pause half a second then back to black (off) for RGB pixels
        sleep(500)
        fill_pixels(pixels, BLACK)
