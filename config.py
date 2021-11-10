#
# BSD 3-Clause License
#
# Copyright (c) 2021, Fred Cirera
# All rights reserved.
#
#

import os
import json
import logging

LOG = logging.getLogger('Config')

BIND_ADDRESS = '127.0.0.1'
WSJT_PORT = 2238
MONI_PORT = 2240

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

    # default config values
    self.config_data = {
      'mongo_server': 'localhost',
      'bind_address': BIND_ADDRESS,
      'wsjt_port': WSJT_PORT,
      'monitor_port': MONI_PORT,
      'call': 'N0CALL',
      'location': 'CM87vl'
    }

    config_filename = 'autoft.json'
    for path in ['/etc', '~', '.']:
      filename = os.path.expanduser(os.path.join(path, config_filename))
      if os.path.exists(filename):
        LOG.debug('Reading config file: %s', filename)
        self._read_config(filename)

  def to_json(self):
    return json.dumps(self.config_data, indent=4)

  def _read_config(self, filename):
    try:
      with open(filename, 'r') as confd:
        lines = []
        for line in confd:
          line = line.strip()
          if not line or line.startswith('#'):
            continue
          lines.append(line)
        self.config_data.update(json.loads('\n'.join(lines)))
    except ValueError as err:
      LOG.error('Configuration error: "%s"', err)
      sys.exit(os.EX_CONFIG)

  def __getattr__(self, attr):
    if attr not in self.config_data:
      raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__, attr))
    return self.config_data[attr]
