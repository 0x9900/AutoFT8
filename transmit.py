#
# BSD 3-Clause License
#
# Copyright (c) 2021, Fred W6BSD
# All rights reserved.
# See licence file for more information.
#
import logging
import operator
import re
import socket
import threading
import time

from datetime import datetime
from importlib import import_module

import wsjtx

from config import Config

LOG = logging.getLogger('Transmit')
# LOG.setLevel(logging.DEBUG)

class Transmit(threading.Thread):

  def __init__(self, status, period, daemon=None):
    config = Config()
    if isinstance(period, range):
      period = list(period)
    super().__init__(daemon=daemon)
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.period = period
    self.status = status
    self._killed = False
    # import the selector from plugins
    *module_name, class_name = config.select_method.split('.')
    module_name = '.'.join(['plugins'] + module_name)
    module = import_module(module_name)
    klass = getattr(module, class_name)
    self.call_selector = klass(config, status.db)
    self.call = config.call

  def wait(self):
    while True:
      for _ in range(12):
        time.sleep(1)
        if self._killed:
          return

      while datetime.utcnow().second not in self.period:
        time.sleep(.25)
        if self._killed:
          break
      break

  def shutdown(self):
    LOG.info('Transmit thread killed')
    self._killed = True

  def stop_transmit(self, flag):
    LOG.debug('Stop transmit')
    if not self.status.ip_wsjt:
      return
    stop_pkt = wsjtx.WSHaltTx()
    stop_pkt.tx = flag
    try:
      self.sock.sendto(stop_pkt.raw(), self.status.ip_wsjt)
    except:
      logging.error(self.status.ip_wsjt)
      raise

  def transmit(self, packet):
    LOG.debug('Transmiting %s', packet)
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.sock.sendto(packet, self.status.ip_wsjt)

  def run(self):
    # Wait for the very end of the sequence
    while True:
      LOG.info(self.status)
      self.wait()
      if self._killed:
        break

      LOG.info(self.status)

      if self.status.is_pause():
        self.stop_transmit(True)
        self.status.xmit = 0
        self.status.call = ''
        while self.status.is_pause():
          if self._killed:
            return
          time.sleep(.5)
        continue

      if self.is_incontact(self.status.call):
        self.status.call = ''

      call = self.is_inprogress(self.status.call)
      if call:
        LOG.info('is_inprogress: %s', call['Message'])
        self.transmit(Transmit.encode_xmit(call))
        self.status.call = call['call']
        continue

      call = self.run_pileup()
      if call:
        LOG.info('run_pileup: %s', call['Message'])
        self.transmit(Transmit.encode_xmit(call))
        self.status.call = call['call']
        continue

      self.status.xmit -= 1
      if not self.status.call or not self.status.xmit:
        call = self.call_selector.get()
        if call:
          LOG.info('%s: %s', self.call_selector, call['Message'])
          self.transmit(Transmit.encode_xmit(call))
          self.status.call = call['call']
          self.status.xmit = self.status.max_tries
          self.status.db.black.update_one(
            {"call": call['call']},
            {"$set": {"time": Transmit.timestamp(), "logged": False}},
            upsert=True)
          continue

      self.stop_transmit(True)
    # Exit
    self.sock.close()

  def is_incontact(self, call):
    exp = re.compile(r'{}|CQ'.format(self.call))
    request = {
      "call": call,
      "to": {"$not": exp},
      "timestamp": {"$gt": Transmit.timestamp() - 15},
    }
    return self.status.db.calls.count_documents(request)

  def is_inprogress(self, call):
    # Search if someone is trying to contact us
    request =  {
      "call": call,
      "timestamp": {"$gt": Transmit.timestamp() - 60},
    }
    if not call:
      return

    LOG.debug('req = %s', request)
    record = self.status.db.calls.find_one(request)
    if not record or record['to'] not in ('CQ',  self.call):
      record = None
    return record

  def run_pileup(self):
    calls = []
    request = {
      "to": self.call,
      "timestamp": {"$gt": Transmit.timestamp() - 15}
    }

    LOG.debug('req = %s', request)
    record = self.status.db.calls.find(request)
    for call in record:
      coef = Transmit.coefficient(call['distance'], call['SNR'])
      calls.append((coef, call))

    if not calls:
      return

    calls.sort(key=operator.itemgetter(0))
    _, call = calls.pop()
    return call

  @staticmethod
  def coefficient(distance, snr):
    return distance * 10**(snr/10)

  @staticmethod
  def timestamp():
    return int(datetime.utcnow().timestamp())

  @staticmethod
  def encode_xmit(call):
    packet = wsjtx.WSReply()
    packet.call = call['call']
    packet.Time = call['Time']
    packet.SNR = call['SNR']
    packet.DeltaTime = call['DeltaTime']
    packet.DeltaFrequency = call['DeltaFrequency']
    packet.Mode = call['Mode']
    packet.Message = call['Message']
    return packet.raw()
