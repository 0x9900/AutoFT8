#
# BSD 3-Clause License
#
# Copyright (c) 2021, Fred W6BSD
# All rights reserved.
#
#

import os
import yaml
import logging

LOG = logging.getLogger('Config')

DEFAULT_CONFIG = """
  mongo_server: "localhost"
  bind_address: "127.0.0.1"
  wsjt_port: 2238
  monitor_port: 2240
  call: "N0CALL"
  location: "CM87vl"
"""

class Config:
  _instance = None
  config_data = None
  def __new__(cls, *args, **kwargs):
    if cls._instance is None:
      cls._instance = super(Config, cls).__new__(cls)
      cls._instance.config_data = {}
    return cls._instance

  def __init__(self):
    if self.config_data:
      return

    config_filename = 'autoft.yaml'
    for path in ['/etc', '~', '.']:
      filename = os.path.expanduser(os.path.join(path, config_filename))
      if os.path.exists(filename):
        LOG.debug('Reading config file: %s', filename)
        self._read_config(filename)

  def to_yaml(self):
    return yaml.dump(self.config_data)

  def _read_config(self, filename):
    try:
      with open(filename, 'r') as confd:
        configuration = yaml.safe_load(confd)
      self.config_data.update(configuration)
    except ValueError as err:
      LOG.error('Configuration error: "%s"', err)
      sys.exit(os.EX_CONFIG)

  def get(self, key, default=None):
    if key not in self.config_data:
      return default
    value = self.config_data[key]
    if isinstance(value, dict):
      return type(key, (object, ), value)
    else:
      return value

  def __getattr__(self, attr):
    if attr not in self.config_data:
      raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__, attr))
    return self.config_data[attr]
