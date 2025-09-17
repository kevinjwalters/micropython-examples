### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT

import array
from math import pi, sin, cos, sqrt

### Z_LED_POS AND M_LED_POS are inelegant arrays to reduce memory use
### and perhaps cause less memory fragmentation

### TODO considering punting these fields out to a zc_constants or similar

### localtime fields
YEAR = 0
MONTH = 1
MDAY = 2
HOUR = 3
MINUTE = 4
SECOND = 5
WEEKDAY = 6
YEARDAY = 7


ZIPCOUNT = 60
ZIP_DIAMETER = 80        ### in mm
ZIP_RADIUS = ZIP_DIAMETER / 2
DIM_SCALE = ZIP_DIAMETER / 2

### TODO - try an array.array to see how much memory it saves for Z_LED_POS AND M_LED_POS
### indexing will need to be [2 * idx]

### LED positions with values ranging from -1.0 to 1.0
### top left of bounding square is -1,-1 bottom right is 1,1

Z_LED_POS = array.array("f", [0.0] * (ZIPCOUNT * 2))
M_LED_POS = array.array("f", [0.0] * (5 * 5 * 2))

for z_idx in range(ZIPCOUNT):
    Z_LED_POS[z_idx * 2] = sin(z_idx / ZIPCOUNT * 2 * pi)
    Z_LED_POS[z_idx * 2 + 1] = 0.0 - cos(z_idx / ZIPCOUNT * 2 * pi)

#Z_LED_POS = tuple(tuple([(sin(idx / ZIPCOUNT * 2 * pi),
#                          0.0 - cos(idx / ZIPCOUNT * 2 * pi))
#                         for idx in range(ZIPCOUNT)]))

### This is in the display dimensions (-1 to 1)
Z_LED_SPACING = pi * ZIP_DIAMETER / ZIPCOUNT / DIM_SCALE
M_LED_SPACING = 4.0 / DIM_SCALE

### Look up table for pixels (in height order, bottom first)
### near a set of discrete x positions to make digital_rain
### more efficient
half_width = 15
z_leds_near_x = [[] for _ in range(half_width * 2 + 1)]   ### [[]] * N is a trap!
z_near_distance = Z_LED_SPACING / 1.8
height_order_idxs = [x for pair in zip(range(ZIPCOUNT // 2, ZIPCOUNT),
                                       range(ZIPCOUNT // 2 - 1, -1, -1)) for x in pair]
for x_idx in range(len(z_leds_near_x)):
    pos_x = (x_idx - half_width) / half_width
    for zp_idx in height_order_idxs:
        led_x = Z_LED_POS[zp_idx * 2]
        if abs(led_x - pos_x) < z_near_distance:
            z_leds_near_x[x_idx].append(zp_idx)

def get_z_pixels_through_x(l_x):
    p_idx = half_width + round(l_x * half_width)
    if p_idx < 0 or p_idx >= len(z_leds_near_x):
        return []
    return z_leds_near_x[p_idx]

def get_z_pixel_dist(idx, x, y):
    dx = x - Z_LED_POS[idx * 2]
    dy = y - Z_LED_POS[idx * 2 + 1]
    return sqrt(dx*dx + dy*dy)


M_LEFT = 0 - M_LED_SPACING * 2
M_RIGHT = 0 - M_LEFT
### This would be 2.0 if micro:bit display was central but it's
### a bit higher and fouth row [3] is almost aligned with middle
M_TOP = 0 - M_LED_SPACING * 2.9
m_idx = 0
for y_idx in range(5):
    for x_idx in range(5):
        #M_LED_POS.append((M_LEFT + x_idx * M_LED_SPACING, M_TOP + y_idx * M_LED_SPACING))
        M_LED_POS[m_idx] = M_LEFT + x_idx * M_LED_SPACING
        M_LED_POS[m_idx + 1] = M_TOP + y_idx * M_LED_SPACING
        m_idx += 2

m_near_distance = M_LED_SPACING / 1.8

def get_m_pixels_through_x(l_x):
    near_idxs = []
    ### Scan the top row for nearby pixels
    for p_idx in range(5):
        if abs(M_LED_POS[p_idx * 2] - l_x) < m_near_distance:
            near_idxs.append(p_idx)
    row_near_count = len(near_idxs)
    if row_near_count == 0:
        return near_idxs

    ### duplicate first row to cover all the rows
    near_idxs = near_idxs * 5
    for mi_idx in range(row_near_count, len(near_idxs)):
        near_idxs[mi_idx] += mi_idx // row_near_count * 5
    return near_idxs


def vertical_line_near_pixel(near_dist, x1, y1b, y1t, x2, y2):
    ### pylint: disable=chained-comparison
    """If line runs within near_dist from (x2, y2) then
       (distance, y_relint, beyond) is returned otherwise None"""
    x_distance = abs(x2 - x1)
    if y1t <= y2 <= y1b:  ### point is next to line
        return (x_distance, (y2 - y1t) / (y1b - y1t), False)

    distance = float("Inf")
    if y2 > y1b and y2 < y1b + near_dist:
        distance = sqrt(x_distance * x_distance + (y2 - y1b) * (y2 - y1b))
        return (distance, 1, True)
    elif y2 < y1t and y2 > y1t - near_dist:
        distance = sqrt(x_distance * x_distance + (y2 - y1t) * (y2 - y1t))
        return (distance, 0, True)

    return None


def get_pixels_near_angle(angle, radius):
    c_x = sin(angle) * ZIP_RADIUS / DIM_SCALE
    c_y = 0.0 - cos(angle) * ZIP_RADIUS / DIM_SCALE

    nearest_z_idx = round(angle / (2 * pi) * ZIPCOUNT) % ZIPCOUNT

    bri = (radius - get_z_pixel_dist(nearest_z_idx, c_x, c_y)) / radius
    if bri <= 0.0:
        return []

    z_pixels = [(nearest_z_idx, bri)]
    for _ in range(0, ZIPCOUNT // 2):
        ccw_idx = (nearest_z_idx - 1) % ZIPCOUNT
        cw_idx = (nearest_z_idx + 1) % ZIPCOUNT
        prev_pixel_count = len(z_pixels)

        bri = (radius - get_z_pixel_dist(ccw_idx, c_x, c_y)) / radius
        if bri > 0.0:
            z_pixels.append((ccw_idx, bri))

        bri = (radius - get_z_pixel_dist(cw_idx, c_x, c_y)) / radius
        if bri > 0.0:
            z_pixels.append((cw_idx, bri))
        if len(z_pixels) == prev_pixel_count:
            break

    return z_pixels
