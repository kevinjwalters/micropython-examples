### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


import utime

from zc_utils import HOUR, MINUTE, SECOND


class ComboClock:
    def __init__(self, rtc, *,
                 rtc_clock_drift_ppm=0,
                 rtc_trim_conv=1,
                 mp_clock_drift_ppm=0,
                 current_time=None):
        self._rtc = rtc

        if rtc_clock_drift_ppm is not None:
            rtc_trim_value = round((0.0 - rtc_clock_drift_ppm) * rtc_trim_conv)
            print("TRIM", rtc_trim_value)
            self._rtc.set_trim(rtc_trim_value)

        if current_time:
            self._rtc.time = current_time

        self._rtc.start()
        if not self.sync_clocks():
            raise RuntimeError("Cannot synchronise RTC with MP MB clock")

        self._mp_clock_drift_ppm = mp_clock_drift_ppm
        self._conv_ticks_ms = 1.0 - mp_clock_drift_ppm / 1e6 if mp_clock_drift_ppm else 1
        self._last_frac_ms = None
        self._lost_sync = 0

        self.stopwatch_running = False
        self._stopwatch_start = self._stopwatch_stop = self._stopwatch_last = utime.ticks_ms()


    def sync_clocks(self, attempts=10_000, current_time=None):
        time_now = time_new = self._rtc.time if current_time is None else current_time
        time_tms = utime.ticks_ms()
        for _ in range(attempts):
            time_new = self._rtc.time
            time_tms = utime.ticks_ms()
            ### Wait for seconds to change
            if time_new[SECOND] != time_now[SECOND]:
                break

        if time_new[5] != time_now[5]:
            self._sync_time = time_new
            self._sync_time_tms = time_tms
            self._lost_sync = 0
            return True
        else:
            return False


    @property
    def time_with_ms_and_ticks(self):
        if self._lost_sync != 0:
            #print("RESYNC ATTEMPT")
            if self.sync_clocks(20, self._rtc.time):
                pass
                #print("RESYNCED!")

        rtc_time = self._rtc.time
        now_t_ms = utime.ticks_ms()
        since_ms = utime.ticks_diff(now_t_ms, self._sync_time_tms)
        cor_since_ms = round(since_ms * self._conv_ticks_ms)

        oneday_s = ((rtc_time[HOUR] - self._sync_time[HOUR]) * 3600
                    + (rtc_time[MINUTE] - self._sync_time[MINUTE]) * 60
                    + rtc_time[SECOND] - self._sync_time[SECOND])

        if oneday_s < 0:
            oneday_s += 86400

        self._last_frac_ms = cor_since_ms % 1000
        tick_coroneday_s = int(cor_since_ms / 1000.0)
        ### Re-synchronise if RTC time does not match MicroPython tick time
        ### or at least every half day
        if oneday_s != tick_coroneday_s or oneday_s > 43200:
            self._lost_sync = tick_coroneday_s - oneday_s
            #print("NEED RESYNC")
            if self._lost_sync > 0:
                ### MP is ahead, try a sync now as RTC is likely to catch up
                if self.sync_clocks(40, rtc_time):
                    #print("RESYNCED!")
                    rtc_time = self._rtc.time
                    now_t_ms = utime.ticks_ms()
                    since_ms = utime.ticks_diff(now_t_ms, self._sync_time_tms)
                    cor_since_ms = round(since_ms * self._conv_ticks_ms)
                    self._last_frac_ms = cor_since_ms % 1000
                else:
                    self._last_frac_ms = 999
            else:
                self._last_frac_ms = 0

        #print(oneday_s, rtc_time[5], since_ms/1000.0, cor_since_ms/1000.0, self._last_frac_ms)
        return (rtc_time, self._last_frac_ms, now_t_ms)

    def set_rtc(self, current_time):
        self._rtc.time = current_time

    def stopwatch_reset(self):
        self._stopwatch_start = self._stopwatch_stop = utime.ticks_ms()

    def stopwatch_start(self):
        self._stopwatch_start = utime.ticks_add(utime.ticks_ms(),
                                                utime.ticks_diff(self._stopwatch_start,
                                                                 self._stopwatch_stop))
        self.stopwatch_running = True

    def stopwatch_stop(self):
        self._stopwatch_stop = utime.ticks_ms()
        self.stopwatch_running = False

    def stopwatch_time_ms(self):
        if self.stopwatch_running:
            raw_dur_ms = utime.ticks_diff(utime.ticks_ms(), self._stopwatch_start)
        else:
            raw_dur_ms = utime.ticks_diff(self._stopwatch_stop, self._stopwatch_start)
        return raw_dur_ms * self._conv_ticks_ms
