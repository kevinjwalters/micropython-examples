### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


import math

_M_CONV = 64.0
_Z_CONV = 255.49

class HaloBackground:
    MICROBIT_CHANGED = 0x01
    HALO_CHANGED = 0x02


    def __init__(self, zip_, mdisplaylist, brightness=1, options=None):
        self._zip = zip_
        self._mdisplaylist = mdisplaylist
        self._last_render_tms = None
        self._options = options if options is not None else {}

        self._brightness = None
        self.displayed = 0  ### bit mask of localtime fields shown by background

        ### list of values, e.g. 9 for micro:bit display, [20, 20, 20] for ZIP LED
        self._palette = []
        self._palette_bri = []  ### brightness adjusted values

        ##self._start_time_lt = None
        ##self._start_time_ms = None
        ##self._start_time_tms = None

        self.brightness = brightness  ### This can be modified later

        if type(self) == HaloBackground:  ### pylint: disable=unidiomatic-typecheck
            raise ValueError("Needs to be sub-classed")

    ### Convert micro:bit pixel values between 0 and 9 to normalised values
    @classmethod
    def m_pix_norm(cls, value, bri):
        ### 0.15 at full brightness will be max value on micro:bit
        return math.sqrt(value / bri / _M_CONV)

    ### Convert ZIP LED pixel values between 0 and 255 to normalised values
    @classmethod
    def z_pix_norm(cls, value, bri):
        return math.sqrt(value / bri / _Z_CONV)

    ### Convert values between 0.0 and 1.0 to a value for micro:bit display
    @classmethod
    def m_bri_norm(cls, value, bri):
        ### 0.15 at full brightness will be max value on micro:bit
        return min(9, round(value * bri * _M_CONV))

    ### Convert values between 0.0 and 1.0 to a value for ZIP LEDmicro:bit display
    @classmethod
    def z_bri_norm(cls, value, bri):
        return min(255, round(value * value * bri * _Z_CONV))

    def render(self, local_time, milliseconds, ticks_ms):
        ### This should return MICROBIT_CHANGED | HALO_CHANGED
        raise NotImplementedError

    def start(self, local_time, milliseconds, ticks_ms):
        ### pylint: disable=attribute-defined-outside-init
        self._start_time_lt = local_time
        self._start_time_ms = milliseconds
        self._start_time_tms = ticks_ms

    def stop(self):
        self._last_render_tms = None

    def run_time(self, local_time, milliseconds):
        ### TODO complete this for years
        return ((local_time[7] - self._start_time_lt[7]) * 86400
                 + (local_time[3] - self._start_time_lt[3]) * 3600
                 + (local_time[4] - self._start_time_lt[4]) * 60
                 + local_time[5] - self._start_time_lt[5] + milliseconds / 1000.0)

    def palette_add(self, value):
        last_idx = len(self._palette)
        self._palette.append(value)
        try:
            self._palette_bri.append([self.z_bri_norm(v, self._brightness) for v in value])
        except TypeError:
            self._palette_bri.append(self.m_bri_norm(value, self._brightness))
        return last_idx

    def palette(self, idx):
        return self._palette_bri[idx]

    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, value):
        if self._brightness != value:
            self._brightness = value
            for idx in range(len(self._palette)):
                ### Use inplace updates to avoid creating new lists
                try:
                    for c_idx in range(len(self._palette[idx])):
                        self._palette_bri[idx][c_idx] = self.z_bri_norm(self._palette[idx][c_idx], self._brightness)
                except TypeError:
                    self._palette_bri[idx] = self.m_bri_norm(self._palette[idx], self._brightness)
