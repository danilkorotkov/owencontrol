# -*- coding: utf-8 -*-
import sys, os, time, string
from PyQt4 import QtCore, QtGui, uic 
from PyQt4.Qt import Qt
from PyQt4.QtGui import *
from PyQt4.QtCore import QObject, SIGNAL

MainInterfaceWindow = "graphwindow.ui" 
Ui_MainWindow, QtBaseClass = uic.loadUiType(MainInterfaceWindow)


class GraphWindow (QtGui.QMainWindow, Ui_MainWindow):
    """MainWindow inherits QMainWindow"""
    path="logs/"
    lf1=[]
    
    def __init__ ( self, parent = None ):
        super(GraphWindow, self).__init__(parent)
        Ui_MainWindow.__init__(self)
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
        
        self.ExitButton.pressed.connect(self.test)
        self.listWidget.itemClicked.connect(self.test5)
    
        self.scene=QtGui.QGraphicsScene()
        self.graphicsView.setScene(self.scene)
        
        self.test2()
 
    def __del__ ( self ):
        self.ui = None

    # Funkzija zavershenija raboti okna.        
    def test(self):
        self.close()
        
        # Funkzija vivoda imen failov v spisok
    def test2(self):
        
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
                minutes='0'+str(s[4])
            else:
                minutes=str(s[4])
            s='%s-%s-%s %s:%s' % (str(s[0])[2:],str(s[1]),str(s[2]),str(s[3]),minutes)+u" Линия: "+l
            self.lf1[i].append(s)
        

        for i in range(len(lf)):    # Pomeschaem imena log failov v vizual'nij spisok
            self.listWidget.addItem(self.lf1[i][1])

# Funkzija reakzii na nazatie fajla v spiske.
    def test5(self):
        self.statusBar.showMessage(u"Имя лога: "+self.lf1[self.listWidget.currentRow()][0]) # Vivodim coobschenie v statusBar.
        self.test4()  # Vizivaem funkziju prorisovki grafika  

# Funkzija prorisovki grafikov.  
    def test4(self): 
        
        file_name=self.lf1[self.listWidget.currentRow()][0] # параметр функции - имя лог файла 

        lines=[]   # читаем лог файл
        file=open(self.path+file_name)
        for line in file:
            lines.append(line.rstrip('\n')) # Читаем файл по строкам
        file.close()

        #print lines

        cpw=[]                             # Временный массив для разбиения строк на составлящие (возмоно не нужен)
        for i in range(len(lines)):
            cpw.append(lines[i].strip().split(','))

        #print cpw    

        if 9 <= len(lines) < 29: #обработка длины лога
            step=len(lines)-2
        elif len(lines) < 9:
            self.scene.clear()
            textItem = QGraphicsTextItem("",None,self.scene)
            textItem.setHtml(self.SetInfoPanelText ('неверный лог'))
            textItem.setPos(self.graphicsView.width()*0.9/2, self.graphicsView.height()*0.9/2)
            return
        else:
            step=29

        xy=[] # Заполнение массива координат графиков
        for i in range(len(cpw)):
            xy.append([])
            for j in range(len(cpw[i])):
                xy[-1].append(float(cpw[i][j]))

        #print xy

        cpw=[] # clear memory
        x1=xy[-1][0]
        x0=xy[0][0] # Вычитание нулевой точки по оси x
        for i in range(len(xy)):
            xy[i][0]=xy[i][0]-x0
        
        maxx=xy[-1][0] # поиск максимумов координат графиков
        maxy=0
        maxz=0
        max3=0
        max4=0
        max5=0
        for i in range(len(xy)):
            if maxy < xy[i][1]:
                maxy=xy[i][1]
            if maxz < xy[i][2]:
                maxz=xy[i][2]
            if max3 < xy[i][3]:
                max3=xy[i][3]
            if max4 < xy[i][4]:
                max4 = xy[i][4]
            if max5 < xy[i][5]:
                max5 = xy[i][5]
                

        kx=int(self.graphicsView.width()*0.9)/xy[-1][0] # Выбор коэффициентов нормировки по осям (сцена центрируется автоматически)
        ky=int(self.graphicsView.height()*0.95)/maxy
        
        for i in range(len(xy)): # Преобразование координат графиков к экранным
            xy[i][0]*=kx # Простое растяжение по оси
            xy[i][1]=(maxy-xy[i][1])*ky # Растяжение по оси с отражением
            if maxz != 0:
                xy[i][2]=maxy*xy[i][2]/(maxz*2) # Нормировка на 1 и далее нормировка на примерно половину высоты графика температуры
            if max3 != 0:
                xy[i][3]=maxy*xy[i][3]/(max3*2.1)
            if max4 != 0:
                xy[i][4]=maxy*xy[i][4]/(max4*2.2)
            if max5 != 0:
                xy[i][5]=maxy*xy[i][5]/(max5)
        
        self.scene.clear() # Очистка сцены
        
        for i in range(len(xy)-1): # Вывод графика температуры
           self.scene.addLine(xy[i][0],xy[i][1],xy[i+1][0],xy[i+1][1],QPen(QColor(Qt.black),4)) 
                
        ssx=int(maxx/step) # Шаг сетки по оси x
        mx=0
        i=0
        while mx < maxx: # Прорисовка штрихов по оси x
            mx+=ssx
            i+=1

            if (mx%60) <10:
                tempor=str(mx//60)+':0'+str(mx%60)
            else:
                tempor=str(mx//60)+':'+str(mx%60)
            textItem = QGraphicsTextItem(tempor,None,self.scene).setPos(mx*kx-15, self.graphicsView.height()*0.38+20*(i%2))
            
        self.scene.addLine(0,maxy*ky,mx*kx,maxy*ky,QPen(QColor(Qt.blue))) # Ось x

        ssy=int(maxy/step) # Шаг сетки по оси y
        my=0
        while my < maxy: # Прорисовка штрихов по оси y.
            my+=ssy
            
            textItem = QGraphicsTextItem(str(my),None,self.scene).setPos(0, (maxy-my)*ky)
            textItem1 = QGraphicsTextItem(str(int(my*max5/maxy)),None,self.scene).setPos(mx*kx+10, (maxy-my)*ky)
        self.scene.addLine(0,maxy*ky,0,(maxy-my)*ky,QPen(QColor(Qt.black),4)) # Ось y. 
        self.scene.addLine(mx*kx,maxy*ky,mx*kx,(maxy-my)*ky,QPen(QColor(Qt.yellow),4)) # Ось y2. 

        nx=0 # Прорисовка вертикальных линий сетки.
        while nx < maxx:
            nx+=ssx
            self.scene.addLine(nx*kx,maxy*ky,nx*kx,(maxy-my)*ky,QPen(QColor(Qt.black),0.3))
            
        ny=0 # Прорисовка горизонтальных линий сетки.
        while ny < maxy:
            ny+=ssy
            self.scene.addLine(0,(maxy-ny)*ky,mx*kx,(maxy-ny)*ky,QPen(QColor(Qt.black),0.3))

        ust=file_name.split('_')[-1] # Выделение уствки из имени файла
        ust=int(ust.split('.')[0])
#        print ust
        for i in range(len(xy)-1): # Вывод остальных графиков
           self.scene.addLine(xy[i][0],(maxy-ust)*ky,xy[i+1][0],(maxy-ust)*ky,QPen(QColor(Qt.red),4)) # график уставки
           self.scene.addLine(xy[i][0],(maxy-xy[i][2])*ky,xy[i+1][0],(maxy-xy[i+1][2])*ky,QPen(QColor(Qt.cyan),4)) # второй график
           self.scene.addLine(xy[i][0],(maxy-xy[i][3])*ky,xy[i+1][0],(maxy-xy[i+1][3])*ky,QPen(QColor(Qt.magenta),4)) # третий график
           self.scene.addLine(xy[i][0],(maxy-xy[i][4])*ky,xy[i+1][0],(maxy-xy[i+1][4])*ky,QPen(QColor(Qt.green),4))   # четвёртый график
           self.scene.addLine(xy[i][0],(maxy-xy[i][5])*ky,xy[i+1][0],(maxy-xy[i+1][5])*ky,QPen(QColor(Qt.yellow),4))   # пятый график
        
    # легенда    
        lx=mx*kx+10-260
        ly=my*ky/5-60
        lh=220
        lw=200
        self.scene.addRect(lx,ly,lw,lh,QPen(QColor(Qt.black)),QBrush(QColor(Qt.white)))
        
        textItem = QGraphicsTextItem("",None,self.scene)
        l=file_name.split('_')[1]
        if l=="1":
            
            textItem.setHtml(self.SetInfoPanelText ("Линия 6,5 м."))# parse from file
        else:
            textItem.setHtml(self.SetInfoPanelText ("Линия 3,5 м."))# parse from file
        textItem.setPos(lx+20, ly+0)
        
        self.scene.addLine(lx+10,ly+45,lx+45,ly+45,QPen(QColor(Qt.black),4) )
        #textItem = QGraphicsTextItem("",None,self.scene).setPos(lx+50, ly+35)
        textItem = QGraphicsTextItem("",None,self.scene)
        textItem.setHtml(self.SetInfoPanelText ('Температура'))
        textItem.setPos(lx+50, ly+25)
        
        self.scene.addLine(lx+10,ly+65,lx+45,ly+65,QPen(QColor(Qt.red),4) )
#        textItem = QGraphicsTextItem("Ustavka",None,self.scene).setPos(lx+50, ly+55)
        textItem = QGraphicsTextItem("",None,self.scene)
        textItem.setHtml(self.SetInfoPanelText ('Уставка ' + str(ust) ))
        textItem.setPos(lx+50, ly+45)

        self.scene.addLine(lx+10,ly+85,lx+45,ly+85,QPen(QColor(Qt.cyan),4) )
#        textItem = QGraphicsTextItem("Power",None,self.scene).setPos(lx+50, ly+75)
        textItem = QGraphicsTextItem("",None,self.scene)
        textItem.setHtml(self.SetInfoPanelText ('Мощность'))
        textItem.setPos(lx+50, ly+65)
        
        self.scene.addLine(lx+10,ly+105,lx+45,ly+105,QPen(QColor(Qt.magenta),4) )
#        textItem = QGraphicsTextItem("State",None,self.scene).setPos(lx+50, ly+95)
        textItem = QGraphicsTextItem("",None,self.scene)
        textItem.setHtml(self.SetInfoPanelText ('Состояние'))
        textItem.setPos(lx+50, ly+85)

        self.scene.addLine(lx+10,ly+125,lx+45,ly+125,QPen(QColor(Qt.green),4) )
#        textItem = QGraphicsTextItem("Fan",None,self.scene).setPos(lx+50, ly+115)
        textItem = QGraphicsTextItem("",None,self.scene)
        textItem.setHtml(self.SetInfoPanelText ('Вентилятор'))
        textItem.setPos(lx+50, ly+105)

        self.scene.addLine(lx+10,ly+145,lx+45,ly+145,QPen(QColor(Qt.yellow),4) )
#        textItem = QGraphicsTextItem("Fan",None,self.scene).setPos(lx+50, ly+115)
        textItem = QGraphicsTextItem("",None,self.scene)
        textItem.setHtml(self.SetInfoPanelText ('Тены '+str(max5)))
        textItem.setPos(lx+50, ly+125)

# Фактическая выдаржка
        dx=x1-x0
        min=dx//60
        #hour=int(min//60)
        min=int(min%60)
        #hour=str(hour)
        #if len(hour)==1:
        #    hour='0'+hour
        min=str(min)
        #if len(min)==1:
        #    min='0'+min
        #t=hour+':'+min
        t=min+' мин'
        textItem = QGraphicsTextItem("",None,self.scene)
        textItem.setHtml(self.SetInfoPanelText ('Выдержка '+t))
        textItem.setPos(lx+20, ly+145)
# Начало
        s=time.gmtime(float(x0))
        min=str(s[4])
        if len(min)==1:
            min='0'+min
        hour=str(s[3])
        if len(hour)==1:
            hour='0'+hour
        
        t=hour+':'+min        
        textItem = QGraphicsTextItem("",None,self.scene)
        textItem.setHtml(self.SetInfoPanelText ('Начало '+t))
        textItem.setPos(lx+20, ly+165)
# Окончание
        s=time.gmtime(float(x1))
        min=str(s[4])
        if len(min)==1:
            min='0'+min
        hour=str(s[3])
        if len(hour)==1:
            hour='0'+hour
        t=hour+':'+min
        textItem = QGraphicsTextItem("",None,self.scene)
        textItem.setHtml(self.SetInfoPanelText ('Окончание '+t))
        textItem.setPos(lx+20, ly+185)
        
        
    def SetInfoPanelText (self,text):
        out=_translate("GraphWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
    "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
    "p, li { white-space: pre-wrap; }\n"
    "</style></head><body style=\" font-family:\'Free Helvetian\'; font-size:12pt; font-weight:400; font-style:normal;\">\n"
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
