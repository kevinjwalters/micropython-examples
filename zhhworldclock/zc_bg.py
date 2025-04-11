### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


class HaloBackground:
    MICROBIT_CHANGED = 0x01
    HALO_CHANGED = 0x02


    def __init__(self, zip_, mdisplaylist, options=None):
        self._zip = zip_
        self._mdisplaylist = mdisplaylist
        self._last_render_tms = None
        self._options = options if options is not None else {}

        self.displayed = 0  ### bit mask of localtime fields shown by background

        ##self._start_time_lt = None
        ##self._start_time_ms = None
        ##self._start_time_tms = None

        if type(self) == HaloBackground:  ### pylint: disable=unidiomatic-typecheck
            raise ValueError("Needs to be sub-classed")


    def render(self, local_time, milliseconds, ticks_ms):
        ### This should return MICROBIT_CHANGED | HALO_CHANGED
        raise NotImplementedError

    def start(self, local_time, milliseconds, ticks_ms):
        ### pylint: disable=attribute-defined-outside-init
        self._start_time_lt = local_time
        self._start_time_ms = milliseconds
        self._start_time_tms = ticks_ms

    def stop(self):
        self._last_render_tms = None

    def run_time(self, local_time, milliseconds):
        ### TODO complete this for years
        return ((local_time[7] - self._start_time_lt[7]) * 86400
                 + (local_time[3] - self._start_time_lt[3]) * 3600
                 + (local_time[4] - self._start_time_lt[4]) * 60
                 + local_time[5] - self._start_time_lt[5] + milliseconds / 1000.0)
