#!/opt/local/bin/python3.8
#
# BSD 3-Clause License
#
# Copyright (c) 2021, Fred Cirera
# All rights reserved.
#

import logging
import re
import select
import socket
import sys
import threading
import time

from datetime import datetime
from pymongo import MongoClient

import geo
import monitor
import sqstatus
import transmit
import wsjtx

RE_EXCHANGES = {
  "CQ": re.compile(r'^(?P<to>CQ) ((?P<extra>.*) )(?P<call>\w+)(|/\w+) (?P<grid>[A-Z]{2}[0-9]{2})'),
  "REPLY": re.compile(r'^(?P<to>\w+)(|/\w+) (?P<call>\w+)(|/\w+) (?P<grid>[A-Z]{2}[0-9]{2})'),
  "SNR": re.compile(r'^(?P<to>\w+)(|/\w+) (?P<call>\w+)(|/\w+) (?P<snr>(0|[-+]\d+))'),
  "SNRR": re.compile(r'^(?P<to>\w+)(|/\w+) (?P<call>\w+)(|/\w+) R(?P<snr>(0|[-+]\d+))'),
  "R73": re.compile(r'^(?P<to>\w+)(|/\w+) (?P<call>\w+)(|/\w+) (?P<R73>(RRR|R*73))'),
}

BIND_ADDRESS = '127.0.0.1'
WSJT_PORT = 2238
MONI_PORT = 2240

STATUS = sqstatus.SQStatus()

def geoloc(lat, lon):
  return {"type": "Point", "coordinates" : [lat, lon]}

def timestamp():
  return int(datetime.utcnow().timestamp())

def parse_packet(packet):
  """Save the traffic in the database"""

  for ex_type, regex in RE_EXCHANGES.items():
    match = regex.match(packet.Message)
    if match:
      break

  if not match:
    logging.error('Cannot parse message "%s"', packet.Message)
    return packet

  data = match.groupdict().copy()
  data['timestamp'] = timestamp()
  data.update(packet.as_dict())
  exchange = type('EX', (object,), match.groupdict())

  if ex_type == 'CQ' and exchange.extra != 'NA':
    return

  if ex_type == 'CQ' or ex_type == 'REPLY':
    try:
      lat, lon = geo.grid2latlon(exchange.grid)
      dist = geo.distance(HERE, (lat, lon))
      direction = geo.azimuth(HERE, (lat, lon))
    except (ValueError, AssertionError) as err:
      logging.error("%s, %s", packet.Message, err)
      return
    data['coordinates'] = geoloc(lat, lon)
    data['distance'] = dist
    data['direction'] = direction
    logging.debug("From: %-7s To: %-7s - %s Dist: %6d Dir: %3d SNR: % 6.2f ΔTime: %1.2f",
                  exchange.call, exchange.to, exchange.grid, dist, direction,
                  packet.SNR, packet.DeltaTime)
  elif ex_type == "SNR" or ex_type == "SNRR":
    exchange.snr = int(exchange.snr)
    if exchange.to == 'W6BSD':
      STATUS.xmit = STATUS.max_tries
      logging.info("From: %-7s To: %-7s - %s: %4d - SNR: % 6.2f ΔTime % 1.2f",
                   exchange.call, exchange.to, ex_type.lower(), exchange.snr, packet.SNR,
                   packet.DeltaTime)
  elif ex_type == "R73":
    if exchange.to == 'W6BSD':
      STATUS.xmit += STATUS.max_tries
      logging.info('** From: %-7s To: %-7s  %s - SNR: % 6.3f',
                   exchange.call, exchange.to, exchange.R73, packet.SNR)

  STATUS.db.calls.update_one({'call': exchange.call}, {"$set": data}, upsert=True)


def process_wsjt(data, ip_from):
  try:
    packet = wsjtx.ft8_decode(data)
  except (IOError, NotImplementedError) as err:
    logging.error(err)
    return

  logging.debug(packet)
  if isinstance(packet, wsjtx.WSHeartbeat):
    STATUS.ip_wsjt = ip_from
  elif isinstance(packet, wsjtx.WSStatus):
    pass
  elif isinstance(packet, wsjtx.WSDecode):
    parse_packet(packet)
    logging.info(packet)
  elif isinstance(packet, wsjtx.WSLogged):
    STATUS.xmit = 0
    STATUS.db.black.update_one({"call": packet.DXCall},
                               {"$set": {"time": timestamp(), "logged": True}},
                               upsert=True)
    STATUS.call = ''
    logging.info(packet)
  else:
    logging.warning(packet)


def process(sock):
  ip_from = None
  sock = [sock]

  while True:
    fds, _, _ = select.select(sock, [], [], 0.5)
    for fdin in fds:
      data, ip_from = fdin.recvfrom(1024)
      process_wsjt(data, ip_from)


def main():
  logging.info('Starting auto ham')
  STATUS.db = MongoClient('localhost').wsjt

  # WSJT-X server channel
  sock_wsjt = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  sock_wsjt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock_wsjt.setblocking(False) # Set socket to non-blocking mode
  sock_wsjt.setblocking(0)
  sock_wsjt.bind((BIND_ADDRESS, WSJT_PORT))

  logging.info('WSJT-X  IP: %s, Port: %d', BIND_ADDRESS, WSJT_PORT)
  logging.info('Monitor IP: %s, Port: %d', BIND_ADDRESS, MONI_PORT)

  try:
    xmit_thread = transmit.Transmit(STATUS, range(0, 60, 15), daemon=True)
    xmit_thread.start()
    sqmonitor = monitor.Monitor((BIND_ADDRESS, MONI_PORT), STATUS, daemon=True)
    sqmonitor.start()
    process(sock_wsjt)
    time.sleep(300)
  except KeyboardInterrupt:
    logging.info("Shutting down")
    xmit_thread.shutdown()
    xmit_thread.join()
    sqmonitor.shutdown()
    sqmonitor.join()
    sock_wsjt.close()

if __name__ == "__main__":
  logging.basicConfig(format='%(name)s %(asctime)s %(levelname)s: %(message)s',
                      datefmt='%c', level=logging.INFO)
  HERE = geo.grid2latlon('CM87vl')
  main()
