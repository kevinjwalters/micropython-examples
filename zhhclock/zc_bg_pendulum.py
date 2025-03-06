### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


import math

from zc_bg import HaloBackground
from zc_utils import get_pixels_near_angle


class Pendulum(HaloBackground):
    def __init__(self, zip_, mdisplaylist, options=None):
        super().__init__(zip_, mdisplaylist, options)

        if self._options.get("length") is None:
            ### a pendulum just under one metre for 2s period
            self._length = 0.9939608115313338
        else:
            self._length = self._options.get("length")

        if self._options.get("start_angle") is None:
            ### a pendulum just under one metre for 2s period
            self._start_angle = 1/12 * math.pi * 2
        else:
            self._start_angle = self._options.get("start_angle") / 180.0 * 2 * math.pi

        self._gravity = 9.81
        self._coef = math.sqrt(self._gravity / self._length)


    def render(self, local_time, milliseconds, ticks_ms):
        t_s = self.run_time(local_time, milliseconds)
        ### Classic small angle approximation
        angle = self._start_angle * math.cos(self._coef * t_s)

        z_bri = 10
        il_radius = 0.22
        for z_idx, bri in get_pixels_near_angle(math.pi + angle, il_radius):
            self._zip[z_idx] = (round(bri * bri * z_bri), 0, 0)

        return self.HALO_CHANGED
