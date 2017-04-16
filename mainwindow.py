# -*- coding: utf-8 -*-
import sys, time, spidev, pigpio, csv, string, datetime
from PyQt4 import QtCore, QtGui, uic
from PyQt4.Qt import Qt
from PyQt4.QtGui import *
#from PyQt4.QtGui import QIcon, QAction, QKeySequence, QMessageBox
import RPi.GPIO as GPIO
from PyQt4.QtCore import pyqtSlot, QObject, SIGNAL
import metrocss
from UserData import UserData
from LongButton import LongButton
from graphwindow import GraphWindow

#-------------------windows----------------------------
MainInterfaceWindow = "metro_uic.ui" 
Ui_MainWindow, QtBaseClass = uic.loadUiType(MainInterfaceWindow)

InputWindow = "datainput.ui"
Ui_InputWindow, QtBaseClass = uic.loadUiType(InputWindow)

#---------------globals--------------------------------

DEGREE  = u"\u00B0" + 'C'
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

A=21
B=20
C=16
OEBuff=23
Fan2=24
Fan1=25
SSRPwm0=12
SSRPwm1=13
Freq=2
sets={}
FI=300
FT=15

Mux=(C,B,A)
spi = spidev.SpiDev()
pi = pigpio.pi() # Connect to local host.

#--------------temp measure-----------------------
class TempThread(QtCore.QThread): # работа с АЦП в потоке 
    def __init__(self, temp_signal, parent=None):
        super(TempThread, self).__init__(parent)
        self.temp_signal = temp_signal
        self.isRun=False
        self.Va=range(7)

    def run(self):
        while self.isRun:
            Ch=1
            while Ch <= 6:
                self.SetChannel(Ch)
                self.Va[Ch]=self.GetADC()
                Ch += 1
            self.temp_signal.emit(self.Va)
            time.sleep(0.815)

    def stop(self):
        self.isRun=False

    def GetADC(self): #все названия сохранены на языке автора функции
        M0 =0 
        muestras =0
        while muestras <= 49:
            adc = spi.xfer2([0, 0])
            hi = (adc[0] & 0x1F);
            low = (adc[1] & 0xFC);#FE for B, FC for C chip (MCP3201-B/C) ©Danil
            dato = (hi << 8) | low;
            M0 += dato
            muestras += 1
        dato = M0/50
        V = long(dato) * 2.5 / 8192.0;    
        return V

    def SetChannel(self,Ch):
        if Ch >= 1 or Ch <= 6:
            A=Ch>>2
            B=(Ch>>1) & 1
            C=Ch & 1
            GPIO.output(Mux,(A,B,C))


#-------------app window--------------------------
#-------------------------------------------------
class MainWindow(QtGui.QMainWindow, Ui_MainWindow):
    
    temp_signal = QtCore.pyqtSignal(list)
    user_data_signal = QtCore.pyqtSignal(int,int)
    Fan1_On=0 #fan on/off = 0/1
    Fan2_On=0
    Line_65=0 #line on=1 line off=0
    Line_35=0
    T1=T2=t1=t2=0
    TRate1=[] #log набора температуры
    TRate2=[]
    deltaTRate1=0 #хранение текущей скорости роста температуры
    deltaTRate1=0
    iconOn = QtGui.QIcon()
    iconOff = QtGui.QIcon()
    MTemp1=0.0 #храним вычисленное значение температуры
    Mtemp2=0.0
    WaitText="ГОТОВ К ЗАПУСКУ"
    WorkText="НАГРЕВ "
    DelayText="ВЫДЕРЖКА "
    coldStart1=1 #коррекция скорости при отключении датчиков
    coldStart2=1
    coldStart=0 #запуск программы после загрузки
    Heater1=0 # температура тэнов
    Heater2=0
    
    State1=0 #флаги состояния нагрев/выдержка
    State2=0
    justStarted1=0 #флаги начала отсчета времени
    justStarted2=0
    startTime1=0
    startTime2=0
    countdown1=0
    countdown2=0
    level=[0*10000,25*10000,50*10000,75*10000,100*10000]
    
    Fan1Interval=FI # запуск по FT через 300 сек
    Fan1Time=FT
    Fan2Interval=FI
    Fan2Time=FT
    
    file_name_1='' 
    file_name_2=''
    
    
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.iconOff.addPixmap(QtGui.QPixmap("Fanoff.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.iconOn.addPixmap(QtGui.QPixmap("Fanon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)

    #--------------ini set--------------------
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        read_settings()
        self.call_ini_set() #set css from metrocss+T-temp and t-delay from settings
        
        call_board_ini() #set raspberry ports
        self.set_adc() #start ADC data 
        self.set_hotkeys()
        
        self.SetVirtualButtons()
        
    #--------------prog buttons set--------------------
        self.p1_1.pressed.connect(self.SelectProg)
        self.p1_2.pressed.connect(self.SelectProg)
        self.p1_3.pressed.connect(self.SelectProg)
        self.p1_4.pressed.connect(self.SelectUserProg)

        self.p2_1.pressed.connect(self.SelectProg)
        self.p2_2.pressed.connect(self.SelectProg)
        self.p2_3.pressed.connect(self.SelectProg)
        self.p2_4.pressed.connect(self.SelectUserProg)
        self.user_data_signal.connect(self.set_user_data, QtCore.Qt.QueuedConnection)
    
    #--------------params buttons set--------------------
        self.Over_Heat_Ctrl_1.pressed.connect(self.ParamsSet)
        self.Over_Heat_Ctrl_2.pressed.connect(self.ParamsSet)
        self.Sensor1_1.pressed.connect(self.ParamsSet)
        self.Sensor1_2.pressed.connect(self.ParamsSet)
        self.Sensor2_1.pressed.connect(self.ParamsSet)
        self.Sensor2_2.pressed.connect(self.ParamsSet)
        self.Fan1_Allow.pressed.connect(self.ParamsSet)
        self.Fan2_Allow.pressed.connect(self.ParamsSet)
        
    #--------------startstop buttons set--------------------    
        
        self.StartVirt1.pressed.connect(self.StartStop)
        self.StartVirt2.pressed.connect(self.StartStop)
        self.StopVirt1.pressed.connect(self.StartStop)
        self.StopVirt2.pressed.connect(self.StartStop)
        
     #--------------fans buttons set--------------------      
        self.Fan1.pressed.connect(self.SetFans)
        self.Fan2.pressed.connect(self.SetFans)
        
     #--------------history button set-------------------- 
        self.HistoryGraph.pressed.connect(self.ViewHistory)
        
#-------------------------------------------------
#---------------end app window--------------------


#----------------------------methods------------------------------
    @pyqtSlot()
    def ViewHistory(self):
        self.HistoryGraph.setStyleSheet(metrocss.prog_active)
        self.LogsView=GraphWindow(self)
        self.LogsView.show()
        self.HistoryGraph.setStyleSheet(metrocss.prog_passive)

    @pyqtSlot()
    def DoMainWork(self):
        global file_name_1, file_name_2
        i=0
        p=0
        self.CleanAir()
        #it=0
        if self.justStarted1==0 and self.Line_65:
            self.startTime1=datetime.datetime.now()
            self.justStarted1=1
            self.State1=0
            
            file_name_1=str(int(time.time()))+'_1_'+str(self.T1)+'.txt'
            
        if self.justStarted2==0 and self.Line_35:
            self.startTime2=datetime.datetime.now()
            self.justStarted2=1
            self.State2=0
            
            file_name_2=str(int(time.time()))+'_2_'+str(self.T2)+'.txt'
            
        if self.Line_65==1:
            #---------heaters control------------------------
            if self.State1==0:
                delta1=str(datetime.datetime.now()-self.startTime1)[:7]
               #----проверяем границы температура относительно уставки
                if self.MTemp1 <  (self.T1 - 15):
                    pi.hardware_PWM(SSRPwm0, Freq, self.level[4])
                    i=self.level[4]/10000
                    self.InfoPanel1.setHtml(metrocss.SetInfoPanelText(self.WorkText+delta1+" "+str(i)+"%"))
                
                elif (self.T1 - 15) <= self.MTemp1 < self.T1:
                    if self.deltaTRate1 >= 5:
                       pi.hardware_PWM(SSRPwm0, Freq, self.level[0])
                       i=self.level[0]/10000
                    elif 3 <= self.deltaTRate1 <5:
                        pi.hardware_PWM(SSRPwm0, Freq, self.level[1])
                        i=self.level[1]/10000
                    elif 1 <= self.deltaTRate1 < 3:
                        pi.hardware_PWM(SSRPwm0, Freq, self.level[2])
                        i=self.level[2]/10000
                    elif self.deltaTRate1 < 1:
                        pi.hardware_PWM(SSRPwm0, Freq, self.level[4])
                        i=self.level[4]/10000
                    
                    self.InfoPanel1.setHtml(metrocss.SetInfoPanelText(self.WorkText+delta1+" "+str(i)+"%"))
                #----уходим на выдержку-------------------------
                elif self.MTemp1 >= self.T1:
                    pi.hardware_PWM(SSRPwm0, Freq, self.level[0])
                    self.State1=1
                    self.startTime1=datetime.datetime.now()
                    self.countdown1=datetime.timedelta(minutes=self.t1)
                    delta1=datetime.datetime.now()-self.startTime1
                    delta1=str((self.countdown1-delta1))[:7]
                    self.InfoPanel1.setHtml(metrocss.SetInfoPanelText(self.DelayText+str(self.countdown1)[:7] ) )
            
            elif self.State1==1:
                delta1=datetime.datetime.now()-self.startTime1
                
                #--------обратный отсчет выдержки------------------------
                if delta1.total_seconds()/60 <= self.t1:
                    delta1=str((self.countdown1-delta1))[:7]
                    
                    if self.MTemp1 >=self.T1:
                        pi.hardware_PWM(SSRPwm0, Freq, self.level[0])
                        i=self.level[0]/10000
                    elif (self.T1 - 1) <= self.MTemp1 < self.T1:
                        pi.hardware_PWM(SSRPwm0, Freq, self.level[1])
                        i=self.level[1]/10000
                    elif (self.T1-2) <=self.MTemp1 < (self.T1-1):
                        pi.hardware_PWM(SSRPwm0, Freq, self.level[2])
                        i=self.level[2]/10000
                    elif (self.T1-4) <=self.MTemp1 < (self.T1-2):
                        pi.hardware_PWM(SSRPwm0, Freq, self.level[3])
                        i=self.level[3]/10000
                    elif (self.T1-4) > self.MTemp1:
                        pi.hardware_PWM(SSRPwm0, Freq, self.level[4])
                        i=self.level[4]/10000
                    self.InfoPanel1.setHtml(metrocss.SetInfoPanelText(self.DelayText+delta1+" "+str(i)+"%"))
                
                #--------работа сделана------------------------
                elif delta1.total_seconds()/60 > self.t1: 
                    self.StartButton1.setStyleSheet(metrocss.StartButton_active)
                    self.StopButton1.setStyleSheet(metrocss.StopButton_passive)
                    self.setWorkzonePassive('1')
                    self.Line_65=0
                    self.InfoPanel1.setHtml(metrocss.SetInfoPanelText(self.WaitText))
                    pi.hardware_PWM(SSRPwm0, Freq, 0)
                    self.State1=0
                    self.justStarted1=0
            save_log(file_name_1,self.MTemp1,i,self.State1,self.Fan1_On, self.Heater1)
            
        if self.Line_35==1:
            #---------heaters control------------------------
            if self.State2==0:
                delta2=str(datetime.datetime.now()-self.startTime2)[:7]
               #----проверяем границы температура относительно уставки
                if self.MTemp2 <  (self.T2 - 15):
                    pi.hardware_PWM(SSRPwm1, Freq, self.level[4])
                    p=self.level[4]/10000
                    self.InfoPanel2.setHtml(metrocss.SetInfoPanelText(self.WorkText+delta2+" "+str(p)+"%"))
                
                elif (self.T2 - 15) <= self.MTemp2 < self.T2:
                    if self.deltaTRate2 >= 5:
                       pi.hardware_PWM(SSRPwm1, Freq, self.level[0])
                       p=self.level[0]/10000
                    elif 3 <= self.deltaTRate2 <5:
                        pi.hardware_PWM(SSRPwm1, Freq, self.level[1])
                        p=self.level[1]/10000
                    elif 1 <= self.deltaTRate2 < 3:
                        pi.hardware_PWM(SSRPwm1, Freq, self.level[2])
                        p=self.level[2]/10000
                    elif self.deltaTRate2 < 1:
                        pi.hardware_PWM(SSRPwm1, Freq, self.level[4])
                        p=self.level[4]/10000
                    
                    self.InfoPanel2.setHtml(metrocss.SetInfoPanelText(self.WorkText+delta2+" "+str(p)+"%"))
                #----уходим на выдержку-------------------------
                elif self.MTemp2 >= self.T2:
                    pi.hardware_PWM(SSRPwm1, Freq, self.level[0])
                    self.State2=1
                    self.startTime2=datetime.datetime.now()
                    self.countdown2=datetime.timedelta(minutes=self.t2)
                    delta2=datetime.datetime.now()-self.startTime2
                    delta2=str((self.countdown2-delta2))[:7]
                    self.InfoPanel2.setHtml(metrocss.SetInfoPanelText(self.DelayText+str(self.countdown2)[:7] ) )
            
            elif self.State2==1:
                delta2=datetime.datetime.now()-self.startTime2
                
                #--------обратный отсчет выдержки------------------------
                if delta2.total_seconds()/60 <= self.t2:
                    delta2=str((self.countdown2-delta2))[:7]
                    
                    if self.MTemp2 >=self.T2:
                        pi.hardware_PWM(SSRPwm1, Freq, self.level[0])
                        p=self.level[0]/10000
                    elif (self.T2 - 1) <= self.MTemp2 < self.T2:
                        pi.hardware_PWM(SSRPwm1, Freq, self.level[1])
                        p=self.level[1]/10000
                    elif (self.T2-2) <=self.MTemp2 < (self.T2-1):
                        pi.hardware_PWM(SSRPwm1, Freq, self.level[2])
                        p=self.level[2]/10000
                    elif (self.T2-4) <=self.MTemp2 < (self.T2-2):
                        pi.hardware_PWM(SSRPwm1, Freq, self.level[3])
                        p=self.level[3]/10000
                    elif (self.T2-4) > self.MTemp2:
                        pi.hardware_PWM(SSRPwm1, Freq, self.level[4])
                        p=self.level[4]/10000
                    self.InfoPanel2.setHtml(metrocss.SetInfoPanelText(self.DelayText+delta2+" "+str(p)+"%"))
                
                #--------работа сделана------------------------
                elif delta2.total_seconds()/60 > self.t2: 
                    self.StartButton2.setStyleSheet(metrocss.StartButton_active)
                    self.StopButton2.setStyleSheet(metrocss.StopButton_passive)
                    self.setWorkzonePassive('2')
                    self.Line_35=0
                    self.InfoPanel2.setHtml(metrocss.SetInfoPanelText(self.WaitText))
                    pi.hardware_PWM(SSRPwm1, Freq, 0)
                    self.State2=0
                    self.justStarted2=0
            save_log(file_name_2,self.MTemp2,p,self.State2,self.Fan2_On, self.Heater2)                    


    @pyqtSlot()
    def CleanAir(self): #работа вентиляторов в цикле полимеризации
        if sets['Fan1_Allow'] and self.Line_65 and (round(self.MTemp1) in range(150,200)):
            if self.Fan1Interval > 0:
                self.Fan1Interval -=1
            elif self.Fan1Interval == 0:
                if self.Fan1Time > 0:
                    self.Fan1Time -=1
                    if self.Fan1_On:
                        pass
                    else:
                        self.SetFans(1)
                elif self.Fan1Time == 0:
                    self.Fan1Interval=FI
                    self.Fan1Time=FT
                    if self.Fan1_On:
                        self.SetFans(1)
                    else:
                        pass 
        if sets['Fan2_Allow']==1 and self.Line_35==1 and (round(self.MTemp2) in range(150,200)):
            if self.Fan2Interval > 0:
                self.Fan2Interval -=1
            elif self.Fan2Interval == 0:
                if self.Fan2Time > 0:
                    self.Fan2Time -=1
                    if self.Fan2_On:
                        pass
                    else:
                        self.SetFans(2)
                elif self.Fan2Time == 0:
                    self.Fan2Interval=FI
                    self.Fan2Time=FT
                    if self.Fan2_On:
                        self.SetFans(2)
                    else:
                        pass
        
    def SetFans(self, Line=0):#триггер вентиляторов
        if Line==1:
            if self.Fan1_On==0:
                self.Fan1_On=1
                GPIO.output(Fan1, self.Fan1_On)
                self.Fan1.setIcon(self.iconOn)
            else:
                self.Fan1_On=0
                GPIO.output(Fan1, self.Fan1_On)
                self.Fan1.setIcon(self.iconOff)
            
        elif Line==2:
            if self.Fan2_On==0:
                self.Fan2_On=1
                GPIO.output(Fan2, self.Fan2_On)
                self.Fan2.setIcon(self.iconOn)
            else:
                self.Fan2_On=0
                GPIO.output(Fan2, self.Fan2_On)
                self.Fan2.setIcon(self.iconOff)            
        else:
            sender=self.sender()
            if sender==self.Fan1:
                if self.Fan1_On==0:
                    sender.setIcon(self.iconOn)
                    self.Fan1_On=1
                    GPIO.output(Fan1, self.Fan1_On)
                else:
                    sender.setIcon(self.iconOff)
                    self.Fan1_On=0
                    GPIO.output(Fan1, self.Fan1_On)
            else:
                if self.Fan2_On==0:
                    sender.setIcon(self.iconOn)
                    self.Fan2_On=1
                    GPIO.output(Fan2, self.Fan2_On)
                else:
                    sender.setIcon(self.iconOff)
                    self.Fan2_On=0
                    GPIO.output(Fan2, self.Fan2_On)
    
    def setWorkzonePassive(self,point):#ожидающая рабочая зона
        if point=='1':
            self.Channel1.setStyleSheet(metrocss.Channel_waiting)
            self.Channel2.setStyleSheet(metrocss.Channel_waiting)
            self.Channel3.setStyleSheet(metrocss.Channel_waiting)
        else:
            self.Channel4.setStyleSheet(metrocss.Channel_waiting)
            self.Channel5.setStyleSheet(metrocss.Channel_waiting)
            self.Channel6.setStyleSheet(metrocss.Channel_waiting)

        getattr(self, 'Counter'+str(point)).setStyleSheet(metrocss.Rate_Counter_waiting)
        getattr(self, 'Rate'+str(point)).setStyleSheet(metrocss.Rate_Counter_waiting)
        getattr(self, 'MainTemp'+str(point)).setStyleSheet(metrocss.MainTemp_waiting)
        getattr(self, 'InfoPanel'+str(point)).setStyleSheet(metrocss.InfoPanel_waiting)
        getattr(self, 'SetTemp'+str(point)).setStyleSheet(metrocss.Sets_waiting)
        getattr(self, 'SetDelay'+str(point)).setStyleSheet(metrocss.Sets_waiting)

    def setWorkzoneActive(self,point):#оранжевая рабочая зона
        if point=='1':
            self.Channel1.setStyleSheet(metrocss.Channel_working)
            self.Channel2.setStyleSheet(metrocss.Channel_working)
            self.Channel3.setStyleSheet(metrocss.Channel_working)
        else:
            self.Channel4.setStyleSheet(metrocss.Channel_working)
            self.Channel5.setStyleSheet(metrocss.Channel_working)
            self.Channel6.setStyleSheet(metrocss.Channel_working)

        getattr(self, 'Counter'+str(point)).setStyleSheet(metrocss.Rate_Counter_working)
        getattr(self, 'Rate'+str(point)).setStyleSheet(metrocss.Rate_Counter_working)
        getattr(self, 'MainTemp'+str(point)).setStyleSheet(metrocss.MainTemp_working)
        getattr(self, 'InfoPanel'+str(point)).setStyleSheet(metrocss.InfoPanel_working)
        getattr(self, 'SetTemp'+str(point)).setStyleSheet(metrocss.Sets_working)
        getattr(self, 'SetDelay'+str(point)).setStyleSheet(metrocss.Sets_working)
        
        
        

    @pyqtSlot()
    def StartStop(self):#кнопки старт стоп
        sender=self.sender()
        name=sender.name
        s=len(name)
        point=name[s-1]
        longpressed=sender.longpressed
        if longpressed==0: return
        
        if  name[:5]=='Start':
            if point=='1' and self.Line_65==0:
                self.StartButton1.setStyleSheet(metrocss.StartButton_passive)
                self.StopButton1.setStyleSheet(metrocss.StopButton_active)
                self.setWorkzoneActive(point)
                self.Line_65=1
                sets['Counter1'] +=1
                self.Counter1.setHtml(metrocss.Show_Counter(sets['Counter1']))
                save_settings(sets)
                
            elif point=='2' and self.Line_35==0:
                self.StartButton2.setStyleSheet(metrocss.StartButton_passive)
                self.StopButton2.setStyleSheet(metrocss.StopButton_active)
                self.setWorkzoneActive(point)
                self.Line_35=1
                sets['Counter2'] +=1
                self.Counter2.setHtml(metrocss.Show_Counter(sets['Counter2']))
                save_settings(sets)

        elif name[:4]=='Stop':
            if point=='1' and self.Line_65==1:
                self.StartButton1.setStyleSheet(metrocss.StartButton_active)
                self.StopButton1.setStyleSheet(metrocss.StopButton_passive)
                self.setWorkzonePassive(point)
                self.Line_65=0
                self.InfoPanel1.setHtml(metrocss.SetInfoPanelText(self.WaitText))
                pi.hardware_PWM(SSRPwm0, Freq, 0)
                self.startHeat1=0
                self.startDelay1=0
                self.justStarted1=0
                
                self.Fan1Interval=FI
                self.Fan1Time=FT
                if self.Fan1_On: self.SetFans(1)
                
            elif point=='2' and self.Line_35==1:
                self.StartButton2.setStyleSheet(metrocss.StartButton_active)
                self.StopButton2.setStyleSheet(metrocss.StopButton_passive)
                self.setWorkzonePassive(point)
                self.Line_35=0
                self.InfoPanel2.setHtml(metrocss.SetInfoPanelText(self.WaitText))
                pi.hardware_PWM(SSRPwm1, Freq, 0)
                self.startHeat2=0
                self.startDelay2=0
                self.justStarted2=0
                
                self.Fan2Interval=FI
                self.Fan2Time=FT
                if self.Fan2_On: self.SetFans(2)

    def All_is_Clear(self):#корректное завершение
        spi.close()
        pi.stop()
        GPIO.cleanup()
        self.close()

    def __del__ ( self ):#какая-то системная 
        self.ui = None

    @pyqtSlot()
    def ParamsSet(self):#работа кнопок Параметры
        sender=self.sender()
        
        #------------------heater sensors----------------------
        if sender==self.Over_Heat_Ctrl_1:
            if sets['OH_ctrl_1']==1:
                self.Over_Heat_Ctrl_1.setStyleSheet(metrocss.SetButtons_passive)
                sets['OH_ctrl_1']=0
            else:
                self.Over_Heat_Ctrl_1.setStyleSheet(metrocss.SetButtons_active)
                sets['OH_ctrl_1']=1

        if sender==self.Over_Heat_Ctrl_2:
            if sets['OH_ctrl_2']==1:
                self.Over_Heat_Ctrl_2.setStyleSheet(metrocss.SetButtons_passive)
                sets['OH_ctrl_2']=0
            else:
                self.Over_Heat_Ctrl_2.setStyleSheet(metrocss.SetButtons_active)
                sets['OH_ctrl_2']=1
        
        #---------------main sensors------------------            
        if sender==self.Sensor1_1:
            self.coldStart1=0
            if sets['sensor1_1']==1:
                self.Sensor1_1.setStyleSheet(metrocss.SetButtons_passive)
                sets['sensor1_1']=0
                if sets['sensor1_2']==0:
                    self.Sensor1_2.setStyleSheet(metrocss.SetButtons_active)
                    sets['sensor1_2']=1
            else:
                self.Sensor1_1.setStyleSheet(metrocss.SetButtons_active)
                sets['sensor1_1']=1         

        if sender==self.Sensor1_2:
            self.coldStart1=0
            if sets['sensor1_2']==1:
                self.Sensor1_2.setStyleSheet(metrocss.SetButtons_passive)
                sets['sensor1_2']=0
                if sets['sensor1_1']==0:
                    self.Sensor1_1.setStyleSheet(metrocss.SetButtons_active)
                    sets['sensor1_1']=1
            else:
                self.Sensor1_2.setStyleSheet(metrocss.SetButtons_active)
                sets['sensor1_2']=1
            
        if sender==self.Sensor2_1:
            self.coldStart2=0
            if sets['sensor2_1']==1:
                self.Sensor2_1.setStyleSheet(metrocss.SetButtons_passive)
                sets['sensor2_1']=0
                if sets['sensor2_2']==0:
                    self.Sensor2_2.setStyleSheet(metrocss.SetButtons_active)
                    sets['sensor2_2']=1
            else:
                self.Sensor2_1.setStyleSheet(metrocss.SetButtons_active)
                sets['sensor2_1']=1 

        if sender==self.Sensor2_2:
            self.coldStart2=0
            if sets['sensor2_2']==1:
                self.Sensor2_2.setStyleSheet(metrocss.SetButtons_passive)
                sets['sensor2_2']=0
                if sets['sensor2_1']==0:
                    self.Sensor2_1.setStyleSheet(metrocss.SetButtons_active)
                    sets['sensor2_1']=1
            else:
                self.Sensor2_2.setStyleSheet(metrocss.SetButtons_active)
                sets['sensor2_2']=1
        
        #--------------------Fan Prams------------------------
        if sender==self.Fan1_Allow:
            if sets['Fan1_Allow']==1:
                self.Fan1_Allow.setStyleSheet(metrocss.SetButtons_passive)
                sets['Fan1_Allow']=0
                if self.Line_65:
                    self.Fan1Interval=FI
                    self.Fan1Time=FT
                    if self.Fan1_On: self.SetFans(1)
            else:
                self.Fan1_Allow.setStyleSheet(metrocss.SetButtons_active)
                sets['Fan1_Allow']=1

        if sender==self.Fan2_Allow:
            if sets['Fan2_Allow']==1:
                self.Fan2_Allow.setStyleSheet(metrocss.SetButtons_passive)
                sets['Fan2_Allow']=0
                if self.Line_35:
                    self.Fan2Interval=FI
                    self.Fan2Time=FT
                    if self.Fan2_On: self.SetFans(2)
            else:
                self.Fan2_Allow.setStyleSheet(metrocss.SetButtons_active)
                sets['Fan2_Allow']=1

        save_settings(sets)
        
    def set_user_data(self, T,t):#ловля сигнала модального окна ввода настроек температуры и выдержки
        if self.point==1:
            self.SetTemp1.setHtml(metrocss.settemp(T))
            self.SetDelay1.setHtml(metrocss.setdelay(t))
            self.T1=T
            self.t1=t
        if self.point==2:
            self.SetTemp2.setHtml(metrocss.settemp(T))
            self.SetDelay2.setHtml(metrocss.setdelay(t))
            self.T2=T
            self.t2=t

    @pyqtSlot()
    def SelectUserProg(self):#отработка нажатия кнопки пользовательская программа
        sender=self.sender()
        name = sender.objectName()
        point=name[1]
        self.point=int(point)        
        if self.point==1 and self.Line_65 == 0:
            self.clear_buttons(self.point)
            sender.setStyleSheet(metrocss.prog_active)
            self.AskWindow=UserData(self.user_data_signal, self)
            self.AskWindow.show()
            self.AskWindow.move(313, 195)

        if self.point==2 and self.Line_35 == 0:
            self.clear_buttons(self.point)
            sender.setStyleSheet(metrocss.prog_active)
            self.AskWindow=UserData(self.user_data_signal, self)
            self.AskWindow.show()
            self.AskWindow.move(313, 195)

    @pyqtSlot()
    def SelectProg(self):#кнопки выбора программ
        sender = self.sender()
        name = sender.objectName()
        if name[1]=='1':
            if self.Line_65 == 0:
                prog=int(name[3])
                line=1
                self.set_prog(prog,line)
            else:
                pass

        if name[1]=='2':
            if self.Line_35 == 0:
                prog=int(name[3])
                line=2
                self.set_prog(prog,line)
            else:
                pass

    @pyqtSlot()
    def set_hotkeys(self):#горячие клавиши для завершения и сворачивания
        # свернуть окно по CTRL+Hself.SetTemp2.setStyleSheet
        self.minact = QAction(self)
        self.minact.setShortcut("CTRL+H")       
        self.minact.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(self.minact)
        QObject.connect(self.minact, SIGNAL("triggered()"), lambda : self.setWindowState(Qt.WindowMinimized))
        # Exit CTRL+Q
        self.actq = QAction(self)
        self.actq.setShortcut("CTRL+Q")       
        self.actq.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(self.actq)
        QObject.connect(self.actq, SIGNAL("triggered()"), self.RunAway)
        # Exit CTRL+Й
        self.actqr = QAction(self)
        self.actqr.setShortcut("CTRL+Й")       
        self.actqr.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(self.actqr)
        QObject.connect(self.actqr, SIGNAL("triggered()"), self.RunAway)

    @pyqtSlot()    
    def set_adc(self):#запуск ацп в потоке
        self.tempthread=TempThread(self.temp_signal)
        self.temp_signal.connect(self.got_worker_msg, QtCore.Qt.QueuedConnection)
        self.tempthreadcontrol(1)
        
    def closeEvent(self, event):#переопределяем закрытие окна
         self.RunAway()

    def ShowResults(self, Tin):#вывод температуры на рабочую зону
        #-------------рассчитываем температуры по разрешенным датчикам---------
        if sets['sensor1_1']==1 and sets['sensor1_2']==1:
            self.MTemp1=(float(Tin[1])+float(Tin[2]))/2
            self.MainTemp1.setHtml(metrocss.Show_Main_Temp ("%.1f" %self.MTemp1 ))
            self.Channel1.setHtml(metrocss.Show_temp(Tin[1]))
            self.Channel2.setHtml(metrocss.Show_temp(Tin[2]))
        elif sets['sensor1_1']==0 and sets['sensor1_2']==1:
            self.MTemp1=float(Tin[2])
            self.MainTemp1.setHtml(metrocss.Show_Main_Temp ("%.1f" %self.MTemp1 ))
            self.Channel1.setHtml(metrocss.Show_temp("NaN"))
            self.Channel2.setHtml(metrocss.Show_temp(Tin[2]))
        elif sets['sensor1_1']==1 and sets['sensor1_2']==0:
            self.MTemp1=float(Tin[1])
            self.MainTemp1.setHtml(metrocss.Show_Main_Temp ("%.1f" %self.MTemp1 ))
            self.Channel1.setHtml(metrocss.Show_temp(Tin[1]))
            self.Channel2.setHtml(metrocss.Show_temp("NaN"))
       
       
        self.Channel3.setHtml(metrocss.Show_temp(Tin[3]))#Тэны всегда!
        self.Channel6.setHtml(metrocss.Show_temp(Tin[6])) 
        self.Heater1=Tin[3]
        self.Heater2=Tin[6]
        
        if sets['sensor2_1']==1 and sets['sensor2_2']==1:
            self.MTemp2=(float(Tin[4])+float(Tin[5]))/2
            self.MainTemp2.setHtml(metrocss.Show_Main_Temp ("%.1f" %self.MTemp2 ))
            self.Channel4.setHtml(metrocss.Show_temp(Tin[4]))
            self.Channel5.setHtml(metrocss.Show_temp(Tin[5]))
        elif sets['sensor2_1']==0 and sets['sensor2_2']==1:
            self.MTemp2=float(Tin[5])
            self.MainTemp2.setHtml(metrocss.Show_Main_Temp ("%.1f" %self.MTemp2 ))
            self.Channel4.setHtml(metrocss.Show_temp("NaN"))
            self.Channel5.setHtml(metrocss.Show_temp(Tin[5]))
        elif sets['sensor2_1']==1 and sets['sensor2_2']==0:
            self.MTemp2=float(Tin[4])
            self.MainTemp2.setHtml(metrocss.Show_Main_Temp ("%.1f" %self.MTemp2 ))
            self.Channel4.setHtml(metrocss.Show_temp(Tin[4]))
            self.Channel5.setHtml(metrocss.Show_temp("NaN"))
        
        #-------------работаем со стеком значений температур---------
        if self.coldStart==0:
            for i in range(60):
                self.TRate1.append(self.MTemp1)
                self.TRate2.append(self.MTemp2)
                
            self.coldStart0=1
        else:
            self.TRate1.append(self.MTemp1)
            self.TRate2.append(self.MTemp2)
            
        if self.coldStart1==0:
            self.TRate1=[]
            for i in range(60):
                self.TRate1.append(self.MTemp1)
            self.coldStart1=1

    
        if self.coldStart2==0: 
            self.TRate2=[]      
            for i in range(60):   
                self.TRate2.append(self.MTemp2)
            self.coldStart2=1
        
        #-------------вычисляем скорость изменения температуры по стеку---------
        self.deltaTRate1=self.MTemp1-self.TRate1.pop(0)
        self.deltaTRate2=self.MTemp2-self.TRate2.pop(0)
        
        self.Rate1.setHtml(metrocss.Show_Rate(self.deltaTRate1))
        self.Rate2.setHtml(metrocss.Show_Rate(self.deltaTRate2))
        
        #-----вызываем обработку состояния вкл/выкл линии по полученным данным----
        self.DoMainWork()
        
        

    def ConvertResults(self, Va):#преобразование вольты в градусы
        Ch=1
        p='Channel'
        Tout={}
        while Ch <=6:
            p1=p+str(Ch)
            realq=sets[p1][0]*Va[Ch]**3+sets[p1][1]*Va[Ch]**2+sets[p1][2]*Va[Ch]-sets[p1][3];
            T="%.1f" % realq ##+ DEGREE            
            Tout[Ch]=T
            Ch +=1
        return Tout

    def got_worker_msg(self,Va):#ловля сигнала от АЦП
        self.ShowResults(self.ConvertResults(Va))

    def RunAway(self):#кусок корректного закрытия
        self.tempthread.stop()
        self.All_is_Clear()

    def tempthreadcontrol(self, command):#запуск/остановка потока
        if command==1:
            self.tempthread.isRun=True
            self.tempthread.start()
        elif command==0:
            self.tempthread.stop()
                         
    def clear_buttons(self, line):#установка кнопок в серое состояние при смене программы
        if line==1:
            self.p1_1.setStyleSheet(metrocss.prog_passive)
            self.p1_2.setStyleSheet(metrocss.prog_passive)
            self.p1_3.setStyleSheet(metrocss.prog_passive)                
            self.p1_4.setStyleSheet(metrocss.prog_passive)
        if line==2:
            self.p2_1.setStyleSheet(metrocss.prog_passive)
            self.p2_2.setStyleSheet(metrocss.prog_passive)
            self.p2_3.setStyleSheet(metrocss.prog_passive)                
            self.p2_4.setStyleSheet(metrocss.prog_passive)
               

    def set_prog(self, prog, line):#подпрограммы кнопок переключения программы
        if line == 1:
            self.clear_buttons(1)
            if prog==1:
                self.p1_1.setStyleSheet(metrocss.prog_active)
                self.SetTemp1.setHtml(metrocss.settemp(180))
                self.SetDelay1.setHtml(metrocss.setdelay(15))
                self.T1=180
                self.t1=15
                sets['start_prog1']=1
            if prog==2:
                self.p1_2.setStyleSheet(metrocss.prog_active)
                self.SetTemp1.setHtml(metrocss.settemp(190))
                self.SetDelay1.setHtml(metrocss.setdelay(10))
                self.T1=190
                self.t1=10
                sets['start_prog1']=2
            if prog==3:
                self.p1_3.setStyleSheet(metrocss.prog_active)
                self.SetTemp1.setHtml(metrocss.settemp(200))
                self.SetDelay1.setHtml(metrocss.setdelay(10))
                self.T1=200
                self.t1=10
                sets['start_prog1']=3

        if line == 2:
            self.clear_buttons(2)
            if prog==1:
                self.p2_1.setStyleSheet(metrocss.prog_active)
                self.SetTemp2.setHtml(metrocss.settemp(180))
                self.SetDelay2.setHtml(metrocss.setdelay(15))
                self.T2=180
                self.t2=15
                sets['start_prog2']=1
            if prog==2:
                self.p2_2.setStyleSheet(metrocss.prog_active)
                self.SetTemp2.setHtml(metrocss.settemp(190))
                self.SetDelay2.setHtml(metrocss.setdelay(10))
                self.T2=190
                self.t2=10
                sets['start_prog2']=2
            if prog==3:
                self.p2_3.setStyleSheet(metrocss.prog_active)
                self.SetTemp2.setHtml(metrocss.settemp(200))
                self.SetDelay2.setHtml(metrocss.setdelay(10))
                self.T2=200
                self.t2=10
                sets['start_prog2']=3

        save_settings(sets)                

    @pyqtSlot()
    def call_ini_set(self):#установка первоначального состояния из файла настроек
        #---------initial default prog set-----------
        if sets['start_prog1']==1:
            self.set_prog(1,1)
        if sets['start_prog1']==2:
            self.set_prog(2,1)
        if sets['start_prog1']==3:
            self.set_prog(3,1)

        if sets['start_prog2']==1:
            self.set_prog(1,2)
        if sets['start_prog2']==2:
            self.set_prog(2,2)
        if sets['start_prog2']==3:
            self.set_prog(3,2)
            
        #---------heaters set--------------------
        if sets['OH_ctrl_1']==1:
            self.Over_Heat_Ctrl_1.setStyleSheet(metrocss.SetButtons_active)
            
        if sets['OH_ctrl_2']==1:
            self.Over_Heat_Ctrl_2.setStyleSheet(metrocss.SetButtons_active)

        if sets['sensor1_1']==1:
            self.Sensor1_1.setStyleSheet(metrocss.SetButtons_active)

        if sets['sensor1_2']==1:
            self.Sensor1_2.setStyleSheet(metrocss.SetButtons_active)

        if sets['sensor2_1']==1:
            self.Sensor2_1.setStyleSheet(metrocss.SetButtons_active)

        if sets['sensor2_2']==1:
            self.Sensor2_2.setStyleSheet(metrocss.SetButtons_active)

        #---------fans set--------------------
        if sets['Fan1_Allow']==1:
            self.Fan1_Allow.setStyleSheet(metrocss.SetButtons_active)

        if sets['Fan2_Allow']==1:
            self.Fan2_Allow.setStyleSheet(metrocss.SetButtons_active)

        #---------counter set--------------------
        self.Counter1.setHtml(metrocss.Show_Counter(sets['Counter1']))
        self.Counter2.setHtml(metrocss.Show_Counter(sets['Counter2']))    
        
        #---------Infopanel set--------------------
        self.InfoPanel1.setHtml(metrocss.SetInfoPanelText(self.WaitText))
        self.InfoPanel2.setHtml(metrocss.SetInfoPanelText(self.WaitText))
    

    def SetVirtualButtons(self):#рисуем кнопки с длинным нажатием
        
        self.StartVirt1 = LongButton(self.centralwidget, name="StartVirt1")
        self.StartVirt1.setGeometry(QtCore.QRect(15, 75, 134, 139))
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.StartVirt1.sizePolicy().hasHeightForWidth())
        self.StartVirt1.setSizePolicy(sizePolicy)
        self.StartVirt1.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.StartVirt1.setFocusPolicy(QtCore.Qt.NoFocus)
        self.StartVirt1.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.StartVirt1.setAcceptDrops(False)
        self.StartVirt1.setStyleSheet(_fromUtf8("border-style: outset;background-color: none;"))
        
        
        self.StopVirt1 = LongButton(self.centralwidget, name="StopVirt1")
        self.StopVirt1.setGeometry(QtCore.QRect(15, 227, 134, 139))
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.StopVirt1.sizePolicy().hasHeightForWidth())
        self.StopVirt1.setSizePolicy(sizePolicy)
        self.StopVirt1.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.StopVirt1.setFocusPolicy(QtCore.Qt.NoFocus)
        self.StopVirt1.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.StopVirt1.setAcceptDrops(False)
        self.StopVirt1.setStyleSheet(_fromUtf8("border-style: outset;background-color: none;"))
        
        self.StartVirt2 = LongButton(self.centralwidget, name="StartVirt2")
        self.StartVirt2.setGeometry(QtCore.QRect(651, 75, 134, 139))
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.StartVirt2.sizePolicy().hasHeightForWidth())
        self.StartVirt2.setSizePolicy(sizePolicy)
        self.StartVirt2.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.StartVirt2.setFocusPolicy(QtCore.Qt.NoFocus)
        self.StartVirt2.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.StartVirt2.setAcceptDrops(False)
        self.StartVirt2.setStyleSheet(_fromUtf8("border-style: outset;background-color: none;"))
        
        self.StopVirt2 = LongButton(self.centralwidget, name="StopVirt2")
        self.StopVirt2.setGeometry(QtCore.QRect(651, 227, 134, 139))
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.StopVirt2.sizePolicy().hasHeightForWidth())
        self.StopVirt2.setSizePolicy(sizePolicy)
        self.StopVirt2.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.StopVirt2.setFocusPolicy(QtCore.Qt.NoFocus)
        self.StopVirt2.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.StopVirt2.setAcceptDrops(False)
        self.StopVirt2.setStyleSheet(_fromUtf8("border-style: outset;background-color: none;"))
        
        

#------------globals func-----------------------------
def save_log(file_name,temp,power,state,fan_state,heater):
    t=time.time()
    if file_name != '':
        file=open("logs/"+file_name, "a" )
        file.write(str(t)+','+str(temp)+','+str(power)+','+str(state)+','+str(fan_state)+','+str(heater)+'\n')
        file.close()

def read_settings():
    global sets
    try:
        with open('settings.txt', 'rb') as csvfile:
            spamreader = csv.reader(csvfile, delimiter='=', quotechar='|')
            for row in spamreader:
                k, v = row
                try:
                    sets[k] = int(v)
                except ValueError:
                    line=v
                    line=line.replace('[','')
                    line=line.replace(']','')
                    sets[k] = string.split(line,",")
                    s=len(sets[k])
                    i=0
                    while i<s:                
                        x = sets[k][i]
                        x=float(x)
                        sets[k][i]=x
                        i+=1
    except IOError:
        sets=metrocss.a
        save_settings(sets)   
        

def save_settings(sets):
    with open('settings.txt', 'wb') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter='=',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for key, val in sets.items():
            spamwriter.writerow([key, val])

def call_board_ini():

    GPIO.setup(Mux, GPIO.OUT)
    GPIO.output(Mux,(0,0,0))

    spi.open(0,0)
    spi.max_speed_hz = 40000

    GPIO.setup([Fan1, Fan2, OEBuff, SSRPwm0, SSRPwm1], GPIO.OUT)
    GPIO.output([Fan1, Fan2, OEBuff, SSRPwm0, SSRPwm0], 0)

    pi.set_PWM_dutycycle(SSRPwm0, 0) # без этого не отрабатывает первый запуск
    pi.set_PWM_dutycycle(SSRPwm1, 0) # после выхода и нового запуска кода


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

