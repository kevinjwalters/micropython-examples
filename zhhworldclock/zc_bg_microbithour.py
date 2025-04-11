### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT

from microbit import Image

from zc_bg import HaloBackground
from zc_utils import HOUR


class MicrobitHour(HaloBackground):
    def render(self, local_time, milliseconds, ticks_ms):
        hh = local_time[HOUR]
        clock_hhand_img = getattr(Image, "CLOCK" + str(hh % 12))

        ##self._mdisplaylist[:] = [ord(x) - ord("0") for x in str(clock_hhand_img) if x.isdigit()]
        ### This relies on str() representation which isn't good practice
        idx = 0
        for char in str(clock_hhand_img):
            if char.isdigit():
                self._mdisplaylist[idx] = ord(char) - ord("0")
                idx += 1

        return self.MICROBIT_CHANGED
