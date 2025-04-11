### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT

import array
import random

import utime

from zc_bg import HaloBackground
from zc_utils import M_LED_POS, M_LED_SPACING, Z_LED_POS, Z_LED_SPACING, get_m_pixels_through_x, get_z_pixels_through_x, vertical_line_near_pixel


_DP_X = 0
_DP_Y = 1
_DP_SPEED = 2
_DP_TRAIL_LENGTH = 3
_DP_HEAD_BRI = 4


class DigitalRain(HaloBackground):
    def __init__(self, zip_, mdisplaylist, options=None):
        super().__init__(zip_, mdisplaylist, options)

        self._max_drops = 12
        ### This is a flattened list of [x, y, speed, trail_length, head_bri]
        self._rain_drops = array.array('f', [0.0] * (5 * self._max_drops))

        self._last_run_tms = utime.ticks_ms()

    @classmethod
    def _raindrops_prob(cls, duration_s):
        selecta = random.random()
        count_per_s = ((14 + 2 * random.random()) if selecta < 0.7
                       else (15 * 2 * random.random()) if selecta < 0.900
                             else (30 * 2 * random.random() if selecta < 0.975
                                   else (90 * 2 * random.random())))
        return round(count_per_s * duration_s)


    def _removeadddrops(self, dur_s):
        for drop_no in range(self._max_drops):
            base_idx = drop_no * 5
            if self._rain_drops[base_idx + _DP_HEAD_BRI] == 0.0:
                continue
            self._rain_drops[base_idx + _DP_Y] += self._rain_drops[base_idx + _DP_SPEED] * dur_s
            if self._rain_drops[base_idx + _DP_Y] - self._rain_drops[base_idx + _DP_TRAIL_LENGTH] > 1.1:
                self._rain_drops[base_idx + _DP_HEAD_BRI] = 0.0

        ### add new drops based on probability and time elasped since last addition
        new_drop_count = self._raindrops_prob(dur_s)
        drops_added = 0
        for drop_no in range(self._max_drops):
            base_idx = drop_no * 5
            if self._rain_drops[base_idx + _DP_HEAD_BRI] != 0.0:
                continue

            self._rain_drops[base_idx + _DP_X] = random.uniform(-1.05, 1.05)
            self._rain_drops[base_idx + _DP_Y] = random.uniform(-1, -1.1)
            self._rain_drops[base_idx + _DP_SPEED] = random.uniform(0.2, 0.6) if random.random() < 0.9 else random.uniform(0.1, 1.5)
            self._rain_drops[base_idx + _DP_TRAIL_LENGTH] = random.uniform(0.3, 1.5) * 0.5 + random.uniform(0.7, 1.0) * 0.5
            self._rain_drops[base_idx + _DP_HEAD_BRI] = random.randint(60, 255)
            drops_added += 1
            if drops_added >= new_drop_count:
                break

    def render(self, local_time, milliseconds, ticks_ms):
        ### pylint: disable=too-many-locals
        ### move existing drops and remove any drops that have fallen
        ### off the display by setting brightness to zero
        delta_s = utime.ticks_diff(ticks_ms, self._last_run_tms) / 1e3
        self._removeadddrops(delta_s)

        ### Render rain drops
        ### Use a max() strategy to combine "droplets" on LEDs
        z_bri = 30
        il_radius = 0.08
        for drop_no in range(self._max_drops):
            x, y, speed, trail_length, head_bri = self._rain_drops[drop_no * 5:(drop_no * 5 + 5)]
            if head_bri == 0.0:
                continue

            for p_idx in get_z_pixels_through_x(x):
                distances = vertical_line_near_pixel(Z_LED_SPACING, x, y, y - trail_length, *Z_LED_POS[p_idx])
                if distances:
                    trail_bri = distances[1] * distances[1] * 0.75 + 0.25
                    brightness = (trail_bri * head_bri
                                  * max(0, (il_radius - distances[0])) / il_radius)
                    if brightness > 0.0:
                        ### TODO - perhaps match up brightness between the micro:bit V2 and self._zip
                        self._zip[p_idx] = (max(round(brightness * brightness / 65535.0 * z_bri), self._zip[p_idx][0]), 0, 0)

            for m_idx in get_m_pixels_through_x(x):
                distances = vertical_line_near_pixel(M_LED_SPACING, x, y, y - trail_length, *M_LED_POS[m_idx])
                if distances:
                    trail_bri = distances[1] * distances[1] * 0.75 + 0.25
                    brightness = (trail_bri * head_bri
                                  * max(0, (il_radius - distances[0])) / il_radius)
                    if brightness > 0.0:
                        self._mdisplaylist[m_idx] = max(round(brightness / 255.0 * 9), self._mdisplaylist[m_idx])

        self._last_run_tms = ticks_ms
        ### TODO could count the changes
        return self.MICROBIT_CHANGED | self.HALO_CHANGED

    def stop(self):
        ### "Remove" all the rain drops by setting brightness to zero
        for drop_no in range(self._max_drops):
            self._rain_drops[drop_no * 5 + _DP_HEAD_BRI] = 0.0
