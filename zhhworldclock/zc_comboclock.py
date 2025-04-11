### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


import utime

from datecalc import DateCalc
from tzinfo import SimpleTimeZone
from zc_utils import HOUR, MINUTE, SECOND


### Count for the for loop for MP clock vs RTC sync
_LOTS = 10_000


class ComboClock:
    def __init__(self, rtc, *,
                 rtc_clock_drift_ppm=0,
                 rtc_trim_conv=1,
                 mp_clock_drift_ppm=0,
                 tz="GMT",
                 current_time=None):
        self._rtc = rtc

        if rtc_clock_drift_ppm is not None:
            self._rtc_trim_value = round((0.0 - rtc_clock_drift_ppm) * rtc_trim_conv)
            print("TRIM", self._rtc_trim_value)
            self._rtc.set_trim(self._rtc_trim_value)

        ### Set the time on the RTC if one is passed in
        if current_time:
            self._rtc.time = current_time

        self._rtc.start()
        self._mp_clock_drift_ppm = mp_clock_drift_ppm

        self._tz = tz
        self._tzinfo = SimpleTimeZone(self._tz,
                                      current_time if current_time else self._rtc.time)

        self._ts_to_s = 1.0 - mp_clock_drift_ppm / 1e6 if mp_clock_drift_ppm else 1
        self._last_frac_ms = None
        self._lost_sync = 0
        self.resync_enabled = True
        if not self.sync_clocks():
            raise RuntimeError("Cannot synchronise RTC with MP MB clock")

        self.stopwatch_running = False
        self._stopwatch_start = self._stopwatch_stop = self._stopwatch_last = utime.ticks_ms()


    def sync_clocks(self, attempts=_LOTS, current_time=None):
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
    def localtime_with_ms_and_ticks(self):
        rtc_utc_time, ss_ms, now_tms = self.utctime_with_ms_and_ticks
        return (self._tzinfo.utc_to_local(rtc_utc_time),  ss_ms, now_tms)

    @property
    def localandutctime_with_ms_and_ticks(self):
        rtc_utc_time, ss_ms, now_tms = self.utctime_with_ms_and_ticks
        return (self._tzinfo.utc_to_local(rtc_utc_time), rtc_utc_time, ss_ms, now_tms)

    @property
    def utctime_with_ms_and_ticks(self):
        if self.resync_enabled and self._lost_sync != 0:
            if self.sync_clocks(20, self._rtc.time):
                pass

        rtc_time = self._rtc.time
        now_t_ms = utime.ticks_ms()
        if not self.resync_enabled:
            self._last_frac_ms = 0
            return (rtc_time, self._last_frac_ms, now_t_ms)

        since_tms = utime.ticks_diff(now_t_ms, self._sync_time_tms)
        cor_since_ms = round(since_tms * self._ts_to_s)

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
                    since_tms = utime.ticks_diff(now_t_ms, self._sync_time_tms)
                    cor_since_ms = round(since_tms * self._ts_to_s)
                    self._last_frac_ms = cor_since_ms % 1000
                else:
                    self._last_frac_ms = 999
            else:
                self._last_frac_ms = 0

        #print(oneday_s, rtc_time[5], since_ms/1000.0, cor_since_ms/1000.0, self._last_frac_ms)
        return (rtc_time, self._last_frac_ms, now_t_ms)

    def set_rtc_utc(self, current_utctime):
        self._rtc.time = current_utctime

    def set_rtc_local(self, current_localtime):
        self._rtc.time = self._tzinfo.local_to_utc(current_localtime)


    def set_utctime(self, current_utc_time, milliseconds, delay_ms):
        """Returns True if time is known to be well synchronised."""

        time_incr = list(current_utc_time)
        DateCalc.add(time_incr, 2)

        wait_time = 2_000 - (milliseconds + delay_ms)
        if wait_time > 2:
            utime.sleep_ms(round(wait_time / self._ts_to_s))
        self._rtc.time = time_incr
        zero_tms = utime.ticks_ms()
        if self.sync_clocks(current_time=time_incr):
            diff_tms = utime.ticks_diff(self._sync_time_tms, zero_tms)
            ### Fudge alert! -90 makes this work for some reason
            error_ms = 1000 - 90 - diff_tms * self._ts_to_s
            if error_ms > 5:
                ### -80 coarse trim is lose a second every 3.2s, -127 every 2.016s
                self._rtc.set_trim(-127, corse=True)  ### kw has typo
                utime.sleep_us(round((error_ms * 2016 - 500) / self._ts_to_s))
                self._rtc.set_trim(self._rtc_trim_value)
                return True

            ### Return True if previous sync left us with an error below 50ms
            return abs(error_ms) < 50

        return False   ### This should not be reached!


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
            raw_dur_tms = utime.ticks_diff(utime.ticks_ms(), self._stopwatch_start)
        else:
            raw_dur_tms = utime.ticks_diff(self._stopwatch_stop, self._stopwatch_start)
        return raw_dur_tms * self._ts_to_s

    def s_to_ts(self, value):
        return round(value / self._ts_to_s)
