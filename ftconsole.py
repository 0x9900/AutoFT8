#!/usr/bin/env python
#
"""
AutoFT is a program that takes complete control
of WSJTX and fully automatizes the calling sequence.
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
from PyQt5.QtWidgets import (QMainWindow, QTextBrowser, QTextEdit, QAction, QApplication,QMessageBox,QFileDialog)

import sqstatus

SRV_ADDR = ('127.0.0.1', 2240)
DB = MongoClient('localhost').wsjt

TEXT_STYLE = """QTextBrowser {
  background-color: rgb(0,0,30);
  border-color: rgb(0,0,0);
  border-width: 5px;
  border-style: solid;
}"""


def delta(seconds):
  return int(datetime.utcnow().timestamp()) - seconds


class FTCtl(QMainWindow):

  def __init__(self):
    super().__init__()
    self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    self.sock.settimeout(.5)
    self.status = sqstatus.SQStatus()

    self._cache = ""
    self.initUI()

    self.timer = QTimer()
    self.timer.setInterval(1000)
    self.timer.timeout.connect(self.get_status)
    self.timer.start()

  def initUI(self):
    font = self.font()
    font.setPointSize(16)
    self.setFont(font)

    tb1 = self.addToolBar('Actions')
    self.textEdit = QTextBrowser() #QTextEdit()
    # self.textEdit.setFont(QFont('Courier', 14))
    self.textEdit.setFont(QFont('Andale Mono', 16))
    self.textEdit.setOpenExternalLinks(True)
    self.textEdit.setStyleSheet(TEXT_STYLE)
    self.textEdit.setText("AutoFT Started...")
    self.setCentralWidget(self.textEdit)

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

    aboutAction=QAction('About', self)
    aboutAction.setStatusTip('About')
    aboutAction.triggered.connect(self.about)

    tb1 = self.addToolBar('Actions')
    tb1.addAction(pauseAction)
    tb1.addAction(runAction)
    tb1.addAction(skipAction)
    tb1.addAction(purgeAction)

    tb2 = self.addToolBar('About')
    tb2.addAction(aboutAction)

    tb3 = self.addToolBar('Exit')
    tb3.addAction(exitAction)

    self.setGeometry(100, 100, 720, 480)
    self.setWindowTitle('AutoFT Control')
    self.setWindowIcon(QIcon('text.png'))
    self.statusBar()

    self.show()

  def get_status(self):
    self.sock.sendto(self.status.heartbeat(), SRV_ADDR)
    try:
      data, _ = self.sock.recvfrom(1024)
    except (socket.timeout, socket.error) as err:
      self.statusBar().showMessage('Connection {} the sequencer is not running'.format(err))
      return

    self.status.decode(data)
    self.statusBar().showMessage('Transmission: {}'.format('Paused' if self.status.is_pause() else 'On'))

    msg = ('Call: <a href="http://www.qrz.com/db/{0.call}">{0.call}</a> '
           '- Xmit sequence: {0.xmit} - Max Tries: {0.max_tries} '
           '- Pause: {0._pause}').format(self.status)

    if not self.status.is_pause() and self._cache != msg:
      self._cache = msg
      self.textEdit.append(msg.format(self.status))
      self.textEdit.moveCursor(QTextCursor.End)

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
    self.textEdit.append("Transmission paused...")
    self.textEdit.moveCursor(QTextCursor.End)
    try:
      self.sock.sendto(self.status.pause(True), SRV_ADDR)
    except (socket.timeout, socket.error) as err:
      self.statusBar().showMessage('Connection {} the sequencer is not running'.format(err))
      return

  def run(self):
    self.textEdit.append("Transmission active...")
    self.textEdit.moveCursor(QTextCursor.End)
    try:
      self.sock.sendto(self.status.pause(False), SRV_ADDR)
    except (socket.timeout, socket.error) as err:
      self.statusBar().showMessage('Connection {} the sequencer is not running'.format(err))
      return

  def purge(self):
    self.textEdit.append('Purge calls...')
    req = dict(logged=False, time={"$lt": delta(900)})
    idx = 0
    for idx, obj in enumerate(DB.black.find(req), start=1):
      self.textEdit.append("Delete: {}, {}".format(obj['call'], datetime.fromtimestamp(obj['time'])))
      DB.black.delete_one({"_id": obj['_id']})
    self.textEdit.append("{} records deleted".format(idx))
    self.textEdit.moveCursor(QTextCursor.End)

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

    self.textEdit.append('Skip call...'.format(sqs.call))
    self.textEdit.moveCursor(QTextCursor.End)


if __name__ == '__main__':

  app = QApplication(sys.argv)
  ex = FTCtl()
  sys.exit(app.exec_())
