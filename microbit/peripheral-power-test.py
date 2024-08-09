### peripheral-power-test v1.2
### Peripheral power test

### Copy this https://python.microbit.org/ to send to micro:bit V1 or V2

### MIT License

### Copyright (c) 2024 Kevin J. Walters

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

### Other "ports"
### https://github.com/kevinjwalters/arduino-examples/blob/master/uno/peripheral-power-test/peripheral-power-test.ino
### https://github.com/kevinjwalters/circuitpython-examples/blob/master/pico/peripheral-power-test.py


import os
import time

from microbit import pin0, pin1, pin2, display, Image
import neopixel


### Based on https://github.com/microbit-playground/microbit-servo-class/blob/master/servo.py
class Servo:
    def __init__(self, pin, freq=50, min_pulse=600, max_pulse=2400, angle=180):
        self.min_us = min_pulse
        self.max_us = max_pulse
        self.us = 0
        self.freq = freq
        self.angle = angle
        self.analog_period = 0
        self.pin = pin
        self._total_range = self.max_us - self.min_us
        analog_period = round((1 / self.freq) * 1000)  # hertz to miliseconds
        self.pin.set_analog_period(analog_period)

    def write_us(self, us):
        us = min(self.max_us, max(self.min_us, us))
        duty = round(us * 1024 * self.freq // 1000000)
        self.pin.write_analog(duty)
        ##self.pin.write_digital(0)  # turn the pin off

    def write_angle(self, degrees=None):
        if degrees is None:
            self.turn_off()
        degrees = degrees % 360
        us = self.min_us + self._total_range * degrees // self.angle
        self.write_us(us)

    def turn_off(self):
        self.pin.write_analog(0)


machine = os.uname().machine
if "nRF51822" in machine:
    HARDWARE = "V1"
    RGBPIXLIM = 3
else:
    HARDWARE = "V2"
    RGBPIXLIM = 12  ### drops from 3.28V to 2.87V

HIGH_PIN = pin0
RGBPIXELS_PIN = pin1
SERVO_PIN = pin2

display.clear()
HIGH_PIN.write_digital(1)  ### set high

### If NUM_PIXELS is changed then review SERVO_SPEED_LOOPS
NUM_PIXELS = 12
SERVO_SPEED_LOOPS = 4  ### Double speed every N loops

SERVO_MIN = 0
SERVO_MAX = 180

pixels = neopixel.NeoPixel(RGBPIXELS_PIN, NUM_PIXELS)

pixel_black = (0, 0, 0)
pixel_white = (255, 255, 255)

ARDUINO_MIN_PULSE = 544
ARDUION_MAX_PULSE = 2400
myservo = Servo(SERVO_PIN,
                min_pulse=ARDUINO_MIN_PULSE, max_pulse=ARDUION_MAX_PULSE)
myservo.turn_off()  ### turn off servo

### Default servo range is 600 to 2400, slightly narrower than Arduino default
### https://docs.circuitpython.org/projects/motor/en/latest/api.html#adafruit_motor.servo.Servo
### https://github.com/kevinjwalters/circuitpython-examples/blob/master/pico/peripheral-power-test.py

def pixels_off():
    for p_idx in range(NUM_PIXELS):
        pixels[p_idx] = pixel_black
    pixels.show()

pixels_off()

while True:
    ### Flash onboard LED five times to signify start
    for _ in range(5):
        display.show(Image.HEART)
        time.sleep(1)
        display.clear()
        time.sleep(1)

    ### Now start the simultaneous pixel lighting and servo movement
    start_pos = SERVO_MIN
    end_pos = SERVO_MAX
    old_start_pos = end_pos
    degree_step = 3
    reps = 1
    duration_s = 2
    for idx in range(NUM_PIXELS):
        if idx < RGBPIXLIM:
            pixels[idx] = pixel_white
            pixels.show()

        step_pause_s = degree_step * duration_s / reps / 180
        for swing in range(reps):
            pos = start_pos
            while pos != end_pos:
                myservo.write_angle(pos)
                time.sleep(step_pause_s)

                ### Move the servo position but keep within limits
                if end_pos > start_pos:
                    pos += degree_step
                    if pos > SERVO_MAX:
                        pos = SERVO_MAX
                else:
                    pos -= degree_step
                    if pos < SERVO_MIN:
                        pos = SERVO_MIN

            ### Swap start and end servo positions
            old_start_pos = start_pos
            start_pos = end_pos
            end_pos = old_start_pos

        ### For a ring of 12 every 4 pixels double the number of servo movements
        if idx % SERVO_SPEED_LOOPS == SERVO_SPEED_LOOPS - 1:
            if HARDWARE == "V2":
                reps *= 2
                degree_step *= 2

    ### Test complete
    pixels_off()
    myservo.turn_off()
    time.sleep(10)
