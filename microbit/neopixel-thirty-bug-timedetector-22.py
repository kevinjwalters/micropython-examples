### Martin Williams modified version of R21 with pin outputs removed

### This still produces very occasional corrupted neopixel output


import gc

from microbit import display, pin8
import neopixel
from utime import ticks_ms, ticks_us, ticks_diff
from utime import sleep as sleep_s

##import radio
##radio.off()


PROGRAM="R22"


gc.collect()

INSPECTION_PAUSE_S = 3600


### ZIP Halo HD has 60 RGB LEDs
ZIPCOUNT = 60
MIN_COUNT = 60
MAX_COUNT = 67
#counts = (60, 61, 62, 63, 64, 65, 66, 67)
counts = (32 // 3, 48 // 3, 64 // 3, 80 // 3, 96 // 3,
          60, 64, 95)
##reps = 5 * 60 * 200
period_ms = 5 * 60 * 1000
### Try longer run to see if this picks up more problems although not all will be visual
##ZIPCOUNT = 92
##ZIPCOUNT = 95
##ZIPCOUNT = 191
##ZIPCOUNT = 239
BLACK = (0, 0, 0)

NEOPIXEL_PIN = pin8

##display.clear()
display.off()

init_px = neopixel.NeoPixel(NEOPIXEL_PIN, ZIPCOUNT)
init_px.fill(BLACK)
init_px.show()

### This takes about 442-445ms at 13_700
def some_maths(reps=13_700):
    number = 1.2345
    for _ in range(reps):
        number = number * 1.001 - 1.001

t1_us = ticks_us()
some_maths()
t2_us = ticks_us()
print(PROGRAM, "MATH", ticks_diff(t2_us, t1_us))


def calc_show_min_us(pix):
    ### Estimate of minimum time for a good show() call (2175us for 60)
    #SHOW_MIN_US = round((ZIPCOUNT * 3 * 8 + 2 * 50) * 1.25 + ZIPCOUNT * 2 + 95)
    ### This should be 1.25ms but 1.20 works better for some reason

    ### More hacks, for 10 183us is common and 313us is common,
    ### MicroPython timing iffy for these small amounts?
    if len(pix) <= 10:
        return 150

    return round((len(pix) * 3 * 8 + 2 * 50) * 1.20  + 190)

def set_ascending(pix):
    ### GRB is a common order in the wire protocol
    for idx in range(len(pix)):
        triple_idx = 3 * idx
        pix[idx] = ((triple_idx + 1) % 256, triple_idx % 256, (triple_idx + 2) % 256)


count = 0
start_us = ticks_us()
dur_us = 0

baseline_us = [0] * 16

while True:
    for zipcount in counts:
        #print(PROGRAM, "ZIPCOUNT", zipcount)
        zip_px = neopixel.NeoPixel(NEOPIXEL_PIN, zipcount)
        set_ascending(zip_px)
        show_min_us = calc_show_min_us(zip_px)

        for b_idx in range(len(baseline_us)):
            gc.collect()
            start_us = ticks_us()
            zip_px.show()
            ##t2_us = ticks_us(
            baseline_us[b_idx] = ticks_diff(ticks_us(), start_us)

        ### TODO - these values are typically really quick
        ### BUT R14 does a gc collect and times them and gets times
        ### that appear to reflect

        baseline_us.sort()
        ### 90% of (min(IQR) - 20us)
        show_min_us = round((min(baseline_us[4:12]) - 20) * 0.9)
        #print(PROGRAM, "SHMN", show_min_us, baseline_us)

        gc.collect()
        slowcount = 0
        totalcount = 0
        #for rep in range(reps):
        start_ms = ticks_ms()
        while ticks_diff(ticks_ms(), start_ms) < period_ms:
            t1_us = ticks_us()
            zip_px.show()
            t2_us = ticks_us()
            dur_us = ticks_diff(t2_us, t1_us)
            if dur_us < show_min_us:
                if slowcount % 100_000 == 0:
                    pass
                    #print(PROGRAM, "SLOW", dur_us, "vs", show_min_us, "at", rep)
                slowcount += 1
            elif dur_us < 200:
                ### Somehow managed to get micro:bit into a very fast broken mode
                ### where hitting reset button was required to fix MicroPython!
                print(PROGRAM, "BGRD", dur_us)
                t1_us = ticks_us()
                some_maths()
                t2_us = ticks_us()
                print(PROGRAM, "MATH", ticks_diff(t2_us, t1_us))
                sleep_s(3600)
            totalcount += 1

        gc.collect()
        zip_px.fill(BLACK)
        zip_px.show()  ### This could error
        print(PROGRAM, "SUMM", zipcount, slowcount, totalcount)

    count += 1
