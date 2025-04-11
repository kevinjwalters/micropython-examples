### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


from rainbow import wavelengthToRGBtuple

from zc_bg import HaloBackground
from zc_utils import Z_LED_POS


class FallingRainbow(HaloBackground):
    def render(self, local_time, milliseconds, ticks_ms):
        secs = self.run_time(local_time, milliseconds)

        ### Use symmetry of circular LED layout to set other side using same value
        for idx in range(len(self._zip) // 2 + 1):
            wavelength_nm = 380 + (Z_LED_POS[idx][1] + 1.0) * 150 - (secs % 60 - 30) * (380/30)
            r, g, b = wavelengthToRGBtuple(wavelength_nm)
            if wavelength_nm < 405.0:
                b = min(b, r)  ### blue seems too high here, cap to red level

            rgb_col = (int(r * 16), int(g * 16), int(b * 16))
            self._zip[idx] = rgb_col
            if idx != 0:
                self._zip[len(self._zip) - idx] = rgb_col

        return self.HALO_CHANGED
