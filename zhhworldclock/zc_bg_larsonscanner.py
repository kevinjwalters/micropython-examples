### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


from zc_bg import HaloBackground
from zc_utils import M_LED_POS, Z_LED_POS, get_m_pixels_through_x, get_z_pixels_through_x


class LarsonScanner(HaloBackground):
    def render(self, local_time, milliseconds, ticks_ms):
        ### pylint: disable=too-many-locals
        ct_s = self.run_time(local_time, milliseconds) % 4
        direction = 1
        if ct_s >= 2.0:
            direction = -1
            ct_s -= 2.0

        x1 = (ct_s / 0.90909 - 1.1)
        if direction < 0:
            x1 = 0.0 - x1
        x2 = x1 - 0.075 * direction
        x3 = x1 - 0.150 * direction

        il_radius = 0.08
        gbri = self.brightness
        ### This can exceed the brightness of 1.0
        ### [zm]_bri_norm will cap values
        for x in (x1, x2, x3):
            for p_idx in get_z_pixels_through_x(x):
                distance = abs(Z_LED_POS[p_idx][0] - x)
                brightness = (max(0, (il_radius - distance)) / il_radius) * 1.15
                if brightness > 0.0:
                    ### Set red level on ZIP LEDs
                    self._zip[p_idx] = (max(self.z_bri_norm(brightness, gbri),
                                            self._zip[p_idx][0]),
                                        0, 0)

            for m_idx in get_m_pixels_through_x(x):
                distance = abs(M_LED_POS[m_idx][0] - x)
                brightness = (max(0, (il_radius - distance)) / il_radius) * 1.5
                if brightness > 0.0:
                    self._mdisplaylist[m_idx] = max(self.m_bri_norm(brightness, gbri),
                                                    self._mdisplaylist[m_idx])
            gbri /= 2.0

        return self.MICROBIT_CHANGED | self.HALO_CHANGED
