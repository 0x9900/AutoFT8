#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# BSD 3-Clause License
#
# Copyright (c) 2021, Fred W6BSD
# All rights reserved.
#

"""
AutoFT is a program that takes complete control
of WSJTX and fully automatate the calling sequence.
AutoFT try to figure out which of the CQ call has
the best chances of succeeding.

(c) 2021 Fred W6BSD

"""

import logging
import select
import socket
import sys
import time

from datetime import datetime
from pymongo import MongoClient

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import (QIcon, QTextCursor, QFont)
from PyQt5.QtWidgets import (QMainWindow, QTextBrowser, QAction,
                             QApplication, QMessageBox, QFileDialog)

import sqstatus

from config import Config

CONFIG = Config()
SRV_ADDR = (CONFIG.bind_address, CONFIG.monitor_port)
DB = MongoClient(CONFIG.mongo_server).wsjt

TEXT_STYLE = """QTextBrowser {
  background-color: rgb(0, 0, 30);
  border-color: rgb(0, 0, 0);
  border-width: 5px;
  border-style: solid;
}"""


def delta(seconds):
  return int(datetime.utcnow().timestamp()) - seconds

def purge_calls(seconds=1800):
  req = dict(logged=False, time={"$lt": delta(seconds)})
  response = DB.black.delete_many(req)
  return response.deleted_count

class FTCtl(QMainWindow):

  def __init__(self):
    super().__init__()
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.sock.settimeout(.5)
    self.status = sqstatus.SQStatus()

    self._cache = ""
    self.initUI()

    self.timer = QTimer()
    self.timer.setInterval(2500)
    self.timer.timeout.connect(self.get_status)
    self.timer.start()

    self.purge_timer = QTimer()
    self.purge_timer.setInterval(30000)
    self.purge_timer.timeout.connect(purge_calls)
    self.purge_timer.start()


  def initUI(self):
    font = self.font()
    font.setPointSize(16)
    self.setFont(font)

    tb1 = self.addToolBar('Actions')
    self.textLog = QTextBrowser()
    self.textLog.setFont(QFont('Courier New', 14))
    # self.textLog.setFont(QFont('Andale Mono', 16))
    self.textLog.setOpenExternalLinks(True)
    self.textLog.setStyleSheet(TEXT_STYLE)
    self.textLog.setText("AutoFT Started...")
    self.setCentralWidget(self.textLog)

    exitAction = QAction('Exit', self)
    exitAction.setShortcut('Ctrl+Q')
    exitAction.setStatusTip('Exit application')
    exitAction.triggered.connect(self.close)

    pauseAction=QAction('Pause', self)
    pauseAction.setShortcut('Ctrl+P')
    pauseAction.setStatusTip('Pause transmission')
    pauseAction.triggered.connect(self.pause)

    runAction=QAction('Run', self)
    runAction.setShortcut('Ctrl+R')
    runAction.setStatusTip('Run transmission')
    runAction.triggered.connect(self.run)

    purgeAction=QAction('Purge', self)
    purgeAction.setShortcut('Ctrl+D')
    purgeAction.setStatusTip('Purge database')
    purgeAction.triggered.connect(self.purge)

    skipAction=QAction('Skip', self)
    skipAction.setShortcut('Ctrl+S')
    skipAction.setStatusTip('Skip this call')
    skipAction.triggered.connect(self.skip)

    clearAction=QAction('Clear', self)
    clearAction.setShortcut('Ctrl+L')
    clearAction.setStatusTip('Clear screen')
    clearAction.triggered.connect(self.clear)

    aboutAction=QAction('About', self)
    aboutAction.setStatusTip('About')
    aboutAction.triggered.connect(self.about)

    tb1 = self.addToolBar('Actions')
    tb1.addAction(pauseAction)
    tb1.addAction(runAction)
    tb1.addAction(skipAction)
    tb1.addAction(purgeAction)
    tb1.addAction(clearAction)

    tb2 = self.addToolBar('About')
    tb2.addAction(aboutAction)

    tb3 = self.addToolBar('Exit')
    tb3.addAction(exitAction)

    self.setGeometry(100, 100, 720, 480)
    self.setWindowTitle('AutoFT Control')
    self.setWindowIcon(QIcon('text.png'))
    self.statusBar()

    self.show()

  def print(self, line):
    self.textLog.append(line)
    self.textLog.moveCursor(QTextCursor.End)

  def get_status(self):
    self.sock.sendto(self.status.heartbeat(), SRV_ADDR)
    try:
      data, _ = self.sock.recvfrom(1024)
    except (socket.timeout, socket.error) as err:
      self.statusBar().showMessage('Connection {} the sequencer is not running'.format(err))
      return

    self.status.decode(data)
    if not self.status.call:
      return

    req = {"call": self.status.call, "to": CONFIG.call}
    call = DB.calls.find_one(req)
    if call:
      msg = ('Reply: <a href="http://www.qrz.com/db/{0[call]}">{0[call]}</a> '
             '- <b>{0[Message]:18s}</b>'
             '- Xmit seq: {1.xmit} '
             '- Pause: {1._pause}').format(call, self.status)
    else:
      msg = ('Calling: <a href="http://www.qrz.com/db/{0.call}">{0.call}</a> '
             '- Xmit seq: {0.xmit} - Pause: {0._pause}').format(self.status)

    if self._cache != msg:
      self._cache = msg
      self.print(msg)

  def about(self):
    QMessageBox.about(self, "About AutoFT", __doc__)

  def closeEvent(self, event):
    reply = QMessageBox.question(self, 'Quit AutoFT', "Are you sure to quit?",
                                 QMessageBox.Yes | QMessageBox.No,
                                 QMessageBox.Yes)
    if reply == QMessageBox.Yes:
      event.accept()
    else:
      event.ignore()

  def pause(self):
    self.print("Transmission paused... Click Run to transmit.")
    try:
      self.sock.sendto(self.status.pause(True), SRV_ADDR)
    except (socket.timeout, socket.error) as err:
      self.statusBar().showMessage('Connection {} the sequencer is not running'.format(err))
      return

  def run(self):
    self.print("Transmission active...")
    try:
      self.sock.sendto(self.status.pause(False), SRV_ADDR)
    except (socket.timeout, socket.error) as err:
      self.statusBar().showMessage('Connection {} the sequencer is not running'.format(err))
      return

  def purge(self):
    nb_del = purge_calls(120)
    self.print(f"Purge calls cache: {nb_del} records deleted")

  def skip(self):
    sqs = sqstatus.SQStatus()
    try:
      self.sock.sendto(self.status.heartbeat(), SRV_ADDR)
      data, ip_addr = self.sock.recvfrom(1024)
      sqs.decode(data)
      sqs.xmit = 0
      self.sock.sendto(sqs.encode(), ip_addr)
    except (socket.timeout, socket.error) as err:
      self.statusBar().showMessage('Connection {} the sequencer is not running'.format(err))
      return

    self.print('Skip call...'.format(sqs.call))

  def clear(self):
    self.textLog.setText('')


if __name__ == '__main__':
  app = QApplication(sys.argv)
  ex = FTCtl()
  sys.exit(app.exec_())
