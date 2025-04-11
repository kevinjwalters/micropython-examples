### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT

from microbit import Image

from zc_bg import HaloBackground
from zc_utils import HOUR


class Microbit(HaloBackground):
    def render(self, local_time, milliseconds, ticks_ms):
        hh = local_time[HOUR]
        clock_hhand_img = getattr(Image, "CLOCK" + str(hh % 12))
        ### This relies on str() conversion which isn't good practice
        self._mdisplaylist[:] = [ord(x) - ord("0") for x in str(clock_hhand_img) if x.isdigit()]

        return self.MICROBIT_CHANGED
