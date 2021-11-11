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
import wsjtx

from config import Config
from transmit import Transmit

RE_EXCHANGES = {
  "CQ": re.compile(r'^(?P<to>CQ) ((?P<extra>.*) |)(?P<call>\w+)(|/\w+) (?P<grid>[A-Z]{2}[0-9]{2})'),
  "REPLY": re.compile(r'^(?P<to>\w+)(|/\w+) (?P<call>\w+)(|/\w+) (?P<grid>[A-Z]{2}[0-9]{2})'),
  "SNR": re.compile(r'^(?P<to>\w+)(|/\w+) (?P<call>\w+)(|/\w+) (?P<snr>(0|[-+]\d+))'),
  "SNRR": re.compile(r'^(?P<to>\w+)(|/\w+) (?P<call>\w+)(|/\w+) R(?P<snr>(0|[-+]\d+))'),
  "R73": re.compile(r'^(?P<to>\w+)(|/\w+) (?P<call>\w+)(|/\w+) (?P<R73>(RRR|R*73))'),
}

STATUS = sqstatus.SQStatus()

def geoloc(lat, lon):
  return {"type": "Point", "coordinates" : [lat, lon]}

def parse_packet(packet):
  """Save the traffic in the database"""
  config = Config()
  here = geo.grid2latlon(config.location)
  for ex_type, regex in RE_EXCHANGES.items():
    match = regex.match(packet.Message)
    if match:
      break

  if not match:
    logging.error('Cannot parse message "%s"', packet.Message)
    return None

  data = match.groupdict().copy()
  data['timestamp'] = Transmit.timestamp()
  data.update(packet.as_dict())
  exchange = type('EXCHANGE', (object, ), match.groupdict())

  if ex_type == 'CQ' or ex_type == 'REPLY':
    try:
      lat, lon = geo.grid2latlon(exchange.grid)
      dist = geo.distance(here, (lat, lon))
      direction = geo.azimuth(here, (lat, lon))
    except (ValueError, AssertionError) as err:
      logging.error("%s, %s", packet.Message, err)
      return None
    data['coordinates'] = geoloc(lat, lon)
    data['distance'] = dist
    data['direction'] = direction
    logging.debug("From: %-7s To: %-7s - %s Dist: %6d Dir: %3d SNR: % 6.2f ΔTime: %1.2f",
                  exchange.call, exchange.to, exchange.grid, dist, direction,
                  packet.SNR, packet.DeltaTime)
    if hasattr(exchange, 'ex_type') and exchange.extra not in (None, 'NA'):
      logging.warning('Ignoring: %s'. packet.Message)
      return None
  elif ex_type == "SNR" or ex_type == "SNRR":
    if exchange.to == 'W6BSD' and exchange.call == STATUS.call:
      STATUS.xmit = STATUS.max_tries
      logging.info("From: %-7s To: %-7s - %s: %4d - SNR: % 6.2f ΔTime % 1.2f",
                   exchange.call, exchange.to, ex_type, int(exchange.snr), packet.SNR,
                   packet.DeltaTime)
    elif exchange.call == STATUS.call and exchange.to != 'W6BSD':
      STATUS.xmit = 0
  elif ex_type == "R73":
    if exchange.to == 'W6BSD':
      STATUS.xmit += STATUS.max_tries
      logging.info('** From: %-7s To: %-7s  %s - SNR: % 6.3f',
                   exchange.call, exchange.to, exchange.R73, packet.SNR)

  return data


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
    data = parse_packet(packet)
    if data:
      logging.info(packet)
      STATUS.db.calls.update_one({'call': data['call']},
                                 {"$set": data},
                                 upsert=True)
  elif isinstance(packet, wsjtx.WSLogged):
    STATUS.xmit = 0
    STATUS.db.black.update_one({"call": packet.DXCall},
                               {"$set": {"time": Transmit.timestamp(), "logged": True}},
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
  config = Config()

  STATUS.db = MongoClient(config.mongo_server).wsjt

  # WSJT-X server channel
  sock_wsjt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock_wsjt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock_wsjt.setblocking(False) # Set socket to non-blocking mode
  sock_wsjt.setblocking(0)
  bind_addr = socket.gethostbyname(config.bind_address)
  sock_wsjt.bind((bind_addr, config.wsjt_port))

  logging.info('WSJT-X  IP: %s, Port: %d', bind_addr, config.wsjt_port)
  logging.info('Monitor IP: %s, Port: %d', bind_addr, config.monitor_port)

  try:
    #    xmit_thread = Transmit(STATUS, range(0, 60, 15), daemon=True)
    xmit_thread = Transmit(STATUS, range(14, 60, 15), daemon=True)
    xmit_thread.start()
    sqmonitor = monitor.Monitor((bind_addr, config.monitor_port), STATUS, daemon=True)
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
  logging.basicConfig(format='%(name)s %(asctime)s %(levelname)s: %(funcName)s: %(message)s',
                      datefmt='%c', level=logging.INFO)
  main()
