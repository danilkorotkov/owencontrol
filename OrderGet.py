# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
from PyQt4 import QtCore, QtGui, uic
from PyQt4.Qt import Qt
import requests
import os
os.environ["DISPLAY"] = ":0" #remote a

MainInterfaceWindow = "order_w.ui"
Ui_MainWindow, QtBaseClass = uic.loadUiType(MainInterfaceWindow)


class PostThread(QtCore.QThread):
    def __init__(self, URL, timeout=20, payload={}, parent=None):
        super(PostThread, self).__init__(parent)
        self.URL = URL
        self.payload = payload
        self.timeout = timeout

    def run(self):
        self.error = ''
        try:
            self.response = requests.post(url=self.URL, timeout=self.timeout, params=self.payload)
            #print('Answer', self.response.status_code, self.response.text)

        except requests.exceptions.RequestException as e:
            print('Ошибка  1', e)
            self.error = str(e)
        except ValueError as e:
            print('Ошибка 2', e)
            self.error = str(e)

    def stop(self):
        pass

class OrderWindow(QtGui.QMainWindow, Ui_MainWindow):
    orders = []
    importURL = 'http://192.168.1.144/HTTP_POST/hs/Comagic/v2/orders'
    exportURL = 'http://192.168.1.144/HTTP_POST/hs/Comagic/v2/updateorder'
    timeout = 20
    readyToNext = True

    def __init__(self, parent=None):
        super(OrderWindow, self).__init__(parent)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.listWidget.verticalScrollBar().setStyleSheet(_fromUtf8(
            "QScrollBar:vertical {width: 40px; background: rgb(194, 194, 194); margin: 0px;}\n"
            "QScrollBar::handle:vertical {min-height: 40px;}\n"
            "QScrollBar::sub-line:vertical {subcontrol-position: top; subcontrol-origin: margin; height: 70px; }\n"
            "QScrollBar::add-line:vertical {subcontrol-position: bottom; subcontrol-origin: margin; height: 70px; }\n"
            "QScrollBar::down-arrow:vertical, QScrollBar::up-arrow:vertical {background: NONE;}\n"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {background: NONE;}"))

        self.importResponse = PostThread(URL=self.importURL, timeout=self.timeout)
        self.exportResponse = PostThread(URL=self.exportURL, timeout=self.timeout)

        self.ExitButton.pressed.connect(self.exit)
        self.listWidget.itemDoubleClicked.connect(self.OrderClick)
        self.RefButton.pressed.connect(self.refreshInThread)

        self.importResponse.finished.connect(self.importFunc)  # обработка запроса заказов
        self.exportResponse.finished.connect(self.exportFunc)  # обработка изменения статуса

        self.refreshInThread() # получаем список заказов

    def refreshInThread(self): # работа с таблчной частью
        # чистим таблицу
        self.listWidget.clear()
        self.update()
        self.orders = []
        self.statusBar.showMessage('Ищем заказы...')
        # запускаем запрос в потоке
        self.importResponse.start()

    def importFunc(self): # обработка сигнала получения списка заказов
        if self.importResponse.error != '':
            self.statusBar.showMessage(self.importResponse.error)
            self.orders.append(['Ошибка\nобмена', 0])
            self.fill_orders()
            return

        datajson = self.importResponse.response.json()

        OrdersList = datajson['orders']

        for i in range(len(OrdersList)):
            self.orders.append([OrdersList[i]['order'],
                                OrdersList[i]['status'],
                                OrdersList[i]['GUID'],
                                OrdersList[i]['status']])

        self.statusBar.showMessage('Получение прошло успешно')
        self.fill_orders()

    def exportFunc(self): # обработка сигнала отправки изменения статуса заказа
        self.readyToNext = True
        if self.exportResponse.error != '':
            self.statusBar.showMessage(self.exportResponse.error)
            return
        self.ChangeStatus(self.rowPointer)
        self.statusBar.showMessage('Изменения отправлены')

    def __del__(self):
        self.ui = None

    def exit(self):
        self.close()

    def fill_orders(self):
        """
        заполняем листвиджет списком заказов в работе
        с цветовыми маркерами
        """

        for i in range(len(self.orders)):
            self.listWidget.addItem(self.orders[i][0])
            item = self.listWidget.item(i)
            if self.orders[i][1] == 0:
                item.setBackground(QtGui.QColor("red"))
            elif self.orders[i][1] == 1:
                item.setBackground(QtGui.QColor("orange"))

    def ChangeStatus(self, i):
        '''
        смена статуса заказа с отрисовкой в таблице
        '''
        item = self.listWidget.item(i)
        if self.orders[i][1] == 0: # если в работе, то готов
            item.setBackground(QtGui.QColor("green"))
            self.orders[i][1] = 2
        elif self.orders[i][1] == 1: # если в производстве, то готов
            item.setBackground(QtGui.QColor("green"))
            self.orders[i][1] = 2
        elif self.orders[i][1] == 2: # если готов, то возвращаем предыдущий
            self.orders[i][1] = self.orders[i][3]
            if self.orders[i][1] == 0:
                item.setBackground(QtGui.QColor("red"))
            elif self.orders[i][1] == 1:
                item.setBackground(QtGui.QColor("orange"))

    def OrderClick(self):
        """
        обработка даблклика на заказе
        """
        if self.readyToNext == False:
            message = self.statusBar.currentMessage()
            self.statusBar.showMessage(message + 'Дождитесь окончания отправки')
            return

        i = self.listWidget.currentRow()
        number = self.orders[i][0].replace("\n", " ")[:11]

        self.statusBar.showMessage('Отправляем изменения заказа ' + number + '...')

        status = self.orders[i][1]

        payload = {'GUID': self.orders[i][2], 'status': self.orders[i][3]}
        #print('payload= ', payload)

        self.rowPointer = i
        self.readyToNext = False
        self.exportResponse.payload = payload
        self.exportResponse.start()

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

if __name__ == "__main__":
    # create application
    app = QApplication(sys.argv)
    app.setApplicationName('order check')

    # create widget
    window = OrderWindow()
    window.show()
    app.exec_()
    app.deleteLater()
    sys.exit()