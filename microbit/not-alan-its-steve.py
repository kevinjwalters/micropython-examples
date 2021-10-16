### not-alan-its-steve.py v1.2
### Play sequences of audio samples triggered by a PIR sensor

### Tested with BBC micro:bit v2 and MicroPython v1.15-64-g1e2f0d280
### and micro:bit v1 and MicroPython v1.9.2-34-gd64154c73

### MIT License

### Copyright (c) 2021 Kevin J. Walters

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


from microbit import *

import audio
import time

FRAME_SIZE = 32

def frames_from_file(sndfile, frame):
    while sndfile.readinto(frame, FRAME_SIZE) > 0:
        yield frame

def play_file(filename):
    frame = audio.AudioFrame()
    with open(filename, "rb") as sndfile:
        audio.play(frames_from_file(sndfile, frame), wait=True)
        audio.stop()

def play_sequence(audio_sequence):
    for item in audio_sequence:
        if isinstance(item, int):
            sleep(item)
        else:
            play_file(item)


### External speaker on P0 + V2 one together!
try:
    speaker.on()
except NameError:
    pass  ### speaker-less V1

### Mini PIR on pin8 - also works with Cytron edu:bit IR Bit
pin8.set_pull(pin8.NO_PULL)

alan = "alan.raw"
al = "al.raw"
itssteve = "itssteve.raw"
notalan = "notalan.raw"
steve = "steve.raw"

### micro:bit V2 has more storage than V1
### but this is not yet accessible
### https://forum.micropython.org/viewtopic.php?f=17&t=10948
audio_seq = ((alan, 200, al, 200, alan, 1000),
             (alan, 200, alan, 300, alan, 200, alan, 250, alan, 400,
              al, 200, alan, 200, alan, 400, alan, 1000),
             (alan, 250, alan, 250, alan, 1000),
             (notalan, 2000),
             (steve, 200, steve, 200, steve, 100, steve, 300,
              steve, 200, steve, 600, steve, 600, steve, 5000)
            )

### Pause at start-up just in case PIR sensor is "confused"
sleep(5000)

### Loop forever looking for a high signal from PIR sensor for
### three seconds and playing the next sequence in the audio
### sequences or reseting to the first one if nothing is detected
while True:
    audio_idx = 0
    while audio_idx < len(audio_seq):
        start_tick = time.ticks_ms()
        pir = False
        while time.ticks_diff(time.ticks_ms(), start_tick) < 3000:
            if pin8.read_digital():
                pir = True
                break

        if pir:
            play_sequence(audio_seq[audio_idx])
            audio_idx += 1
        else:
            break
