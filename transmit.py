import logging
import socket
import threading
import time

from operator import itemgetter
from datetime import datetime

import wsjtx

LOG = logging.getLogger('Transmit')
# LOG.setLevel(logging.DEBUG)

class Transmit(threading.Thread):

  def __init__(self, status, period, daemon=None):
    if isinstance(period, range):
      period = list(period)
    super().__init__(daemon=daemon)
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.period = period
    self.status = status
    self._killed = False


  def wait(self):
    while True:
      for _ in range(12):
        if self._killed:
          return
        time.sleep(1)

      while datetime.utcnow().second not in self.period:
        if self._killed:
          return
        time.sleep(.5)
      yield

  def shutdown(self):
    LOG.info('Transmit thread killed')
    self._killed = True

  def stop_transmit(self, flag):
    LOG.debug('Stop transmit')
    stop_pkt = wsjtx.WSHaltTx()
    stop_pkt.tx = flag
    self.sock.sendto(stop_pkt.raw(), self.status.ip_wsjt)

  def transmit(self, packet):
    LOG.debug('Transmiting %s', packet)
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.sock.sendto(packet, self.status.ip_wsjt)

  def run(self):
    # Wait for the very end of the sequence
    for _ in self.wait():

      LOG.warning(self.status)
      if self.status.is_pause():
        self.status.call = ''
        self.status.xmit = 0
        self.stop_transmit(False)
        continue

      if self.status.xmit:
        self.status.xmit -= 1
        continue

      call = get_grid(self.status)
      # get a call
      # call = get_call(self.status)
      if not call:
        self.status.call = ''
        self.stop_transmit(True)
        continue

      LOG.warning('Calling: %s dist: %d SNR: %d', call['call'], int(call['distance']), call['SNR'])
      self.status.xmit = self.status.max_tries
      self.status.call = call['call']
      # encode the packet and start transmitting.
      xmit_packet = Transmit.encode_xmit(call)
      self.transmit(xmit_packet)

      self.status.db.black.update_one(
        {"call": call['call']},
        {"$set": {"time": timestamp(), "logged": False}},
        upsert=True)
    # Exit
    self.sock.close()

  @staticmethod
  def encode_xmit(call):
    if not call:
      return None
    packet = wsjtx.WSReply()
    packet.call = call['call']
    packet.Time = call['Time']
    packet.SNR = call['SNR']
    packet.DeltaTime = call['DeltaTime']
    packet.DeltaFrequency = call['DeltaFrequency']
    packet.Mode = call['Mode']
    packet.Message = call['Message']
    return packet.raw()


def timestamp():
  return int(datetime.utcnow().timestamp())


def get_grid(status):
  grids = ['IO', 'JO', 'KO', 'IN', 'JN', 'KN']
  calls = []
  req = status.db.calls.find({
    "to": "CQ",
    "timestamp": {"$gt": timestamp() - 15}
  })
  for obj in req.sort([('SNR', -1)]):
    if obj['grid'][:2] in grids:
      calls.append(obj)

  for call in calls:
    if not status.db.black.count_documents({"call": call['call']}):
      return call
  return None


def get_call(status):
  calls = []
  req = status.db.calls.find({
    "to": "CQ",
    "timestamp": {"$gt": timestamp() - 15}
  })
  for rec in req:
    coef = rec['distance'] * 10**(rec['SNR']/10)
    calls.append((coef, rec))

  calls.sort(key=itemgetter(0), reverse=True)
  for _, call in calls:
    if not status.db.black.count_documents({"call": call['call']}):
      return call
  return None
