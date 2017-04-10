# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore

from PyQt4.QtCore import *
from PyQt4.QtGui import *

class LongButton( QtGui.QPushButton ):
    def __init__ ( self, parent = None, name=None, *args, **kwargs ):
        QtGui.QPushButton.__init__(self, parent, *args, **kwargs)
        self.setAutoRepeat(True)
        self.setAutoRepeatDelay(1000)
        self.setAutoRepeatInterval(2000)
        self._state = 0
        self.name=name
        self.longpressed=0
        self.released=0
        self.clicked.connect(self.foo)
        
    def foo(self):
        if self.isDown():
            if self._state == 0:
                self._state = 1
            else:
                self.longpressed=1
        elif self._state == 1:
            self._state = 0
            self.longpressed=0
            self.released=1
        else:
            self.released=0