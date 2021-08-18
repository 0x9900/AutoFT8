# Header class for all WSJT received packets.  This class handles the header and
# will create class for handling the packet depending on the packet type in
# the header.
import struct

from enum import Enum

WS_MAGIC = 0xADBCCBDA

class PacketType(Enum):
  HEARTBEAT = 0
  STATUS = 1
  DECODE = 2
  CLEAR = 3
  REPLY = 4
  QSOLOGGED = 5
  CLOSE = 6
  REPLAY = 7
  HALTTX = 8
  FREETEXT = 9
  WSPRDECODE = 10
  LOCATION = 11
  LOGGEDADIF = 12
  HIGHLIGHTCALLSIGN = 13
  SWITCHCONFIGURATION = 14
  CONFIGURE = 15


class WSPacket:

  def __init__(self, pkt):
    self._index = 0            # Keeps track of where we are in the packet parsing!
    self._packet = pkt
    self._decode()

  def _decode(self):
    # in here depending on the Packet Type we create the class to handle the packet!
    fmt = '!III'
    size = struct.calcsize(fmt)
    magic, schema, pkt_type = struct.unpack(fmt, self._packet[:size])
    self._index += size
    self.MagicNumber = magic
    self.SchemaVersion = schema
    self.PacketType = pkt_type
    self.ClientID = self._getString()

  def __repr__(self):
    return "{} magic={:#X} id={:s}".format(
      self.__class__, self.MagicNumber, self.ClientID
    )

  def _getString(self):
    length = self._getInt32()
    # Empty strings have a length of zero whereas null strings have a
    # length field of 0xffffffff.
    if length == -1:
      return None
    fmt = "!{:d}s".format(length)
    start = self._index
    end = start + length
    string, *_ = struct.unpack(fmt, self._packet[start:end])
    self._index += length
    return string.decode('utf-8')

  def _getDateTime(self):
    time_offset = 0
    date_off = self._getLongLong()
    time_off = self._getuInt32()
    time_spec = self._getByte()
    if time_spec == 2:
      time_offset = self._getInt32()
    return (date_off, time_off, time_spec, time_offset)

  def _getByte(self):
    data, *_ = struct.unpack("!B", self._packet[self._index:self._index+1])
    self._index += 1
    return data

  def _getBool(self):
    data, *_ = struct.unpack("!?", self._packet[self._index:self._index+1])
    self._index += 1
    return data

  def _getInt32(self):
    data, *_ = struct.unpack("!i", self._packet[self._index:self._index+4])
    self._index += 4
    return data

  def _getuInt32(self):
    data, *_ = struct.unpack("!I", self._packet[self._index:self._index+4])
    self._index += 4
    return data

  def _getLongLong(self):
    data, *_ = struct.unpack("!Q", self._packet[self._index:self._index+8])
    self._index += 8
    return data

  def _getDouble(self):
    data, *_ = struct.unpack("!d", self._packet[self._index:self._index+8])
    self._index += 8
    return data


class WSHeartbeat(WSPacket):
  """Packet Type 0 Heartbeat"""

  def __init__(self, pkt):
    super().__init__(pkt)

  def _decode(self):
    super()._decode()
    self.MaximumSchema = self._getuInt32()
    self.Version = self._getString()
    self.Revision = self._getString()


class WSStatus(WSPacket):
  """Packet Type 1 Status"""

  def __init__(self, pkt):
    super().__init__(pkt)

  def _decode(self):
    super()._decode()
    self.Frequency = self._getLongLong()
    self.Mode = self._getString()
    self.DXCall = self._getString()
    self.Report = self._getString()
    self.TxMode = self._getString()
    self.TxEnabled = self._getBool()
    self.Transmitting = self._getBool()
    self.Decoding = self._getBool()
    self.RxDF = self._getuInt32()
    self.TxDF = self._getuInt32()
    self.DECall = self._getString()
    self.DEgrid = self._getString()
    self.DXgrid = self._getString()
    self.TxWatchdog = self._getBool()
    self.Submode = self._getString()
    self.Fastmode = self._getBool()

  def __repr__(self):
    fields = """Frequency Mode DXCall Report TxMode TxEnabled Transmitting
    Decoding RxDF TxDF DECall DEgrid DXgrid TxWatchdog Submode
    Fastmode"""
    elem = []
    for field in fields.split():
      elem.append("{}: {}".format(field, getattr(self, field)))
    return ', '.join(elem)


class WSDecode(WSPacket):
  """Packet Type 2"""

  def __init__(self, pkt):
    super().__init__(pkt)

  def _decode(self):
    super()._decode()
    self.New = self._getBool()
    self.Time = self._getuInt32()
    self.snr = self._getInt32()
    self.DeltaTime = self._getDouble()
    self.DeltaFrequency = self._getuInt32()
    self.Mode = self._getString()
    self.Message = self._getString()
    self.LowConfidence = self._getBool()
    self.OffAir = self._getBool()

  def __repr__(self):
    return "<WSJTX> New: {}, Δ Time: {: 1.2f}, SNR: {:+3d} - {}".format(self.New, self.DeltaTime, self.snr, self.Message)


class WSClear(WSPacket):
  """Packet Type 3"""

  def __init__(self, pkt):
    super().__init__(pkt)

  def _decode(self):
    super()._decode()
    if self._index < len(self._packet):
      self.Window = self._getByte()
    else:
      self.Window = None

  def __repr__(self):
    return "{} magic={:#X} type={:d} id={:s} window={}".format(
      self.__class__, self.MagicNumber, self.PacketType, self.ClientID,
      self.Window)


class WSReply(WSPacket):
  """Packet Type 4 Reply IN message to client"""

  def __init__(self, pkt):
    super().__init__(pkt)


class WSLogged(WSPacket):
  """Packet Type 5 QSO Logged"""

  def __init__(self, pkt):
    super().__init__(pkt)

  def _decode(self):
    super()._decode()
    dt_tuple = self._getDateTime()
    self.DateOff = dt_tuple[0]
    self.TimeOff = dt_tuple[1]
    self.TimeOffSpec = dt_tuple[2]
    self.TimeOffOffset = dt_tuple[3]
    self.DXcall = self._getString()
    self.DXgrid = self._getString()
    self.DialFrequency = self._getLongLong()
    self.Mode = self._getString()
    self.ReportSent = self._getString()
    self.ReportReceived = self._getString()
    self.TxPower = self._getString()
    self.Comments = self._getString()
    self.Name = self._getString()
    dt_tuple = self._getDateTime()
    self.DateOn = dt_tuple[0]
    self.TimeOn = dt_tuple[1]
    self.TimeOnSpec = dt_tuple[2]
    self.TimeOnOffset = dt_tuple[3]


class WSClose(WSPacket):
  """Packet Type 6 Close"""

  def __init__(self, pkt):
    super().__init__(pkt)

class WSReplay(WSPacket):
  """Packet Type 7 Replay (IN)"""

  def __init__(self, pkt):
    super().__init__(pkt)


class WSHaltTx(WSPacket):
  """Packet Type 8 Halt Tx (IN)"""

  def __init__(self, pkt):
    super().__init__(pkt)


class WSFreeText(WSPacket):
  """Packet Type 9 (IN)"""

  def __init__(self, pkt):
    super().__init__(pkt)


class WSWSPRDecode(WSPacket):
  """Packet Type 10 WSPR Decode"""

  def __init__(self, pkt):
    super().__init__(pkt)


class WSADIF(WSPacket):

  def __init__(self, pkt):
    super().__init__(pkt)
    self.id = 0
    self.adif = ''

  def Decode(self):
    super()._decode()
    self.id = self._getuInt32()
    self.adif = self._getString()

  def __repr__(self):
    return self.adif

def ft8_decode(pkt):
  """Look at the packets header and return a class corresponding to the packet"""

  magic, schema, pkt_type = struct.unpack("!III", pkt[:12])
  if magic != WS_MAGIC:
    raise ValueError('Not a WSJT-X packet')

  if pkt_type == PacketType.HEARTBEAT.value:
    return WSHeartbeat(pkt)
  elif pkt_type == PacketType.STATUS.value:
    return WSStatus(pkt)
  elif pkt_type == PacketType.CLEAR.value:
    return WSClear(pkt)
  elif pkt_type == PacketType.DECODE.value:
    return WSDecode(pkt)
  elif pkt_type == PacketType.QSOLOGGED.value:
    return WSLogged(pkt)
  elif pkt_type == PacketType.CLOSE.value:
    return WSClose(pkt)
  elif pkt_type == PacketType.LOGGEDADIF.value:
    return WSADIF(pkt)
  else:
    raise NotImplementedError("Packet type '{:d}' unknown".format(pkt_type))
