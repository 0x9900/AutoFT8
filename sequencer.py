import logging
import math
import redis
import select
import socket
import struct
import time
import traceback
import sys

import wsjtx

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%c', level=logging.INFO)


HERE = (0, 0)

def distance(origin, dest):
  lat1, lon1 = origin
  lat2, lon2 = dest
  radius = 6371 # km

  dlat = math.radians(lat2 - lat1)
  dlon = math.radians(lon2 - lon1)
  a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
       math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
       math.sin(dlon / 2) * math.sin(dlon / 2))
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
  return int(radius * c)

def azimuth(origin, dest):
  lat1, lon1 = origin
  lat2, lon2 = dest

  dLon = (lon2 - lon1)
  qso = math.cos(math.radians(lat2)) * math.sin(math.radians(dLon))
  y = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(dLon))
  brng = math.atan2(qso,y)
  brng = math.degrees(brng)
  return int(brng)

def grid2latlon(maiden):
  """ Transform a maidenhead grid locator to latitude & longitude """
  assert isinstance(maiden, str), "Maidenhead locator must be a string"

  maiden = maiden.strip().upper()
  maiden_lg = len(maiden)
  assert len(maiden) in [2, 4, 6, 8], 'Locator length error: 2, 4, 6 or 8 characters accepted'

  char_a = ord("A")
  lon = -180.0
  lat = -90.0

  lon += (ord(maiden[0]) - char_a) * 20
  lat += (ord(maiden[1]) - char_a) * 10

  if maiden_lg >= 4:
    lon += int(maiden[2]) * 2
    lat += int(maiden[3]) * 1
  if maiden_lg >= 6:
    lon += (ord(maiden[4]) - char_a) * 5.0 / 60
    lat += (ord(maiden[5]) - char_a) * 2.5 / 60
  if maiden_lg >= 8:
    lon += int(maiden[6]) * 5.0 / 600
    lat += int(maiden[7]) * 2.5 / 600

  return lat, lon


def save(rdb, data):
  """Save the traffic in the database"""

  def _coef(d, s):
    s = s if s else 1
    return d / math.pow(s, -1)

  try:
    oper, call, locator = data.Message.split()
  except ValueError as err:
    logging.error("%s, %s", data.Message, err)
    return
  if oper != 'CQ':
    return

  try:
    dist = distance(HERE, grid2latlon(locator))
  except (ValueError, AssertionError) as err:
    logging.error("%s, %s", data.Message, err)
    return

  coef = _coef(dist, data.snr)
  logging.info("%-7s %s - Distance: %d - SNR: %-3.2f C: %-5.4f",
               call, locator, dist, data.snr, coef)
  rdb.zadd('callers', {call: coef})
  rdb.expire(call, 30)
  #dict(call=call, locator=locator, snr=data.snr, delta=data.DeltaTime))

def cleanup(rdb):
  nb_entries = rdb.zcard('callers')
  rdb.zpopmin('callers', nb_entries)


class SaveQSO:
  def __init__(self, rdb):
    self._db = rdb
    self._prefix = 'qso.'

  def save(self, call):
    rdb.set(self._prefix + call, 1)


def process(rdb, fds):
  while fds:
    fd = fds.pop()
    data, addr = fd.recvfrom(1024)
    packet = wsjtx.ft8_decode(data)

    if isinstance(packet, wsjtx.WSStatus):
      rdb.set('TxEnabled', int(packet.TxEnabled))
    elif isinstance(packet, wsjtx.WSDecode):
      save(rdb, packet)
    elif isinstance(packet, wsjtx.WSClear):
      logging.info(repr(packet))
      cleanup(rdb)
    elif isinstance(packet, wsjtx.WSLogged):
      print(packet.__dict__)
    else:
      logging.warning(packet)


def main():
  global HERE
  HERE = grid2latlon('CM87vl')
  logging.info('Starting auto ham')
  rdb = redis.Redis(host='localhost', port=6379, db=0)
  sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  sock.bind(('127.0.0.1',2238))
  sock.setblocking(0)
  cleanup(rdb)
  try:
    while True:
      nin, _, _ = select.select([sock], [], [], 4)
      if nin:
        process(rdb, nin)

  except KeyboardInterrupt:
    sock.close()
    traceback.print_exc(file=sys.stdout)

if __name__ == "__main__":
  main()
