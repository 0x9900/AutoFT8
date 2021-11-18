#
# BSD 3-Clause License
#
# Copyright (c) 2021, Fred W6BSD
# All rights reserved.
#

import logging
import operator

from . import CallSelector

LOG = logging.getLogger('plugins.Any')

class Any(CallSelector):

  def get(self):
    calls = []
    req = self.db.calls.find({
      "to": "CQ",
      "timestamp": {"$gt": Any.timestamp() - 15}
    })
    for obj in req:
      coef = Any.coefficient(obj['distance'], obj['SNR'])
      calls.append((coef, obj))

    calls.sort(key=operator.itemgetter(0), reverse=True)
    LOG.info([(int(c[0]), c[1]['call']) for c in calls])
    for _, call in calls:
      if not self.db.black.count_documents({"call": call['call']}):
        return call
    return None
