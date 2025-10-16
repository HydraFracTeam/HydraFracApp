# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'design.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QLabel, QMainWindow,
    QMenuBar, QPushButton, QSizePolicy, QStatusBar,
    QWidget)

class Ui_mainWindow(object):
    def setupUi(self, mainWindow):
        if not mainWindow.objectName():
            mainWindow.setObjectName(u"mainWindow")
        mainWindow.resize(1211, 753)
        self.centralwidget = QWidget(mainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.load_template_button = QPushButton(self.centralwidget)
        self.load_template_button.setObjectName(u"load_template_button")
        self.load_template_button.setGeometry(QRect(20, 20, 251, 26))
        self.k_label = QLabel(self.centralwidget)
        self.k_label.setObjectName(u"k_label")
        self.k_label.setGeometry(QRect(30, 100, 181, 18))
        self.k_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.params_label = QLabel(self.centralwidget)
        self.params_label.setObjectName(u"params_label")
        self.params_label.setGeometry(QRect(90, 60, 111, 20))
        self.params_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.h_label = QLabel(self.centralwidget)
        self.h_label.setObjectName(u"h_label")
        self.h_label.setGeometry(QRect(30, 150, 181, 18))
        self.h_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.phi_label = QLabel(self.centralwidget)
        self.phi_label.setObjectName(u"phi_label")
        self.phi_label.setGeometry(QRect(30, 200, 181, 18))
        self.phi_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.k_doubleSpinBox = QDoubleSpinBox(self.centralwidget)
        self.k_doubleSpinBox.setObjectName(u"k_doubleSpinBox")
        self.k_doubleSpinBox.setGeometry(QRect(220, 90, 71, 27))
        self.h_doubleSpinBox = QDoubleSpinBox(self.centralwidget)
        self.h_doubleSpinBox.setObjectName(u"h_doubleSpinBox")
        self.h_doubleSpinBox.setGeometry(QRect(220, 140, 71, 27))
        self.phi_doubleSpinBox = QDoubleSpinBox(self.centralwidget)
        self.phi_doubleSpinBox.setObjectName(u"phi_doubleSpinBox")
        self.phi_doubleSpinBox.setGeometry(QRect(220, 190, 71, 27))
        self.phi_doubleSpinBox.setMaximum(1.000000000000000)
        mainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(mainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1211, 23))
        mainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(mainWindow)
        self.statusbar.setObjectName(u"statusbar")
        mainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(mainWindow)

        QMetaObject.connectSlotsByName(mainWindow)
    # setupUi

    def retranslateUi(self, mainWindow):
        mainWindow.setWindowTitle(QCoreApplication.translate("mainWindow", u"MainWindow", None))
        self.load_template_button.setText(QCoreApplication.translate("mainWindow", u"\u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c .csv \u0448\u0430\u0431\u043b\u043e\u043d", None))
        self.k_label.setText(QCoreApplication.translate("mainWindow", u"\u041f\u0440\u043e\u043d\u0438\u0446\u0430\u0435\u043c\u043e\u0441\u0442\u044c k, \u043c\u0414", None))
        self.params_label.setText(QCoreApplication.translate("mainWindow", u"\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b", None))
        self.h_label.setText(QCoreApplication.translate("mainWindow", u"\u0422\u043e\u043b\u0449\u0438\u043d\u0430 \u043f\u043b\u0430\u0441\u0442\u0430 h, \u043c", None))
        self.phi_label.setText(QCoreApplication.translate("mainWindow", u"\u041f\u043e\u0440\u0438\u0441\u0442\u043e\u0441\u0442\u044c phi", None))
    # retranslateUi

