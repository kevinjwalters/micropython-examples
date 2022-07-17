### carbon-intensity.py v1.0
### Download UK Carbon Intensity data over Wi-Fi and show on an SSD1306 screen

### Tested with Pi Pico W and MicroPython v1.19.1

### copy this file to Pi Pico W as main.py

### MIT License

### Copyright (c) 2022 Kevin J. Walters

### Permission is hereby granted, free of charge, to any person obtaining a copy
### of this software and associated documentation files (the "Software"), to deal
### in the Software without restriction, including without limitation the rights
### to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
### copies of the Software, and to permit persons to whom the Software is
### furnished to do so, subject to the following conditions:

### The above copyright notice and this permission notice shall be included in all
### copies or substantial portions of the Software.

### THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
### IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
### FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
### AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
### LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
### OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
### SOFTWARE.


import time

import urequests as requests
import network
import rp2
import neopixel

from machine import Pin, I2C
from ssd1306 import SSD1306_I2C

### pylint: disable=wrong-import-order
from secrets import secrets


### SSD1306 resolution
WIDTH = 128
HEIGHT = 64
FONT_WIDTH = 8
FONT_HEIGHT = 8

FUEL_MIX_NATIONAL_URL = "https://api.carbonintensity.org.uk/generation"
FUEL_MIX_LOCAL_URL = "https://api.carbonintensity.org.uk/generation"

REQUEST_ATTEMPTS = 5
RETRY_PAUSE_S = 20
PAUSE_PRE_RECONNECT_S = 2
FETCH_PERIOD_MS = 30 * 60 * 1000
SLEEP_MAIN_LOOP_S = 0.25  ### How often button is checked

### Maker Pi Pico (Base) has pull-up resistors on these three pins
input_20 = Pin(20, Pin.IN, pull=None)
button_left = lambda: not input_20.value()
input_21 = Pin(21, Pin.IN, pull=None)
button_middle = lambda: not input_21.value()
input_22 = Pin(22, Pin.IN, pull=None)
button_right = lambda: not input_22.value()

debug = 2

def d_print(level, *args, **kwargs):
    """A simple conditional print for debugging based on global debug level."""
    if not isinstance(level, int):
        print(level, *args, **kwargs)
    elif debug >= level:
        print(*args, **kwargs)


class PixelStatus:
    NOT_CONNECTED = (20, 0, 20)  ### Magenta
    CONNECTED_OK = (0, 20, 0)    ### Green
    DISCONNECTED = (20, 20, 0)   ### Amber
    REQUEST_ERROR = (20, 0, 0)   ### Red
    FETCHING = (0, 0, 20)        ### Blue

    def __init__(self, pin=None, num=1):
        if pin is None:
            dpin = Pin(28)
        else:
            dpin = pin
        self._neopixels = neopixel.NeoPixel(dpin, num)
        self._num = num
        self._status = None


    def fill(self, colour):
        for idx in range(self._num):
            self._neopixels[idx] = colour
        self._neopixels.write()


    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value
        self.fill(self._status)


pixel = PixelStatus()
pixel.status = PixelStatus.NOT_CONNECTED

### SDA on GP0, SCL on GP1, conservative 100kHz clock
HW_0 = 0
sda = Pin(0)
scl = Pin(1)
i2c = I2C(HW_0, sda=sda, scl=scl, freq=100 * 1000)


def vcompact_str(num):
    """Return a very compact string representation of a number for tiny displays,
       single digit after decimal point
       and no leading 0 on numbers with magnitude less than 1."""
    if -1 < num < 0:
        return "-" + "{:.1f}".format(-num).lstrip("0")
    elif num == 0:
        return "0"
    elif num < 1:
        return "{:.1f}".format(num).lstrip("0")

    return str(round(num))


class GenerationDashboard:
    ### These are UK numbers from
    ### https://github.com/carbon-intensity/methodology/raw/master/Carbon%20Intensity%20Forecast%20Methodology.pdf
    CI_REF = {
               "biomass": 120,
               "coal":  937,
               "import ifa": 53,
               "import ifa2": 53,
               "import britned": 474,
               "import nemo": 179,
               "import moyle": 458,
               "import east-west": 458,
               "import nsl": 123,  ### placeholder value
               "imports": (53 + 474 + 179 + 458) / 4,
               "gas": (394 + 651) / 2,
               "nuclear": 0,
               "other": 300,
               "hydro": 0,
               "solar": 0,
               "wind": 0,
        }

    def __init__(self, i2c_,
                 width=WIDTH, height=HEIGHT,
                 font_width=FONT_HEIGHT, font_height=FONT_HEIGHT,
                 title="Electricity Fuel"):
        self._i2c = i2c_
        self._width = width
        self._height = height
        self._font_width = font_width
        self._font_height = font_height

        self._oled = SSD1306_I2C(width, height, i2c)
        self._oled.fill(0)
        if title:
            self._oled.text(title,
                            (self._width - len(title) * font_width) // 2,
                            0)
        self._oled.show()

        self._bar_y = 8
        self._bar_height = 8
        self._bar_width = self._width
        self._text_y = 16
        self._text_cols = (4, 4 + self._width // 2)
        self._colour = 1


    def low_carbon(self, fuel, threshold=150):
        carbon_intensity = self.CI_REF.get(fuel)
        return not(carbon_intensity is None or carbon_intensity >= threshold)

    def update(self, data, end_time=None):
        """data is a list of dict with fuel and perc entries."""

        self._oled.fill(0)

        if end_time is not None:
            self._oled.text(end_time, 0, 0, self._colour)

        ### Two columns with low carbon on left
        left_x, right_x = self._text_cols
        left_y = self._text_y
        right_y = self._text_y
        large_fission = 0
        green = 0
        for row in data:
            fuel = row.get("fuel")
            perc = row.get("perc")
            if fuel is not None and perc is not None:
                ### Using a very compact 7 char representation
                ### sola 42
                ### nucl .4
                text = "{:4s}{:>3s}".format(fuel[:4], vcompact_str(perc))
                low_c = self.low_carbon(fuel)
                if fuel.lower().find("nuclear") >= 0:
                    large_fission += perc
                elif low_c:
                    green += perc

                if low_c:
                    self._oled.text(text, left_x, left_y, self._colour)
                    left_y += 8
                else:
                    self._oled.text(text, right_x, right_y, self._colour)
                    right_y += 8

        self._draw_bar(green, fission=large_fission)

        ### Column separator
        self._oled.fill_rect(right_x - left_x - 1, self._text_y,
                             2, self._height - self._text_y,
                             self._colour)
        self._oled.show()

    def _draw_bar(self, green, fission=0, fusion=0):
        brown = 100 - green - fusion - fission

        ### Outline - black represents green
        self._oled.rect(0, self._bar_y,
                        self._bar_width, self._bar_height,
                        self._colour)

        ### Fill in the brown
        brown_width = (self._bar_width - 1) * brown / 100.0
        if brown_width > 1:
            self._oled.fill_rect(self._width - round(brown_width),
                                 self._bar_y + 1,
                                 round(brown_width),
                                 self._bar_height - 2,
                                 self._colour)

        ### Add thinner bars for nuclear
        fission_width = (self._bar_width - 1) * fission / 100.0
        if fission_width > 0.5:
            self._oled.fill_rect(self._width - round(brown_width
                                                     + fission_width),
                                 self._bar_y + 2,
                                 round(fission_width),
                                 self._bar_height - 4,
                                 self._colour)

        fusion_width = (self._bar_width - 1) * fusion / 100.0
        if fusion_width > 0.5:
            self._oled.fill_rect(self._width - round(brown_width
                                                     + fission_width
                                                     + fusion_width),
                                 self._bar_y + 3,
                                 round(fusion_width),
                                 self._bar_height - 6,
                                 self._colour)


dashboard = GenerationDashboard(i2c)

country = secrets.get("country")
if country is not None:
    rp2.country(country)

CYW43_LINK_UP = 3
CYW43_LINK_BADAUTH = -3

def wifi_connect(wifi,
                 wifi_secrets=None,
                 verbose=True, reconnect=False,
                 wait=15, pause=1):
    wifi_status = None

    if reconnect:
        if verbose:
            print("Wi-Fi reconnecting")
        wlan.disconnect()
    else:
        if verbose:
            print("Wi-Fi connecting")

    if wifi_secrets is None:
        data = secrets
    else:
        data = wifi_secrets
    ssid = data["ssid"]
    password = data["password"]

    wifi.connect(ssid, password)
    attempt = 1
    while attempt <= wait:
        wifi_status = wifi.status()
        if wifi_status < 0 or wifi_status >= CYW43_LINK_UP:
            break
        attempt += 1
        if verbose:
            print("Wi-Fi waiting for connection")
        time.sleep(pause)

    if verbose:
        print("Wi-Fi connected")
    if debug:
        print(wifi.ifconfig())

    return wifi_status


wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan_status = wifi_connect(wlan)
if wlan_status == CYW43_LINK_UP:
    pixel.status = PixelStatus.CONNECTED_OK

### Poll the data service every 30 minutes displaying the data on the
### SSD1306 with some retries if there are request errors including
### checking health of Wi-Fi connection and re-establishing this as
### needed
last_fetch_attempt_ms = None
while True:
    if (button_left()
        or last_fetch_attempt_ms is None
        or time.ticks_diff(time.ticks_ms(),
                           last_fetch_attempt_ms) > FETCH_PERIOD_MS):
        for _ in range(REQUEST_ATTEMPTS):
            resp_data = None
            url = FUEL_MIX_NATIONAL_URL
            last_fetch_attempt_ms = time.ticks_ms()
            d_print(2, "Fetching", url)
            try:
                pixel.status = PixelStatus.FETCHING
                resp = requests.get(url)
                resp_data = resp.json()
                d_print(4, "Response JSON", resp_data)
            except Exception as ex:
                print("Requested failed: " + str(ex))
                pixel.status = PixelStatus.REQUEST_ERROR
                time.sleep(PAUSE_PRE_RECONNECT_S)
                if wlan.status() != CYW43_LINK_UP:
                    pixel.status = PixelStatus.DISCONNECTED
                    wlan_status = wifi_connect(wlan, reconnect=True)

            if resp_data:
                break
            time.sleep(RETRY_PAUSE_S)

        if resp_data:
            try:
                gmix = resp_data["data"]["generationmix"]
                date_to = resp_data["data"]["to"]
                dashboard.update(gmix, end_time=date_to)
                pixel.status = PixelStatus.CONNECTED_OK
            except Exception as ex:
                print("Dashboard exception: " + str(ex))

    time.sleep(SLEEP_MAIN_LOOP_S)
