### SPDX-FileCopyrightText: 2025 Kevin J. Walters
###
### SPDX-License-Identifier: MIT

import ustruct
##import utime

##from zc_utils import HOUR, MINUTE, SECOND

_MP_ARRAY9 = 0x99
_MP_UINT8 = 0xcc
_MP_UINT16 = 0xcd
_MP_UINT32 = 0xce

_MSG_HDR_SRC     = 1
_MSG_HDR_DST     = 2
_MSG_HDR_MAGIC   = 3
_MSG_HDR_TYPE_ID = 4
_MSG_PAYLOAD     = 5

MAGIC = 0x4b
MSG_CLOCK_GROUP = 0x65
BCASTAADDR = 255

### Messages are
### uint32 header from, to, ?, msg_type_id
###

MSG_TIMEWMS_ID = 0x01


### The protocol is described by @mmoskal on https://makecode.com/blog/timing-adventures-in-infrared but
### the actual implementation in https://github.com/microsoft/pxt-common-packages/blob/master/libs/pulse/pulse.cpp
### differs slightly, the start of frame being obviously different, for example.


class ClockMsg:
    ID_MAP = {}   ### this is populated at the bottom of this file

    def __init__(self, msg_id, serial_len):
        self._serial = bytearray(5 + serial_len)
        self._serial[0] = _MP_UINT8
        self._serial[1] = msg_id


class MsgTimeWms(ClockMsg):
    ID = 0x01
    FMT = ">BB8BH"
    EPOCH_YEAR = 1970

    def __init__(self, rtc_time, ss_ms):
        self.rtc_time = rtc_time
        self.ss_ms = ss_ms
        super().__init__(self.ID, ustruct.calcsize(self.FMT))

    @classmethod
    def from_bytes(cls, buf):
        try:
            if buf[_MSG_HDR_TYPE_ID] == cls.ID:
                data = ustruct.unpack_from(cls.FMT,
                                           buf,
                                           _MSG_PAYLOAD)
                return MsgTimeWms((data[1] + cls.EPOCH_YEAR, data[2], data[3], data[4],
                                   data[5], data[6], data[7], data[8]),
                                  data[10])
        except (IndexError, ValueError):
            pass
        return None


    def __bytes__(self):
        ustruct.pack_into(self.FMT,
                          self._serial,
                          0,
                          _MP_ARRAY9,
                          self.rtc_time[0] - self.EPOCH_YEAR,
                          self.rtc_time[1],
                          self.rtc_time[2],
                          self.rtc_time[3],
                          self.rtc_time[4],
                          self.rtc_time[5],
                          self.rtc_time[6],
                          self.rtc_time[7],
                          _MP_UINT16,
                          self.ss_ms)
        return self._serial

ClockMsg.ID_MAP[MSG_TIMEWMS_ID] = MsgTimeWms


class ClockComms:
    def __init__(self, radio_=None, addr=0, *, power=6, channel=7, group=MSG_CLOCK_GROUP):
        self._radio = radio_
        self._addr = addr
        self._power = power
        self._channel = channel
        self._group = group

        self._radio.config(power=self._power, channel=self._channel, group=self._group)

        self.msg_id_list = [MsgTimeWms.ID]

        self._radio_en = False
        self.on()


    def broadcast_msg(self, msg):
        hdr = bytearray([_MP_UINT32, self._addr, BCASTAADDR, MAGIC, msg.ID])
        self._radio.send_bytes(hdr + msg.__bytes__())

    def receive_msg_full(self):
        ##rx_bytes = self._radio.receive_bytes()
        trio = self._radio.receive_full()
        if trio is None:
            return None

        rx_bytes, rssi, tstamp_tus = trio
        if rx_bytes and len(rx_bytes) >= 5 and rx_bytes[_MSG_HDR_MAGIC] == MAGIC:
            msg_cls = ClockMsg.ID_MAP.get(rx_bytes[_MSG_HDR_TYPE_ID])
            if msg_cls is not None:
                return (msg_cls.from_bytes(rx_bytes),
                        rssi, tstamp_tus,
                        rx_bytes[_MSG_HDR_SRC], rx_bytes[_MSG_HDR_DST])

        return None

    def on(self):
        if not self._radio_en:
            self._radio.on()
            self._radio_en = True

    def off(self):
        if self._radio_en:
            self._radio.off()
            self._radio_en = False
