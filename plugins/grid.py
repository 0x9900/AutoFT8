#

import logging
import operator
import re

from . import CallSelector

LOG = logging.getLogger('plugins.Grid')

class Grid(CallSelector):

  def __init__(self, config, db):
    super().__init__(config, db)
    regexps = [f'({r})' for r in self.config.squares]
    self.match = re.compile('|'.join(regexps)).match

  def get(self):
    calls = []
    req = self.db.calls.find({
      "to": "CQ",
      "timestamp": {"$gt": Grid.timestamp() - 15}
    })
    for obj in req.sort([('SNR', -1)]):
      if self.match(obj['grid']):
        coef = obj['distance'] * 10**(obj['SNR']/10)
        calls.append((coef, obj))

    calls.sort(key=operator.itemgetter(0), reverse=True)
    LOG.info([(int(c[0]), c[1]['call']) for c in calls])
    for _, call in calls:
      if not self.db.black.count_documents({"call": call['call']}):
        return call
    return None
