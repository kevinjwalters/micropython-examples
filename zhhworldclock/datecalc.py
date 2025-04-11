### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT


### Epoch in CPython time.struct_time(tm_year=1970, tm_mon=1, tm_mday=1, tm_hour=0, tm_min=0, tm_sec=0, tm_wday=3, tm_yday=1, tm_isdst=0)
### Here it will be (1970, 1, 1,  0, 0, 0,  3,  1)  3 is Thursday (0 Monday, 6 Sunday)
### This is different to unix/libc localtime()

from zc_utils import YEAR, MONTH, MDAY, HOUR, MINUTE, SECOND, WEEKDAY, YEARDAY

class DateCalc:
    """Times are same format as Python's time.localtime()"""

    D_IN_M = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


    @classmethod
    def add(cls, time1, secs):
        ### Do the in-place addition to each field then look
        ### for carries
        time1[SECOND] += secs
        min_diff = time1[SECOND] // 60
        if min_diff:
            time1[SECOND] -= min_diff * 60
            time1[MINUTE] += min_diff
            hour_diff = time1[MINUTE] // 60
            if hour_diff:
                time1[MINUTE] -= hour_diff * 60
                time1[HOUR] += hour_diff
            day_diff = time1[HOUR] // 24
            if day_diff:
                time1[HOUR] -= day_diff * 24
                day = time1[MDAY] + day_diff
                month = time1[MONTH]
                year = time1[YEAR]
                try:
                    yearday = time1[YEARDAY] + day_diff
                except IndexError:
                    yearday = 0
                future = day_diff > 0  ### direction to step across calendar
                while True:
                    if future:
                        mm_count = cls.days_in_month(month, year)
                        if day > mm_count:
                            day -= mm_count
                            month += 1
                            if month > 12:
                                yearday -= cls.days_in_year(year)
                                month -= 12
                                year += 1
                        else:
                            break
                    else:
                        if day < 1:
                            mm_count = cls.days_in_month(month - 1, year)
                            day += mm_count
                            month -= 1
                            if month < 1:
                                month += 12
                                year -= 1
                                yearday += cls.days_in_year(year)
                        else:
                            break

                time1[MDAY] = day
                time1[MONTH] = month
                time1[YEAR] = year
                try:
                    time1[WEEKDAY] = (time1[WEEKDAY] + day_diff) % 7
                    time1[YEARDAY] = yearday
                except IndexError:
                    pass

    @classmethod
    def days_in_month(cls, mon, yyyy):
        m_idx = mon - 1
        return cls.D_IN_M[m_idx] if m_idx != 1 else cls.D_IN_M[m_idx] + bool(cls.is_leap_year(yyyy))

    @classmethod
    def days_in_year(cls, yyyy):
        return 366 if cls.is_leap_year(yyyy) else 365

    @classmethod
    def is_leap_year(cls, year):
        #### From https://stackoverflow.com/questions/725098/leap-year-calculation
        return year % 4 == 0 and year % 100 != 0 or year % 400 == 0
