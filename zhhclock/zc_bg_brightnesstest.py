### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


from zc_bg import HaloBackground


class BrightnessTest(HaloBackground):
    def render(self, local_time, milliseconds, ticks_ms):
        for idx in range(min(len(self._zip), 255)):
            self._zip[idx] = (idx, 0, 0)

        for idx in range(9 + 1):
            self._mdisplaylist[idx] = idx

        return self.MICROBIT_CHANGED | self.HALO_CHANGED
