#!/usr/bin/env python
import select
import socket
import time
import logging
import sys

from datetime import datetime
from pymongo import MongoClient

import sqstatus

SRV_ADDR = ('127.0.0.1', 2240)

logging.basicConfig(level=logging.DEBUG)

def onehour():
  return int(datetime.utcnow().timestamp()) - 3600

def halfhour():
  return int(datetime.utcnow().timestamp()) - 1800

def purge():
  logging.info('Purging records')
  db = MongoClient('localhost').wsjt
  req = {
    'logged': False,
    'time': {"$lt": halfhour()}
  }
  for obj in db.black.find(req):
    logging.warning("Delete: {}, {}".format(obj['call'], datetime.fromtimestamp(obj['time'])))
    db.black.delete_one({"_id": obj['_id']})

def ctrl(sock):
  next_send = 0
  status = sqstatus.SQStatus()
  sock.sendto(status.heartbeat(), SRV_ADDR)
  while True:
    for fd in select.select([sys.stdin, sock], [], [], 1)[0]:
      if fd == sys.stdin:
        line = sys.stdin.readline()
        line = line.rstrip().lower()
        if line == 'help':
          print('** Command list\n pause\n run\n status\n skip\n max <nn>\n purge\n exit\n')
        elif line == 'pause':
          sock.sendto(status.pause(True), SRV_ADDR)
        elif line == 'run':
          sock.sendto(status.pause(False), SRV_ADDR)
        elif line == 'status':
          sock.sendto(status.heartbeat(), SRV_ADDR)
        elif line == 'skip':
          sock.sendto(status.heartbeat(), SRV_ADDR)
          data, ip_addr = sock.recvfrom(1024)
          status.decode(data)
          status.xmit = 0
          sock.sendto(status.encode(), ip_addr)
        elif line.startswith('max'):
          try:
            cmd, nb = line.split()
            sock.sendto(status.max(nb))
          except ValueError:
            print('***** Error')
        elif line in ("quit", "exit"):
          sock.close()
          sys.exit()
        elif line == "purge":
          purge()
        else:
          print('** {}'.format(line))
          sock.sendto(status.heartbeat(), SRV_ADDR)
      elif fd == sock:
        data, _ = fd.recvfrom(1024)
        status.decode(data)
        print(status)
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
  try:
    ctrl(sock)
  except KeyboardInterrupt:
    sock.close()
