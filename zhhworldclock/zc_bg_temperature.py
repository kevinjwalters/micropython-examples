### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


from zc_bg import HaloBackground


class Temperature(HaloBackground):
    MIN_TEMP = 5.0
    MAX_TEMP = 35.0


    def __init__(self, zip_, mdisplaylist, options=None):
        super().__init__(zip_, mdisplaylist, options)

        self._function = self._options.get("function")
        self._temperature = self._function()
        self._last_s = -1


    def render(self, local_time, milliseconds, ticks_ms):
        ### TODO only update every second
        if local_time[5] != self._last_s:
            self._temperature = 0.875 * self._temperature + 0.125 * self._function()
            self._last_s = local_time[5]

        bottom_idx = len(self._zip) // 2
        temp_idx = max(0, min(bottom_idx, round(bottom_idx
                                                * (self.MAX_TEMP - self._temperature)
                                                / (self.MAX_TEMP - self.MIN_TEMP))))
        for idx in range(temp_idx, bottom_idx + 1):
            ratio = idx / bottom_idx
            #sigmoid = 1/(1+ math.exp(0.0 - (5 * (ratio - 0.5))))
            #rgb_col = (int((1.0 - ratio) * 16), 0, int(ratio * 16))
            red_lvl = int(max(0, 1.666 * (0.6 - ratio)) * 16)
            rgb_col = (red_lvl,
                       0,
                       int(max(0, 1.666 * (ratio - 0.4)) * 16) if red_lvl == 0 else 0)
            self._zip[idx] = rgb_col
            if idx != 0:
                self._zip[len(self._zip) - idx] = rgb_col
        return self.HALO_CHANGED
