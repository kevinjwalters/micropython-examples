### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT

from microbit import i2c, sleep
import radio
import utime

from zc_clockcomms import ClockComms, MsgTimeWms
from zc_comboclock import ComboClock


radio.off()

master = True

if master:
    import mcp7940

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
    mcp = mcp7940.MCP7940(ei2c)
    clock = ComboClock(mcp)


comms = ClockComms(radio)
last_tb_ms = utime.ticks_ms()

while True:
    if master:
        rtc_time, ss_ms, ticks_ms = clock.time_with_ms_and_ticks
        if utime.ticks_diff(utime.ticks_ms(), last_tb_ms) > 10_000:
            print("TX", rtc_time, ss_ms)
            comms.on()
            comms.broadcast_msg(MsgTimeWms(rtc_time, ss_ms))
            last_tb_ms = utime.ticks_ms()
            comms.off()
    else:
        msghdr = comms.receive_msg_full()
        if msghdr is not None:
            msg, rssi, rx_tus, src, dst = msgandhdr
            print(msg)
        sleep(15)
