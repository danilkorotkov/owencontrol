# -*- coding: utf-8 -*-
import sys, time, string, calendar
from PyQt4 import QtCore
#--------------temp measure-----------------------
class TimeThread(QtCore.QThread): # time label
    def __init__(self, time_signal, parent=None):
        super(TimeThread, self).__init__(parent)
        self.time_signal = time_signal
        self.isRun=False

    def run(self):
        while self.isRun:
            s=time.localtime()
            
            if s[4]<10:
                minutes='0'+str(s[4])
            else:
                minutes=str(s[4])
                
            if s[3]<10:
                hours='0'+str(s[3])
            else:
                hours=str(s[3])
                
            if s[5]<10:
                secundes='0'+str(s[5])
            else:
                secundes=str(s[5])
            
            month=_fromUtf8(calendar.month_name[s.tm_mon])
            day=str(s[2])
            dayname=_fromUtf8(calendar.day_name[s.tm_wday])
            out=['','','']
            
            out[0]=day+', ' + month
            out[1]='%s:%s:%s' % (hours,minutes,secundes)
            out[2]=dayname
            
            
            self.time_signal.emit(out)
            
            time.sleep(1)

    def stop(self):
        self.isRun=False
        
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s