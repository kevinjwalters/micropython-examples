### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


from rainbow import wavelengthToRGBtuple

from zc_bg import HaloBackground
from zc_utils import SECOND


class RotatingRainbow(HaloBackground):
    def __init__(self, zip_, mdisplaylist, brightness=1, options=None):
        super().__init__(zip_, mdisplaylist,  brightness, options)
        self.displayed = 1 << SECOND


    def render(self, local_time, milliseconds, ticks_ms):
        secs = local_time[SECOND]

        cbri = 0.80 * self.brightness
        for idx in range(len(self._zip)):
            offset_idx = (idx - secs ) % len(self._zip)
            rgb_n = wavelengthToRGBtuple(700 - 295 * offset_idx / len(self._zip))
            self._zip[idx] = (self.z_bri_norm(rgb_n[0], cbri),
                              self.z_bri_norm(rgb_n[1], cbri),
                              self.z_bri_norm(rgb_n[2], cbri))

        return self.HALO_CHANGED
