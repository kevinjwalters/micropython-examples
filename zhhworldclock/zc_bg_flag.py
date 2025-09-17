### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT

import math

from zc_bg import HaloBackground
from zc_utils import HOUR, SECOND, M_LED_POS, Z_LED_POS


class Flag(HaloBackground):
    ### 0 black, 1 red, 2 green, 3 white
    WELSH_FLAG_60 = tuple((3,) * 8 + (1,) * 3 + (3,1,3,1,3,1,2,1,1,2,2,2,1,1)
                          + (2,) * 11 + (1,2,1,1,2,1,1,1,2,2) + (3,) * 3
                          + (1, 1, 3, 0, 1, 3, 3, 1) + (3,) * 3)
    #WELSH_FLAG_COLS = ((0, 0, 0),
    #                   (200//10, 16//30, 46//30),
    #                   (0, 177//10, 64//10),
    #                   (255//13, 255//13, 255//13))

    #UKRAINE_BLUE   = (0, 87//8, 183//6)
    #UKRAINE_GOLD = (255//11, 215//11, 0)

    #POLAND_WHITE = (255//13, 255//13, 255//13)
    #POLAND_CRIMSON = (212//15, 33//20, 61//20)

    ZIPCOL = {"wales":   ([0, 0, 0],
                          [200//10, 16//30, 46//30],
                          [0, 177//10, 64//10],
                          [255//13, 255//13, 255//13]
                          ),
              "ukraine": ([0, 87//8, 183//6],
                          [255//11, 215//11, 0]
                          ),
              "poland":  ([255//13, 255//13, 255//13],
                          [212//15, 33//20, 61//20]
                         )
             }
    ### Convert the r,g,b pixel values at brightness 0.1 into normalised
    ### brightness values
    for _, cols in ZIPCOL.items():
        for col in cols:
            col[0] = HaloBackground.z_pix_norm(col[0], 0.1)
            col[1] = HaloBackground.z_pix_norm(col[1], 0.1)
            col[2] = HaloBackground.z_pix_norm(col[2], 0.1)

    def __init__(self, zip_, mdisplaylist, brightness=1, options=None):
        super().__init__(zip_, mdisplaylist, brightness, options)

        self._pal_bidx = {}
        self._flags = []
        try:
            flags = options.get("flag").split()
        except AttributeError:
            flags = ["ukraine"]

        for flag in flags:
            try:
                bfn = getattr(self, "flag_" + flag)
                self._flags.append(bfn)
                citer = iter(self.ZIPCOL[flag])
                col0 = next(citer)
                self._pal_bidx[flag] = self.palette_add(col0)
                for col in citer:
                    self.palette_add(col)
            except AttributeError:
                pass

    def _flag_h2(self, top_col, bottom_col):
        quarter = len(self._zip) // 4

        colour = top_col
        for idx in range(0, quarter + 1):
            self._zip[idx] = colour
        for idx in range(quarter * 3, len(self._zip)):
            self._zip[idx] = colour

        colour = bottom_col
        for idx in range(quarter + 1, quarter * 3):
            self._zip[idx] = colour

    def flag_ukraine(self):
        bidx = self._pal_bidx["ukraine"]
        self._flag_h2(self.palette(bidx), self.palette(bidx + 1))
        return self.HALO_CHANGED

    def flag_poland(self):
        bidx = self._pal_bidx["poland"]
        self._flag_h2(self.palette(bidx), self.palette(bidx + 1))
        return self.HALO_CHANGED

    def flag_wales(self):
        bidx = self._pal_bidx["wales"]
        for idx in range(len(self._zip)):
            c_idx = self.WELSH_FLAG_60[idx * len(self.WELSH_FLAG_60)
                                       // len(self._zip)]
            self._zip[idx] = self.palette(bidx + c_idx)

        ### Off substitues for white on two pixels top left
        m_bri_TOCALC = self.m_bri_norm(1.0, self.brightness)
        for idx in range(len(self._mdisplaylist)):
            self._mdisplaylist[idx] = 0 if idx in (0, 5) else m_bri_TOCALC

        return self.HALO_CHANGED | self.MICROBIT_CHANGED


    @classmethod
    def _wind_ripple_mod(cls, x_pos):
        zero_to_one = 1.0 - ((x_pos + 1.0) / 2.0)
        if 0.0 <= zero_to_one <= 1.0:
            modulate = (math.sin(zero_to_one * zero_to_one * 3.0 * 2.0 * math.pi)
                        * math.sin(zero_to_one * math.pi))
        else:
            modulate = 0.0
        return modulate


    def _wind_ripple(self, ripple_time, total, changes_):
        ### pylint: disable=too-many-locals
        shift_x = 4.0 * ripple_time / total - 2.0

        if changes_ & self.HALO_CHANGED:
            ### Modulate the values on the Halo taking advantage of symmetry
            half_len = len(self._zip) // 2
            for idx in range(len(self._zip) // 4, len(self._zip) * 3 // 4 + 1):
                led_x = Z_LED_POS[idx * 2]
                moving_x = 0 - led_x + shift_x
                col_p1 = self._wind_ripple_mod(moving_x) / 1.9 + 1.0
                r, g, b = self._zip[idx]
                self._zip[idx] = (min(255, max(0, round(r * col_p1))),
                                  min(255, max(0, round(g * col_p1))),
                                  min(255, max(0, round(b * col_p1))))
                tophalf_idx = (half_len - idx) % len(self._zip)
                if idx != tophalf_idx:
                    r, g, b = self._zip[tophalf_idx]
                    self._zip[tophalf_idx] = (min(255, max(0, round(r * col_p1))),
                                              min(255, max(0, round(g * col_p1))),
                                              min(255, max(0, round(b * col_p1))))

        if changes_ & self.MICROBIT_CHANGED:
            ### Modulate micro:bit display using values calculated per column
            for m_idx in range(0, 5):
                led_x = M_LED_POS[m_idx * 2]
                moving_x = 0 - led_x + shift_x
                col_p1 = self._wind_ripple_mod(moving_x) / 1.9 + 1.0
                for y_off in range(0, 25, 5):
                    self._mdisplaylist[m_idx + y_off] = min(9,
                                                            max(0,
                                                            round(self._mdisplaylist[m_idx + y_off]
                                                                  * col_p1)))


    def render(self, local_time, milliseconds, ticks_ms):
        changes = self._flags[local_time[HOUR] % len(self._flags)]()
        if 0 <= local_time[SECOND] <= 7:
            self._wind_ripple(local_time[SECOND] + milliseconds / 1000.0, 8.0, changes)
        return changes
