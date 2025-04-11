### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


from zc_bg import HaloBackground


### This is mainly intended to aid analysis and debugging of synchronisation across multiple clocks
class Milliseconds(HaloBackground):
    def render(self, local_time, milliseconds, ticks_ms):
        w_quarter = milliseconds % 500 // 125
        r_idx = milliseconds * len(self._zip) // 1000

        ### Only light up on bottom right quarter
        if w_quarter % 4 == 1:
            q_pix_cnt = len(self._zip) // 4
            for idx in range(w_quarter * q_pix_cnt, (w_quarter + 1) * q_pix_cnt):
                self._zip[idx] = (16, 10, 22)
        self._zip[r_idx] = (self._zip[r_idx][0] + 32, self._zip[r_idx][1], self._zip[r_idx][2])

        return self.HALO_CHANGED
