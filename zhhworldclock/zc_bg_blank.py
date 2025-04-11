### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


from zc_bg import HaloBackground


class Blank(HaloBackground):
    def render(self, local_time, milliseconds, ticks_ms):
        return 0
