#

import logging
import operator

from . import CallSelector

LOG = logging.getLogger('plugins.Grid')

class Grid(CallSelector):

  def get(self):
    grids = self.config.squares
    calls = []
    req = self.db.calls.find({
      "to": "CQ",
      "timestamp": {"$gt": Grid.timestamp() - 15}
    })
    for obj in req.sort([('SNR', -1)]):
      if obj['grid'][:2] in grids:
        coef = obj['distance'] * 10**(obj['SNR']/10)
        calls.append((coef, obj))

    calls.sort(key=operator.itemgetter(0), reverse=True)
    LOG.info([(int(c[0]), c[1]['call']) for c in calls])
    for _, call in calls:
      if not self.db.black.count_documents({"call": call['call']}):
        return call
    return None
