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
