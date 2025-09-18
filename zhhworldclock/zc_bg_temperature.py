### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


from zc_bg import HaloBackground


class Temperature(HaloBackground):
    ### Mid point will be 20 degrees Celsius
    MIN_TEMP = 5.0
    MAX_TEMP = 35.0


    def __init__(self, zip_, mdisplaylist, brightness=1, options=None):
        super().__init__(zip_, mdisplaylist, brightness, options)

        self._function = self._options.get("function")
        self._temperature = self._function()
        self._last_s = -1


    def render(self, local_time, milliseconds, ticks_ms):
        ### Update the temperature once a second
        if local_time[5] != self._last_s:
            self._temperature = 0.875 * self._temperature + 0.125 * self._function()
            self._last_s = local_time[5]

        bottom_idx = len(self._zip) // 2
        first_idx = max(0, min(bottom_idx, round(bottom_idx
                                                * (self.MAX_TEMP - self._temperature)
                                                / (self.MAX_TEMP - self.MIN_TEMP))))

        ### Set pixels from top to bottom to represent temperature level
        ### With red colour on top half and blue on bottom half.
        cbri = 0.60 * self.brightness
        for idx in range(first_idx, bottom_idx + 1):
            ratio = idx / bottom_idx
            r_lvl = self.z_bri_norm((max(0.0, 2.0 * (0.56 - ratio))) ** 0.4, cbri)
            b_lvl = self.z_bri_norm((max(0.0, 2.0 * (ratio - 0.49))) ** 0.4, cbri)
            ### For night/dim mode ensure minimum brightness of 2
            rgb_col = (max(2, r_lvl) if r_lvl >= b_lvl else r_lvl,
                       0,
                       max(2, b_lvl) if b_lvl > r_lvl else b_lvl)
            self._zip[idx] = rgb_col
            if idx != 0:
                self._zip[len(self._zip) - idx] = rgb_col
        return self.HALO_CHANGED
