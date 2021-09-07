#
import logging
import select
import socket
import threading
import time

MAX_COUNTER = 7
SEND_TIME = 5

LOG = logging.getLogger('Monitor')

class Monitor(threading.Thread):

  def __init__(self, ip_address, status, daemon=None):
    assert isinstance(ip_address, (tuple, list)), "A tuple (ip, port) is expected"
    super().__init__(daemon=daemon)
    self._ip_address = ip_address
    self._clients = {}
    self._status = status
    self._run_loop = True

    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(False)
    sock.setblocking(0)
    sock.bind(self._ip_address)
    self.sock = sock

  def add_client(self, client_ip):
    self._clients[client_ip] = MAX_COUNTER

  def update_client(self, client_ip):
    if client_ip not in self._clients:
      return
    self._clients[client_ip] -= 1

  def purge_client(self):
    """Purge unseen clients"""
    to_delete = [c for c, x in self._clients.items() if x < 1]
    for item in to_delete:
      del self._clients[item]

  def shutdown(self):
    self._run_loop = False
    LOG.info('Monitor thread killed')

  def run(self):
    LOG.debug('Starting monitor thread')
    next_send = 0
    force_send = False
    while self._run_loop:
      fd_in, _, _ = select.select([self.sock], [], [], .25)
      if fd_in:
        for _fd in fd_in:
          data, ip_from = _fd.recvfrom(1024)
          self.add_client(ip_from)
          self._status.decode(data)
          LOG.debug("%s", self._status)
          force_send = True

      now = int(time.time())
      if force_send or  next_send < now:
        force_send = False
        next_send = SEND_TIME + now
        LOG.debug('NB clients: %d', len(self._clients))
        for client in self._clients:
          LOG.debug('Send to client %s', client)
          self.sock.sendto(self._status.encode(), client)
          self.update_client(client)
        self.purge_client()
    # exit
    self.sock.close()
