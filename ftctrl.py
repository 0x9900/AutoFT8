#!/usr/bin/env python
#
# BSD 3-Clause License
#
# Copyright (c) 2021, Fred Cirera
# All rights reserved.
#

import select
import socket
import time
import logging
import sys

from datetime import datetime
from pymongo import MongoClient

import sqstatus

SRV_ADDR = ('127.0.0.1', 2240)
DB = MongoClient('localhost').wsjt

logging.basicConfig(format='%(name)s %(asctime)s %(levelname)s: %(funcName)s: %(message)s',
                    datefmt='%c', level=logging.INFO)

def onehour():
  return int(datetime.utcnow().timestamp()) - 3600

def halfhour():
  return int(datetime.utcnow().timestamp()) - 1800

def quarterhour():
  return int(datetime.utcnow().timestamp()) - 900

def purge():
  logging.info('Purging records')
  req = {
    'logged': False,
    'time': {"$lt": quarterhour()}
  }
  for obj in DB.black.find(req):
    logging.warning("Delete: {}, {}".format(obj['call'], datetime.fromtimestamp(obj['time'])))
    DB.black.delete_one({"_id": obj['_id']})

def ctrl(sock):
  next_send = 0
  status = sqstatus.SQStatus()
  sock.sendto(status.heartbeat(), SRV_ADDR)
  while True:
    for fd in select.select([sys.stdin, sock], [], [], 1)[0]:
      if fd == sys.stdin:
        line = sys.stdin.readline()
        line = line.rstrip().upper()
        if line == 'HELP':
          print('** Command list\n pause\n run\n status\n skip\n max <nn>\n purge\n exit\n')
        elif line == 'PAUSE':
          sock.sendto(status.pause(True), SRV_ADDR)
        elif line == 'RUN':
          sock.sendto(status.pause(False), SRV_ADDR)
        elif line == 'STATUS':
          sock.sendto(status.heartbeat(), SRV_ADDR)
        elif line == 'SKIP':
          sock.sendto(status.heartbeat(), SRV_ADDR)
          data, ip_addr = sock.recvfrom(1024)
          status.decode(data)
          status.xmit = 0
          sock.sendto(status.encode(), ip_addr)
        elif line.startswith('MAX'):
          try:
            cmd, nb = line.split()
            sock.sendto(status.max(nb))
          except ValueError:
            print('***** Error')
        elif line in ("QUIT", "EXIT"):
          sock.close()
          sys.exit()
        elif line == "PURGE":
          purge()
        else:
          if not line:
            sock.sendto(status.heartbeat(), SRV_ADDR)
            continue
          print('** {}'.format(line))
          result = DB.black.find_one(dict(call=line))
          if result:
            for key, val in result.items():
              print(f"** {key:7s}: {val}")
          else:
            print('** Not found')
          print(f'** https://www.qrz.com/db/{line}')
      elif fd == sock:
        data, _ = fd.recvfrom(1024)
        status.decode(data)
        logging.info(status)
    else:
      now = time.time()
      if next_send < now:
        next_send = now + 30
        sock.sendto(status.heartbeat(), SRV_ADDR)

      if int(time.time()) % 300 == 0:
        purge()

if __name__ == "__main__":
  sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  logging.info("Starting ftctl")
  purge()
  try:
    ctrl(sock)
  except KeyboardInterrupt:
    sock.close()
