# -*- coding: utf-8 -*-
from operator import methodcaller
import sys, os, time, string
from PyQt4 import QtCore, QtGui, uic 
from PyQt4.Qt import Qt
from PyQt4.QtGui import *
#from PyQt4.QtCore import QObject, SIGNAL
import numpy as np
import pyqtgraph as pg

MainInterfaceWindow = "graphwindow.ui" 
Ui_MainWindow, QtBaseClass = uic.loadUiType(MainInterfaceWindow)


class GraphWindow (QtGui.QMainWindow, Ui_MainWindow):
    """MainWindow inherits QMainWindow"""
    path="logs/"
    lf1=[]

    def __init__ ( self, parent = None ):
        super(GraphWindow, self).__init__(parent)
        Ui_MainWindow.__init__(self)
        pg.setConfigOption('background', (194, 194, 194))
        pg.setConfigOption('foreground', (0, 0, 0))
        self.setupUi(self)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.listWidget.verticalScrollBar().setStyleSheet(_fromUtf8(
            "QScrollBar:vertical {width: 35px; background: rgb(194, 194, 194); margin: 0px;}\n"
            "QScrollBar::handle:vertical {min-height: 35x;}\n"
            "QScrollBar::sub-line:vertical {subcontrol-position: top; subcontrol-origin: content; height: 70px; }\n"
            "QScrollBar::add-line:vertical {subcontrol-position: bottom; subcontrol-origin: content; height: 70px; }\n"
            "QScrollBar::down-arrow:vertical, QScrollBar::up-arrow:vertical {background: NONE;}\n"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {background: none;}"))

        self.ExitButton.pressed.connect(self.exit)
        self.listWidget.itemClicked.connect(self.letsgo)

        self.sceneW = int(self.graphicsView.width() * 0.9)
        self.sceneH = int(self.graphicsView.height() * 0.9)
        self.graphicsView.addLegend(size=None, offset=(self.sceneW * 0.8, self.sceneH * 0.25))

        self.searchLogs()
 
    def __del__ ( self ):
        self.ui = None


    def exit(self):  # Funkzija zavershenija raboti okna.
        self.close()
        

    def searchLogs(self): # Funkzija vivoda imen failov v spisok
        
        ld=os.listdir(self.path)   # Berem spisok failov  directorija

        lf=[]                           # Fil'truem faili s rasshireniem .txt - log faili
        for i in range(len(ld)):
            if ld[i].endswith(".txt"):
                lf.append(ld[i])

        lf.sort()      # сортировка по времени
        lf.reverse()   # в обратном порядке
        
        self.lf1=[]
        for i in range(len(lf)):
            self.lf1.append([])
            self.lf1[i].append(lf[i])
            t=lf[i].split('_')[0]
            s=time.localtime(float(t))
            l=lf[i].split('_')[1]
            if l=="1":
               l=u"6,5 м"
            else:
               l=u"3,5 м" 
            
            if s[4]<10:
                minutes='0'+str(s.tm_min)
            else:
                minutes=str(s.tm_min)
            s='%s-%s-%s %s:%s' % (str(s.tm_year)[2:],str(s.tm_mon),str(s.tm_mday),str(s.tm_hour),minutes)+u" Линия: "+l
            self.lf1[i].append(s)
        

        for i in range(len(lf)):    # Pomeschaem imena log failov v vizual'nij spisok
            self.listWidget.addItem(self.lf1[i][1])


    def letsgo(self): # выбор файла в списке
        self.statusBar.showMessage(u"Имя лога: "+self.lf1[self.listWidget.currentRow()][0]) # Vivodim coobschenie v statusBar.
        self.draw()  # Vizivaem funkziju prorisovki grafika

    def draw(self):  # рисуем график

        file_name = self.lf1[self.listWidget.currentRow()][0]  # параметр функции - имя лог файла

        ust=file_name.split('_')[-1] # Выделение уставки из имени файла
        ust=int(ust.split('.')[0])

        try:  # читаем лог файл
            with open(self.path + file_name) as f:
                lines = f.read().splitlines()  # Читаем файл по строкам
        except IOError:
            self.graphicsView.setTitle(title=u'Ошибка чтения файла')
            return
        
        if lines[-1]=='':
            lines.pop()
        else:
            pass

        # Временный массив для разбиения строк на составлящие

        cpw = list(map(methodcaller("split", ","), lines))

        timeAxis=[] # Заполнение массива координат графиков
        tempLine=[]
        powerLine=[]
        stateLine=[]
        fanLine=[]
        heatLine=[]
        try:
            for i in range(len(cpw)):
                timeAxis.append(float(cpw[i][0]))
                tempLine.append(float(cpw[i][1]))
                powerLine.append(float(cpw[i][2]))
                stateLine.append(float(cpw[i][3]))
                fanLine.append(float(cpw[i][4]))
                heatLine.append(float(cpw[i][5]))
        except ValueError:
            self.graphicsView.setTitle(title=u'Ошибка')
            return
        length=len(timeAxis)
        delt=0
        x0=timeAxis[0]
        x1=timeAxis[-1]
        iter=0
        try:
            while delt==0:
                if stateLine[iter]==1:
                    delt=timeAxis[iter]
                    index=iter
                if iter<length:
                    iter+=1
        except IndexError:
            #self.graphicsView.setTitle(title=u'Ошибка')
            delt=delt=timeAxis[-1]
            index=-1
            #return
        cpw=[] # clear memory
        lines=[]

        dx=x1-delt

        for i in range(length): # Вычитание нулевой точки по оси x
            timeAxis[i]=timeAxis[i]-x0

        timeAxis=np.array(timeAxis)
        tempLine = np.array(tempLine)
        powerLine = np.array(powerLine)
        stateLine = np.array(stateLine)
        fanLine = np.array(fanLine)
        heatLine = np.array(heatLine)
        ustLine = np.arange(length)
        ustLine[::]=ust

        maxTemp=tempLine.max() # поиск максимумов координат графиков
        maxPower=powerLine.max()
        maxHeat=heatLine.max()

        if maxPower != 0:
            powerLine=maxTemp*powerLine/(maxPower*2) # Нормировка на 1 и далее нормировка на примерно половину высоты графика температуры
        stateLine=maxTemp*stateLine/2.1
        fanLine=maxTemp*fanLine/2.2

        timeAxis = timeAxis/60
        self.graphicsView.clear()
        try:
            self.graphicsView.plotItem.legend.items = []
            while self.graphicsView.plotItem.legend.layout.count() > 0:
                self.graphicsView.plotItem.legend.layout.removeAt(0)
        except AttributeError:
            pass

        self.graphicsView.setLabel('left', u'Температура, с')
        self.graphicsView.setLabel('bottom', u'Время, мин')

        self.graphicsView.showGrid(x=True, y=True, alpha=None)
        self.graphicsView.plot(x=timeAxis, y=tempLine, name=self.SetInfoPanelText('Температура'),pen=pg.mkPen('k', width=3))
        self.graphicsView.plot(x=timeAxis, y=powerLine, name=self.SetInfoPanelText('Мощность'), pen=pg.mkPen('r', width=3))
        self.graphicsView.plot(x=timeAxis, y=heatLine, name=self.SetInfoPanelText('ТЭНы'), pen=pg.mkPen('y', width=4))
        self.graphicsView.plot(x=timeAxis, y=stateLine, name=self.SetInfoPanelText('Состояние'), pen=pg.mkPen('m', width=3))
        self.graphicsView.plot(x=timeAxis, y=fanLine, name=self.SetInfoPanelText('Вентиляторы'), pen=pg.mkPen('g', width=3))

        self.graphicsView.plot(x=timeAxis, y=ustLine, name=self.SetInfoPanelText('Уставка'+str(ust)), pen=pg.mkPen('b', width=3))
        #self.graphicsView.addLine(y=maxHeat, name=self.SetInfoPanelText('ТЭН'), pen=pg.mkPen('y', width=3))
        #self.graphicsView.addLine(x=timeAxis[index], name=self.SetInfoPanelText('Выдержка'), pen=pg.mkPen('m', width=3))

        #dx=timeAxis[-1]-delt
        delay=dx//60
        delay=int(delay%60)
        delay=str(delay) +' мин' # Выдержка

        s=time.localtime(float(x0))
        m=str(s[4])
        if len(m)==1:
            m='0'+m
        h=str(s[3])
        if len(h)==1:
            h='0'+h
        t_start=h+':'+m # Начало

        s=time.localtime(float(x1))
        m=str(s[4])
        if len(m)==1:
            m='0'+m
        h=str(s[3])
        if len(h)==1:
            h='0'+h
        t_end=h+':'+m # # Окончание

        self.graphicsView.setTitle(title=self.SetInfoPanelText(
            'Начало: ' + t_start + ', Окончание: ' + t_end + ', Выдержка: ' + delay + ', ТЭН: ' + str(
                maxHeat)))


    def SetInfoPanelText (self,text):
        out=_translate("GraphWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
    "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
    "p, li { white-space: pre-wrap; }\n"
    "</style></head><body style=\" font-family:\'Free Helvetian\'; font-size:14pt; font-weight:400; font-style:normal;\">\n"
    "<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">%s</p></body></html>"%text, None)
        return out

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)  
