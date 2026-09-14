### ana-dig-reader v1.3
### Respond to simple serial commands with digital or analogue gpio

### Copyright (c) 2026 Kevin J. Walters


import os

from microbit import *


SOFTWARE_NAME = "ana-dig-reader"
SOFTWARE_VERSION = "1.3"

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


sleep(10 * 1000)
flash(2)


uart.init(baudrate=38400, tx=SERIAL_TX_PIN, rx=SERIAL_RX_PIN)

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
                    uart.write("{:05d} ".format(get_sample_analogue()))
                uart.write("{:05d}\n".format(get_sample_analogue()))
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
        uart.write("{:s}\n".format(value))
