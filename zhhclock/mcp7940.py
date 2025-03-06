### This is https://github.com/salty-muffin/micropython-mcp7940/blob/master/mcp7940.py
### which is based on https://github.com/tinypico/micropython-mcp7940/blob/master/mcp7940.py
### based on https://github.com/mattytrentini/micropython-mcp7940/blob/master/mcp7940.py
### with fixes from https://github.com/PaulskPt/Circuitpython_MCP7940

### Copyright (c) 2019 Matt Trentini, Seon Rozenblum, Paulus H.J. Schulinck, Zeno Gries

### SPDX-License-Identifier: MIT


"""incorporated fixes from the circuitpython port of this library: https://github.com/PaulskPt/Circuitpython_MCP7940"""

from micropython import const


class MCP7940:
    """
    Example usage:

        # Read time
        mcp = MCP7940(i2c)
        time = mcp.time # Read time from MCP7940
        is_leap_year = mcp.is_leap_year() # Is the year in the MCP7940 a leap year?

        # Set time
        ntptime.settime() # Set system time from NTP
        mcp.time = utime.localtime() # Set the MCP7940 with the system time
    """

    ADDRESS = const(0x6F)
    RTCSEC = 0x00  # RTC seconds register
    RTCWKDAY = 0x03  # RTC Weekday register
    ST = 7  # Status bit
    VBATEN = 3  # External battery backup supply enable bit

    def __init__(self, i2c, battery_enabled=True):
        self._i2c = i2c
        if battery_enabled:
            self.battery_backup_enable(1)
        else:
            self.battery_backup_enable(0)
        self._battery_enabled = battery_enabled
        self._running = False

    def start(self):
        self._set_bit(MCP7940.RTCSEC, MCP7940.ST, 1)
        self._running = True

    def stop(self):
        self._set_bit(MCP7940.RTCSEC, MCP7940.ST, 0)
        self._running = False

    def is_started(self):
        return self._read_bit(MCP7940.RTCSEC, MCP7940.ST)

    def battery_backup_enable(self, enable):
        self._set_bit(MCP7940.RTCWKDAY, MCP7940.VBATEN, int(enable))

    def is_battery_backup_enabled(self):
        return self._read_bit(MCP7940.RTCWKDAY, MCP7940.VBATEN)

    def _set_bit(self, register, bit, value):
        """Set only a single bit in a register. To do so, need to read
        the current state of the register and modify just the one bit.
        """
        mask = 1 << bit
        current = self._i2c.readfrom_mem(MCP7940.ADDRESS, register, 1)
        updated = (current[0] & ~mask) | ((value << bit) & mask)
        self._i2c.writeto_mem(MCP7940.ADDRESS, register, bytes([updated]))

    def _read_bit(self, register, bit):
        register_val = self._i2c.readfrom_mem(MCP7940.ADDRESS, register, 1)
        return (register_val[0] & (1 << bit)) >> bit

    def set_trim(self, value, corse=False):
        self._set_bit(0x07, 2, int(corse))
        sign = 1
        if value < 0:
            sign = 0
            value *= -1
        self._i2c.writeto_mem(
            MCP7940.ADDRESS, 0x08, bytes([value & 0b1111111 | sign << 7])
        )

    def get_trim(self):
        trim = self._i2c.readfrom_mem(MCP7940.ADDRESS, 0x08, 1)[0]
        value = trim & 0b1111111
        if (trim & (1 << 7)) >> 7:
            return value
        else:
            return -value

    @property
    def time(self):
        return self._get_time()

    @time.setter
    def time(self, t):
        """
        >>> import time
        >>> time.localtime()
        (2019, 6, 3, 13, 12, 44, 0, 154)
        # 1:12:44pm on Monday (0) the 3 Jun 2019 (154th day of the year)
        """
        year, month, date, hours, minutes, seconds, weekday, yearday = t
        # Reorder
        time_reg = [seconds, minutes, hours, weekday + 1, date, month, year % 100]

        reg_filter = (0x7F, 0x7F, 0x3F, 0x07, 0x3F, 0x3F, 0xFF)
        # t = bytes([MCP7940.bcd_to_int(reg & filt) for reg, filt in zip(time_reg, reg_filter)])
        t = [
            (MCP7940.int_to_bcd(reg) & filt) for reg, filt in zip(time_reg, reg_filter)
        ]
        # Note that some fields will be overwritten that are important!
        # fixme!
        running = self._running
        if running:
            self.stop()

        self._i2c.writeto_mem(MCP7940.ADDRESS, 0x00, bytes(t))

        self.battery_backup_enable(int(self._battery_enabled))

        if running:
            self.start()

    @property
    def alarm1(self):
        return self._get_time(start_reg=0x0A)

    @alarm1.setter
    def alarm1(self, t):
        (
            _,
            month,
            date,
            hours,
            minutes,
            seconds,
            weekday,
            _,
        ) = t  # Don't need year or yearday
        # Reorder
        time_reg = [seconds, minutes, hours, weekday + 1, date, month]
        reg_filter = (0x7F, 0x7F, 0x3F, 0x07, 0x3F, 0x3F)  # No year field for alarms
        t = [
            (MCP7940.int_to_bcd(reg) & filt) for reg, filt in zip(time_reg, reg_filter)
        ]
        self._i2c.writeto_mem(MCP7940.ADDRESS, 0x0A, bytes(t))

    @property
    def alarm2(self):
        return self._get_time(start_reg=0x11)

    @alarm2.setter
    def alarm2(self, t):
        (
            _,
            month,
            date,
            hours,
            minutes,
            seconds,
            weekday,
            _,
        ) = t  # Don't need year or yearday
        # Reorder
        time_reg = [seconds, minutes, hours, weekday + 1, date, month]
        reg_filter = (0x7F, 0x7F, 0x3F, 0x07, 0x3F, 0x3F)  # No year field for alarms
        t = [
            (MCP7940.int_to_bcd(reg) & filt) for reg, filt in zip(time_reg, reg_filter)
        ]
        self._i2c.writeto_mem(MCP7940.ADDRESS, 0x11, bytes(t))

    @classmethod
    def bcd_to_int(cls, bcd):
        """Expects a byte encoded wtih 2x 4bit BCD values."""
        # Alternative using conversions: int(str(hex(bcd))[2:])
        return (bcd & 0xF) + (bcd >> 4) * 10

    @classmethod
    def int_to_bcd(cls, i):
        return (i // 10 << 4) + (i % 10)

    @classmethod
    def is_leap_year(cls, year):
        """https://stackoverflow.com/questions/725098/leap-year-calculation"""
        if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0:
            return True
        return False

    def _get_time(self, start_reg=0x00):
        num_registers = 7 if start_reg == 0x00 else 6
        time_reg = self._i2c.readfrom_mem(
            MCP7940.ADDRESS, start_reg, num_registers
        )  # Reading too much here for alarms
        reg_filter = (0x7F, 0x7F, 0x3F, 0x07, 0x3F, 0x3F, 0xFF)[:num_registers]
        t = [MCP7940.bcd_to_int(reg & filt) for reg, filt in zip(time_reg, reg_filter)]
        # Reorder
        t2 = (t[5], t[4], t[2], t[1], t[0], t[3] - 1)
        t = (t[6] + 2000,) + t2 + (0,) if num_registers == 7 else t2
        # now = (2019, 7, 16, 15, 29, 14, 6, 167)  # Sunday 2019/7/16 3:29:14pm (yearday=167)
        # year, month, date, hours, minutes, seconds, weekday, yearday = t
        # time_reg = [seconds, minutes, hours, weekday, date, month, year % 100]

        return t
