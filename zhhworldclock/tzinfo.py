### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


### $ for tzname in Canada/Pacific America/New_York America/Santiago \
### > Europe/London Europe/Paris Europe/Warsaw Europe/Bucharest Europe/Kyiv Europe/Minsk \
### > Asia/Kolkata Asia/Kuala_Lumpur Asia/Hong_Kong Australia/Perth Asia/Tokyo \
### > Australia/Queensland Australia/Sydney
### > do
### >   printf "%-17s %-40s\n" ${tzname} $(strings /usr/share/zoneinfo/${tzname} | tail -1)
### > done
### Canada/Pacific    PST8PDT,M3.2.0,M11.1.0
### America/New_York  EST5EDT,M3.2.0,M11.1.0
### America/Santiago  <-04>4<-03>,M9.1.6/24,M4.1.6/24
### Europe/London     GMT0BST,M3.5.0/1,M10.5.0
### Europe/Paris      CET-1CEST,M3.5.0,M10.5.0/3
### Europe/Warsaw     CET-1CEST,M3.5.0,M10.5.0/3
### Europe/Bucharest  EET-2EEST,M3.5.0/3,M10.5.0/4
### Europe/Kyiv       EET-2EEST,M3.5.0/3,M10.5.0/4
### Europe/Minsk      <+03>-3
### Asia/Kolkata      IST-5:30
### Asia/Kuala_Lumpur <+08>-8
### Asia/Hong_Kong    HKT-8
### Australia/Perth   AWST-8
### Asia/Tokyo        JST-9
### Australia/Queensland AEST-10
### Australia/Sydney  AEST-10AEDT,M10.1.0,M4.1.0/3

from datecalc import DateCalc
from zc_utils import YEAR, MONTH, MDAY, HOUR, MINUTE, SECOND, WEEKDAY


class SimpleTimeZone:
    ### UTC offset is positive west in these two class variables
    ### Location lookups
    TZ_LOOKUP = {
                 "Canada/Pacific":       "US/Pacific",
                 "America/New_York":     "US/Eastern",
                 "America/Santiago":     ["-04", 4, "-03", "M9.1.6/24,M4.1.6/24"],
                 "GMT":                  ["GMT", 0],
                 "Europe/London":        "GB",
                 "Europe/Paris":         "CET",
                 #"Europe/Warsaw":        "CET",
                 #"Europe/Bucharest":     "EET",
                 "Europe/Kyiv":          "EET",
                 "Europe/Minsk":         ["+03", -3],
                 "Asia/Kolkata":         ["IST", -5.5],
                 #"Asia/Kuala_Lumpur":    ["+08", -8],
                 #"Australia/Perth":      ["AWST", -8],
                 "Asia/Hong_Kong":       ["HKT", -8],
                 "Asia/Tokyo":           ["JST", -9],
                 #"Australia/Queensland": ["AEST", -10],
                 #"Australia/Sydney":     ["AEST", -10, "AEDT", "M10.1.0,M4.1.0/3"]
              }

    ### Commonly used values
    TZ_DATA = {
               "US/Pacific": ["PST", +8, "PDT",  "M3.2.0,M11.1.0"],
               "US/Eastern": ["EST",  +5, "EDT",  "M3.2.0,M11.1.0"],
               "GB":         ["GMT",  0, "BST",  "M3.5.0/1,M10.5.0"],
               "CET":        ["CET", -1, "CEST", "M3.5.0,M10.5.0/3"],
               "EET":        ["EET", -2, "EEST", "M3.5.0/3,M10.5.0/4"]
              }


    def __init__(self, tz, utc_time=None, *, optimization=True):
        self._tz = tz
        self._optimization = optimization

        try:
            tz_data = self.TZ_LOOKUP[self._tz]
            ### TODO could split on / and do multi-level map lookup??
            if isinstance(tz_data, str):
                tz_data = self.TZ_DATA[tz_data]
        except KeyError:
            raise ValueError("Unknown time zone: " + tz)

        self._tz_data = tz_data
        ### TZ values are positive to the west, this value is
        ### positive to the east
        self.utcoffset = 0 - round(self._tz_data[1] * 3600)
        self._dst_cached = None   ### recent value
        self._dst_day_cache = {}  ### yyyymm -> dst change day mapping
        self._dstobs = len(self._tz_data) > 2
        if self._dstobs:
            self._tz_name = None
            part1, part2 = self._tz_data[3].split(",", 1)
            self._dst_start_rule = self._parse_rule(part1)
            ## print("DST ASSIGNED")  ### TODO DELETE
            if len(self._tz_data) > 4:
                self._dst_offset_s = round(self._tz_data[4] * 3600)
            else:
                self._dst_offset_s = 3600
            self._dst_end_rule = self._parse_rule(part2)
            if utc_time is not None:
                offset_time = list(utc_time)
                DateCalc.add(offset_time, self.utcoffset)
                self._tz_name = tz_data[2] if self.dst(offset_time) else tz_data[0]
            else:
                self._tz_name = None
        else:
            self._tz_name = tz_data[0]

    @classmethod
    def _parse_rule(cls, rule):
        ### Turn M3.5.0/1 into (hh, mm, ss, "M", 10, 5, 0)
        hh = 2
        mm = ss = 0
        args = []
        rule_type = "?"

        if rule[0] == "M":
            rule_type = "M"
            args = rule[1:].split(".")
            try:
                end_rule, time = args[len(args) - 1].split("/", 1)
                hh = int(time)  ### TODO parse any :mm:ss
                args[len(args) - 1] = end_rule
            except ValueError:
                pass
        return tuple([hh, mm, ss, rule_type] + [int(x) for x in args])


    def _switch_day(self, offset_time):
        """Return the switch_day (1..31) for this month or None if there is none."""
        day = None
        if offset_time[MONTH] == self._dst_start_rule[4]:
            rule = self._dst_start_rule
        elif offset_time[MONTH] == self._dst_end_rule[4]:
            rule = self._dst_end_rule
        else:
            return day

        rule_week = rule[5]     ### 1-5, 5 is last of the month
        rule_daysun0 = rule[6]  ### 0 Sun to 6 Sat
        rule_weekday = (rule_daysun0 - 1 ) % 7  ### 0 Mon to 6 Sun

        cursor_time = list(offset_time)
        back = cursor_time[MDAY] - 1
        cursor_time[MDAY] -= back
        cursor_time[WEEKDAY] = (cursor_time[WEEKDAY] - back) % 7

        adv = (rule_weekday - cursor_time[WEEKDAY]) % 7
        cursor_time[MDAY] += adv
        cursor_time[WEEKDAY] = rule_weekday

        day = cursor_time[MDAY] + (rule_week - 1) * 7
        if day > 28:
            d_in_m = DateCalc.days_in_month(offset_time[MONTH], offset_time[YEAR])
            while day > d_in_m:
                day -= 7

        return day

    ### offset_time is UTC offset by time zone but not with DST applied
    def dst(self, offset_time):
        if not self._dstobs:
            return 0

        month_now = offset_time[MONTH]
        startm = month_now  == self._dst_start_rule[4]
        endm = month_now == self._dst_end_rule[4]
        if not startm and not endm:
            if self._optimization and self._dst_cached is not None:
                return self._dst_cached

            now_dst = self._dst_start_rule[4] < month_now < self._dst_end_rule[4]
            if self._dst_start_rule[4] > self._dst_end_rule[4]:
                ### Invert for Southern hemisphere
                now_dst = not now_dst
            dst_offset = self._dst_offset_s if now_dst else 0
            if self._optimization:
                self._dst_cached = dst_offset
            return dst_offset

        yyyymm = "{:4d}{:02d}".format(offset_time[YEAR], month_now)
        switch_day = self._dst_day_cache.get(yyyymm)
        if switch_day is None:
            switch_day = self._switch_day(offset_time)
            self._dst_day_cache[yyyymm] = switch_day

        day_now = offset_time[MDAY]
        if day_now < switch_day:
            is_dst = endm
        elif day_now > switch_day:
            is_dst = startm
        else:
            if startm:
                is_dst = offset_time[HOUR] >= self._dst_start_rule[0]
            elif endm:
                is_dst = self._dst_end_rule[0] < offset_time[HOUR]
            else:
                raise RuntimeError("Internal error")

        self._tz_name = self._tz_data[2] if is_dst else self._tz_data[0]
        return is_dst

    def utc_to_local(self, utc_time):
        offset_time = list(utc_time)
        ### This needs to be done as two date additions
        DateCalc.add(offset_time, self.utcoffset)
        if self._dstobs and self.dst(offset_time):
            DateCalc.add(offset_time, self._dst_offset_s)
        return offset_time

    ### For one hour a year this will be ambiguous without the ninth field
    def local_to_utc(self, local_time):
        offset_time = list(local_time)
        ### This needs to be done as two date additions
        DateCalc.add(offset_time, 0 - self.utcoffset)
        if self._dstobs and self.dst(offset_time):
            DateCalc.add(offset_time, 0 - self._dst_offset_s)
        return offset_time
