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
        x2 = x1 - 0.075 * dir
        x3 = x1 - 0.150 * dir

        z_bri = 30
        m_bri = 255
        il_radius = 0.08
        for x in (x1, x2, x3):
            for p_idx in get_z_pixels_through_x(x):
                distance = abs(Z_LED_POS[p_idx][0] - x)
                brightness = (max(0, (il_radius - distance)) / il_radius)
                if brightness > 0.0:
                    ### TODO - perhaps match up brightness between the micro:bit V2 and self._zip
                    self._zip[p_idx] = (max(round(brightness * brightness * z_bri), self._zip[p_idx][0]), 0, 0)

            for m_idx in get_m_pixels_through_x(x):
                distance = abs(M_LED_POS[m_idx][0] - x)
                brightness = (max(0, (il_radius - distance)) / il_radius)
                if brightness > 0.0:
                    self._mdisplaylist[m_idx] = max(round(brightness * m_bri), self._mdisplaylist[m_idx])

            z_bri /= 2
            m_bri /= 2

        return self.MICROBIT_CHANGED | self.HALO_CHANGED
