#
# BSD 3-Clause License
#
# Copyright (c) 2021, Fred Cirera
# All rights reserved.
#
#
import ctypes
import struct

SQ_MAGIC = 0xBADDECAF
SQ_VERSION = 1

SQ_STRUCT = struct.Struct('!IHHHH??10s')

SQ_HEARTBEAT = 0x01
SQ_PAUSE = 0x02
SQ_DATA = 0x08

XMIT_MAXRETRY = 5

class SQStatus:
  __xmit__ = 0
  """
  SQ Status heart beat (type = 0x0001 heartbeat)
  1  magic number   uint   (4)
  2  version        ushort (2)
  3  packet type    ushort (2)

  SQ Status data format (type = 0x0002 data)
  1  magic number   uint   (4)
  2  version        ushort (2)
  3  packet type    ushort (2)
  4  max retry      ushort (2)
  5  xmit           ushort (2)
  6  pause          bool   (1)
  7  shutdown       bool   (1)
  8  call           utf-8  (10)
  """
  def __init__(self):
    self.max_tries = XMIT_MAXRETRY

    # Private variables
    self._call = b''
    self._pause = False
    self._shutdown = False

    # Local variables
    self._ip_wsjt = None
    self._ip_monit = None

  def __repr__(self):
    msg = ("{0.__class__} Xmit:{0.xmit} Max_Tries: {0.max_tries} "
           "Call: {0.call} Pause: {0._pause}")
    return msg.format(self)

  def heartbeat(self):
    sq_struct = struct.Struct('!IHH')
    packet = ctypes.create_string_buffer(sq_struct.size)
    sq_struct.pack_into(packet, 0, SQ_MAGIC, SQ_VERSION, SQ_HEARTBEAT)
    return packet.raw

  def pause(self, flag=True):
    self._pause = flag
    sq_struct = struct.Struct('!IHH?')
    packet = ctypes.create_string_buffer(sq_struct.size)
    sq_struct.pack_into(packet, 0, SQ_MAGIC, SQ_VERSION, SQ_PAUSE, flag)
    return packet.raw

  def encode(self):
    packet = ctypes.create_string_buffer(SQ_STRUCT.size)
    SQ_STRUCT.pack_into(packet, 0, SQ_MAGIC, SQ_VERSION, SQ_DATA, self.max_tries,
                        self.xmit, self._pause, self._shutdown, self._call)
    return packet.raw

  def decode(self, packet):
    sq_header = struct.Struct('!IHH')
    buffer = ctypes.create_string_buffer(packet[:sq_header.size], sq_header.size)
    data = sq_header.unpack_from(buffer)
    magic, version, pkt_type = data[:3]
    if magic != SQ_MAGIC or version < SQ_VERSION:
      raise IOError("SQS packet error")

    if pkt_type == SQ_HEARTBEAT:
      return

    elif pkt_type == SQ_PAUSE:
      sq_struct = struct.Struct('!IHH?')
      buffer = ctypes.create_string_buffer(packet, sq_struct.size)
      data = sq_struct.unpack_from(buffer)
      magic, version, pkt_type, pause = data
      self._pause = pause


    elif pkt_type == SQ_DATA:
      buffer = ctypes.create_string_buffer(packet, SQ_STRUCT.size)
      data = SQ_STRUCT.unpack_from(buffer)
      magic, version, pkt_type, max_tries, xmit, pause, shutdown, call = data
      self.max_tries = max_tries
      self.xmit = xmit
      self._call = call.strip(b'\0x00')
      self._pause = pause
      self._shutdown = shutdown

  @property
  def xmit(self):
    return self.__xmit__

  @xmit.setter
  def xmit(self, val):
    assert isinstance(val, int)
    self.__xmit__ = 0 if val < 0 else val

  @property
  def call(self):
    return self._call.decode('utf-8')

  @call.setter
  def call(self, val):
    assert isinstance(val, str)
    self._call = val[:10].upper().encode('utf-8')

  @property
  def ip_wsjt(self):
    return self._ip_wsjt

  @ip_wsjt.setter
  def ip_wsjt(self, val):
    assert isinstance(val, tuple), "socket tuple expected"
    self._ip_wsjt = val

  @property
  def ip_monit(self):
    return self._ip_monit

  @ip_monit.setter
  def ip_monit(self, val):
    assert isinstance(val, tuple), "socket tuple expected"
    self._ip_monit = val

  def is_pause(self):
    return self._pause
