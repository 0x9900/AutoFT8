#
# BSD 3-Clause License
#
# Copyright (c) 2021, Fred W6BSD
# All rights reserved.
# See licence file for more information.
#
import logging
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

  def wait(self):
    while True:
      for _ in range(13):
        if self._killed:
          return
        time.sleep(1)

      while datetime.utcnow().second not in self.period:
        if self._killed:
          return
        time.sleep(.2)
      yield

  def shutdown(self):
    LOG.info('Transmit thread killed')
    self._killed = True

  def stop_transmit(self, flag):
    LOG.debug('Stop transmit')
    stop_pkt = wsjtx.WSHaltTx()
    stop_pkt.tx = flag
    if not self.status.ip_wsjt:
      return
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
    for _ in self.wait():
      # LOG.warning(self.status)
      if self.status.is_pause():
        self.status.call = ''
        self.status.xmit = 0
        self.stop_transmit(False)
        continue

      if self.status.xmit:
        self.status.xmit -= 1
        continue

      call = self.call_selector.get()
      if not call:
        self.status.call = ''
        self.stop_transmit(True)
        continue

      LOG.info('Calling: %s dist: %d SNR: %d', call['call'], int(call['distance']), call['SNR'])
      self.status.xmit = self.status.max_tries
      self.status.call = call['call']
      # encode the packet and start transmitting.
      xmit_packet = Transmit.encode_xmit(call)
      self.transmit(xmit_packet)

      self.status.db.black.update_one(
        {"call": call['call']},
        {"$set": {"time": Transmit.timestamp(), "logged": False}},
        upsert=True)
    # Exit
    self.sock.close()

  @staticmethod
  def timestamp():
    return int(datetime.utcnow().timestamp())

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
