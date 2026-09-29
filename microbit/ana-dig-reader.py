### ana-dig-reader v1.5
### Respond to simple serial commands with analogue samples

### copy this file (minus comments at top) to https://python.microbit.org/

### MIT License

### Copyright (c) 2026 Kevin J. Walters

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

### SPDX-FileCopyrightText: 2026 Kevin J. Walters

### Copyright (c) 2026 Kevin J. Walters


import os
import time

from microbit import *

BLOCKING = True

SOFTWARE_NAME = "ana-dig-reader"
SOFTWARE_VERSION = "1.5"

BOARD_MANU = "BBC"
machine = os.uname().machine
with_pos = machine.find(" with ")
BOARD_NAME = machine[:with_pos]
BOARD_MCU = machine[with_pos + 6:]

ADC_RESOLUTION = 10

ADC_VREF = 3.3
ANALOGUE_PIN = "P1"


SERIAL_TX_PIN = pin15
SERIAL_RX_PIN = pin14
GPIO_PIN = pin1

SERIAL_BAUDRATE = 38400
TX_BYTE_US = 1000 * 1000 * (1 + 8 + 1) // SERIAL_BAUDRATE

READV_ANA_CMD = "C"
INFO_CMD = "I"
COUNT_OFFSET = ord(" ")


def flash(f_count):
    display.on()
    for _ in range(f_count):
        display.show(Image.HEART)
        sleep(300)
        display.clear()
        sleep(300)
    display.off()

def get_sample_analogue():
    return GPIO_PIN.read_analog()

def uart_write(buf, block=BLOCKING):
    if block:
        tx_start_us = time.ticks_us()
        uart.write(buf)
        tx_delay_us = TX_BYTE_US * len(buf)
        while time.ticks_diff(time.ticks_us(), tx_start_us) < tx_delay_us:
            pass
    else:
        serial.write(buf)

sleep(10 * 1000)
flash(2)


uart.init(baudrate=SERIAL_BAUDRATE, tx=SERIAL_TX_PIN, rx=SERIAL_RX_PIN)

one_byte_buf = bytearray(1)
while True:
    rx_count = uart.readinto(one_byte_buf)
    value = None
    if rx_count is not None:
        cmd = chr(one_byte_buf[0])
        if cmd == READV_ANA_CMD:
            one_byte_buf[0] = COUNT_OFFSET
            rx_count = uart.readinto(one_byte_buf)
            count = one_byte_buf[0] - COUNT_OFFSET
            if count > 0:
                for _ in range(count - 1):
                    uart_write("{:05d} ".format(get_sample_analogue()))
                uart_write("{:05d}\n".format(get_sample_analogue()))
            else:
                value = ""
        elif cmd == INFO_CMD:
            flash(3)
            value = ('"INFO","{:s}","{:s}",'.format(SOFTWARE_NAME, SOFTWARE_VERSION) +
                     '"{:s}","{:s}","{:s}",'.format(BOARD_MANU, BOARD_NAME, BOARD_MCU) +
                     '"MicroPython",' +
                     '"adc_bits={:d};aref={:.1f};'.format(ADC_RESOLUTION, ADC_VREF) +
                     'input_pin={:s};read=raw"'.format(ANALOGUE_PIN))
    if value is not None:
        uart_write("{:s}\n".format(value))
