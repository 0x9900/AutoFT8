#
# BSD 3-Clause License
#
# Copyright (c) 2021, Fred W6BSD
# All rights reserved.
#

from abc import ABC, abstractmethod
from datetime import datetime

class CallSelector(ABC):

  def __init__(self, config, db):
    self.config = config.get(self.__class__.__name__)
    self.db = db

  @abstractmethod
  def get(self):
    pass

  @staticmethod
  def timestamp():
    return int(datetime.utcnow().timestamp())

  @staticmethod
  def coefficient(distance, snr):
    return distance * 10**(snr/10)
