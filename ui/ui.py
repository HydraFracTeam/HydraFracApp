# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_ui.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QMainWindow,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QStatusBar, QTabWidget, QTableView, QTextEdit,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.setWindowModality(Qt.WindowModality.NonModal)
        MainWindow.resize(1920, 1080)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_5 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.left_panel = QGroupBox(self.centralwidget)
        self.left_panel.setObjectName(u"left_panel")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.left_panel.sizePolicy().hasHeightForWidth())
        self.left_panel.setSizePolicy(sizePolicy1)
        self.left_panel.setMinimumSize(QSize(0, 0))
        self.verticalLayout_3 = QVBoxLayout(self.left_panel)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.scrollArea = QScrollArea(self.left_panel)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setMinimumSize(QSize(520, 0))
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 504, 1102))
        self.verticalLayout_14 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.groupBox_3 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_11 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.load_file_button = QPushButton(self.groupBox_3)
        self.load_file_button.setObjectName(u"load_file_button")

        self.horizontalLayout_2.addWidget(self.load_file_button)

        self.load_file_label = QLabel(self.groupBox_3)
        self.load_file_label.setObjectName(u"load_file_label")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.load_file_label.sizePolicy().hasHeightForWidth())
        self.load_file_label.setSizePolicy(sizePolicy2)
        self.load_file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_2.addWidget(self.load_file_label)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.insert_data_from_buffer_button = QPushButton(self.groupBox_3)
        self.insert_data_from_buffer_button.setObjectName(u"insert_data_from_buffer_button")

        self.horizontalLayout_3.addWidget(self.insert_data_from_buffer_button)

        self.reset_data_button = QPushButton(self.groupBox_3)
        self.reset_data_button.setObjectName(u"reset_data_button")

        self.horizontalLayout_3.addWidget(self.reset_data_button)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)


        self.verticalLayout_11.addLayout(self.verticalLayout_2)

        self.horizontalLayout_27 = QHBoxLayout()
        self.horizontalLayout_27.setObjectName(u"horizontalLayout_27")
        self.export_session_btn = QPushButton(self.groupBox_3)
        self.export_session_btn.setObjectName(u"export_session_btn")

        self.horizontalLayout_27.addWidget(self.export_session_btn)

        self.import_session_btn = QPushButton(self.groupBox_3)
        self.import_session_btn.setObjectName(u"import_session_btn")

        self.horizontalLayout_27.addWidget(self.import_session_btn)


        self.verticalLayout_11.addLayout(self.horizontalLayout_27)


        self.verticalLayout_14.addWidget(self.groupBox_3)

        self.static_params_group = QGroupBox(self.scrollAreaWidgetContents)
        self.static_params_group.setObjectName(u"static_params_group")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.static_params_group.sizePolicy().hasHeightForWidth())
        self.static_params_group.setSizePolicy(sizePolicy3)
        self.static_params_group.setMinimumSize(QSize(0, 0))
        self.verticalLayout_13 = QVBoxLayout(self.static_params_group)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.horizontalLayout_17 = QHBoxLayout()
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.horizontalLayout_14 = QHBoxLayout()
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.well_length_label = QLabel(self.static_params_group)
        self.well_length_label.setObjectName(u"well_length_label")

        self.horizontalLayout_14.addWidget(self.well_length_label)

        self.well_length_spinbox = QDoubleSpinBox(self.static_params_group)
        self.well_length_spinbox.setObjectName(u"well_length_spinbox")
        self.well_length_spinbox.setEnabled(False)
        self.well_length_spinbox.setReadOnly(False)
        self.well_length_spinbox.setDecimals(2)
        self.well_length_spinbox.setMaximum(10000.000000000000000)
        self.well_length_spinbox.setValue(2500.000000000000000)

        self.horizontalLayout_14.addWidget(self.well_length_spinbox)


        self.horizontalLayout_17.addLayout(self.horizontalLayout_14)

        self.horizontalLayout_13 = QHBoxLayout()
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.well_height_label = QLabel(self.static_params_group)
        self.well_height_label.setObjectName(u"well_height_label")

        self.horizontalLayout_13.addWidget(self.well_height_label)

        self.well_height_spinBox = QDoubleSpinBox(self.static_params_group)
        self.well_height_spinBox.setObjectName(u"well_height_spinBox")
        self.well_height_spinBox.setEnabled(False)
        self.well_height_spinBox.setReadOnly(False)
        self.well_height_spinBox.setDecimals(2)
        self.well_height_spinBox.setMaximum(10000.000000000000000)
        self.well_height_spinBox.setValue(10.000000000000000)

        self.horizontalLayout_13.addWidget(self.well_height_spinBox)


        self.horizontalLayout_17.addLayout(self.horizontalLayout_13)


        self.verticalLayout_13.addLayout(self.horizontalLayout_17)

        self.horizontalLayout_18 = QHBoxLayout()
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.viscosity_label = QLabel(self.static_params_group)
        self.viscosity_label.setObjectName(u"viscosity_label")

        self.horizontalLayout_10.addWidget(self.viscosity_label)

        self.viscosity_spinBox = QDoubleSpinBox(self.static_params_group)
        self.viscosity_spinBox.setObjectName(u"viscosity_spinBox")
        self.viscosity_spinBox.setEnabled(False)
        self.viscosity_spinBox.setReadOnly(False)
        self.viscosity_spinBox.setDecimals(3)
        self.viscosity_spinBox.setMaximum(10.000000000000000)
        self.viscosity_spinBox.setSingleStep(0.100000000000000)
        self.viscosity_spinBox.setValue(1.000000000000000)

        self.horizontalLayout_10.addWidget(self.viscosity_spinBox)


        self.horizontalLayout_18.addLayout(self.horizontalLayout_10)

        self.horizontalLayout_11 = QHBoxLayout()
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.volume_coef_label = QLabel(self.static_params_group)
        self.volume_coef_label.setObjectName(u"volume_coef_label")

        self.horizontalLayout_11.addWidget(self.volume_coef_label)

        self.volume_coef_spinBox = QDoubleSpinBox(self.static_params_group)
        self.volume_coef_spinBox.setObjectName(u"volume_coef_spinBox")
        self.volume_coef_spinBox.setEnabled(False)
        self.volume_coef_spinBox.setReadOnly(False)
        self.volume_coef_spinBox.setDecimals(3)
        self.volume_coef_spinBox.setMaximum(10.000000000000000)
        self.volume_coef_spinBox.setSingleStep(0.100000000000000)
        self.volume_coef_spinBox.setValue(1.000000000000000)

        self.horizontalLayout_11.addWidget(self.volume_coef_spinBox)


        self.horizontalLayout_18.addLayout(self.horizontalLayout_11)


        self.verticalLayout_13.addLayout(self.horizontalLayout_18)

        self.horizontalLayout_16 = QHBoxLayout()
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.porosity_label = QLabel(self.static_params_group)
        self.porosity_label.setObjectName(u"porosity_label")

        self.horizontalLayout_9.addWidget(self.porosity_label)

        self.porosity_spinBox = QDoubleSpinBox(self.static_params_group)
        self.porosity_spinBox.setObjectName(u"porosity_spinBox")
        self.porosity_spinBox.setEnabled(False)
        self.porosity_spinBox.setReadOnly(False)
        self.porosity_spinBox.setDecimals(3)
        self.porosity_spinBox.setMaximum(10.000000000000000)
        self.porosity_spinBox.setSingleStep(0.100000000000000)
        self.porosity_spinBox.setValue(0.200000000000000)

        self.horizontalLayout_9.addWidget(self.porosity_spinBox)


        self.horizontalLayout_16.addLayout(self.horizontalLayout_9)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.frac_amount_label = QLabel(self.static_params_group)
        self.frac_amount_label.setObjectName(u"frac_amount_label")

        self.horizontalLayout_8.addWidget(self.frac_amount_label)

        self.frac_amount_spinBox = QSpinBox(self.static_params_group)
        self.frac_amount_spinBox.setObjectName(u"frac_amount_spinBox")
        self.frac_amount_spinBox.setEnabled(False)
        self.frac_amount_spinBox.setReadOnly(False)
        self.frac_amount_spinBox.setMinimum(2)
        self.frac_amount_spinBox.setMaximum(1000)
        self.frac_amount_spinBox.setValue(10)

        self.horizontalLayout_8.addWidget(self.frac_amount_spinBox)


        self.horizontalLayout_16.addLayout(self.horizontalLayout_8)


        self.verticalLayout_13.addLayout(self.horizontalLayout_16)

        self.horizontalLayout_12 = QHBoxLayout()
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.compressibility_label = QLabel(self.static_params_group)
        self.compressibility_label.setObjectName(u"compressibility_label")

        self.horizontalLayout_12.addWidget(self.compressibility_label)

        self.compressibility_spinBox = QDoubleSpinBox(self.static_params_group)
        self.compressibility_spinBox.setObjectName(u"compressibility_spinBox")
        self.compressibility_spinBox.setEnabled(False)
        self.compressibility_spinBox.setReadOnly(False)
        self.compressibility_spinBox.setDecimals(6)
        self.compressibility_spinBox.setMaximum(1000.000000000000000)
        self.compressibility_spinBox.setValue(0.000040000000000)

        self.horizontalLayout_12.addWidget(self.compressibility_spinBox)


        self.verticalLayout_13.addLayout(self.horizontalLayout_12)

        self.horizontalLayout_25 = QHBoxLayout()
        self.horizontalLayout_25.setObjectName(u"horizontalLayout_25")
        self.reservoir_pressure_label = QLabel(self.static_params_group)
        self.reservoir_pressure_label.setObjectName(u"reservoir_pressure_label")

        self.horizontalLayout_25.addWidget(self.reservoir_pressure_label)

        self.reservoir_pressure_spinbox = QDoubleSpinBox(self.static_params_group)
        self.reservoir_pressure_spinbox.setObjectName(u"reservoir_pressure_spinbox")
        self.reservoir_pressure_spinbox.setEnabled(False)
        self.reservoir_pressure_spinbox.setReadOnly(False)
        self.reservoir_pressure_spinbox.setMaximum(100000.000000000000000)
        self.reservoir_pressure_spinbox.setValue(300.000000000000000)

        self.horizontalLayout_25.addWidget(self.reservoir_pressure_spinbox)


        self.verticalLayout_13.addLayout(self.horizontalLayout_25)

        self.horizontalLayout_26 = QHBoxLayout()
        self.horizontalLayout_26.setObjectName(u"horizontalLayout_26")
        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.debit_label_support = QLabel(self.static_params_group)
        self.debit_label_support.setObjectName(u"debit_label_support")

        self.horizontalLayout_7.addWidget(self.debit_label_support)

        self.debit_status_label = QLabel(self.static_params_group)
        self.debit_status_label.setObjectName(u"debit_status_label")

        self.horizontalLayout_7.addWidget(self.debit_status_label)


        self.horizontalLayout_26.addLayout(self.horizontalLayout_7)

        self.horizontalLayout_15 = QHBoxLayout()
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.debit_label = QLabel(self.static_params_group)
        self.debit_label.setObjectName(u"debit_label")

        self.horizontalLayout_15.addWidget(self.debit_label)

        self.debit_doubleSpinBox = QDoubleSpinBox(self.static_params_group)
        self.debit_doubleSpinBox.setObjectName(u"debit_doubleSpinBox")
        self.debit_doubleSpinBox.setEnabled(False)
        self.debit_doubleSpinBox.setReadOnly(False)
        self.debit_doubleSpinBox.setMaximum(100000.000000000000000)
        self.debit_doubleSpinBox.setValue(100.000000000000000)

        self.horizontalLayout_15.addWidget(self.debit_doubleSpinBox)


        self.horizontalLayout_26.addLayout(self.horizontalLayout_15)


        self.verticalLayout_13.addLayout(self.horizontalLayout_26)

        self.insert_static_params_button = QPushButton(self.static_params_group)
        self.insert_static_params_button.setObjectName(u"insert_static_params_button")
        self.insert_static_params_button.setEnabled(False)

        self.verticalLayout_13.addWidget(self.insert_static_params_button)


        self.verticalLayout_14.addWidget(self.static_params_group)

        self.optimize_params_block = QGroupBox(self.scrollAreaWidgetContents)
        self.optimize_params_block.setObjectName(u"optimize_params_block")
        self.verticalLayout_12 = QVBoxLayout(self.optimize_params_block)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.groupBox_4 = QGroupBox(self.optimize_params_block)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.horizontalLayout_20 = QHBoxLayout(self.groupBox_4)
        self.horizontalLayout_20.setObjectName(u"horizontalLayout_20")
        self.frac_length_min_border_label = QLabel(self.groupBox_4)
        self.frac_length_min_border_label.setObjectName(u"frac_length_min_border_label")

        self.horizontalLayout_20.addWidget(self.frac_length_min_border_label)

        self.frac_length_min_border_doubleSpinBox = QDoubleSpinBox(self.groupBox_4)
        self.frac_length_min_border_doubleSpinBox.setObjectName(u"frac_length_min_border_doubleSpinBox")
        self.frac_length_min_border_doubleSpinBox.setEnabled(False)
        self.frac_length_min_border_doubleSpinBox.setDecimals(2)
        self.frac_length_min_border_doubleSpinBox.setMaximum(10000.000000000000000)
        self.frac_length_min_border_doubleSpinBox.setValue(0.010000000000000)

        self.horizontalLayout_20.addWidget(self.frac_length_min_border_doubleSpinBox)

        self.frac_length_max_border_label = QLabel(self.groupBox_4)
        self.frac_length_max_border_label.setObjectName(u"frac_length_max_border_label")

        self.horizontalLayout_20.addWidget(self.frac_length_max_border_label)

        self.frac_length_max_border_doubleSpinBox = QDoubleSpinBox(self.groupBox_4)
        self.frac_length_max_border_doubleSpinBox.setObjectName(u"frac_length_max_border_doubleSpinBox")
        self.frac_length_max_border_doubleSpinBox.setEnabled(False)
        self.frac_length_max_border_doubleSpinBox.setMaximum(10000.000000000000000)
        self.frac_length_max_border_doubleSpinBox.setValue(10000.000000000000000)

        self.horizontalLayout_20.addWidget(self.frac_length_max_border_doubleSpinBox)


        self.verticalLayout_12.addWidget(self.groupBox_4)

        self.groupBox_5 = QGroupBox(self.optimize_params_block)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.groupBox_5.setMinimumSize(QSize(0, 0))
        self.horizontalLayout_19 = QHBoxLayout(self.groupBox_5)
        self.horizontalLayout_19.setObjectName(u"horizontalLayout_19")
        self.permeability_min_border_label = QLabel(self.groupBox_5)
        self.permeability_min_border_label.setObjectName(u"permeability_min_border_label")

        self.horizontalLayout_19.addWidget(self.permeability_min_border_label)

        self.permeability_min_border_doubleSpinBox = QDoubleSpinBox(self.groupBox_5)
        self.permeability_min_border_doubleSpinBox.setObjectName(u"permeability_min_border_doubleSpinBox")
        self.permeability_min_border_doubleSpinBox.setEnabled(False)
        self.permeability_min_border_doubleSpinBox.setDecimals(4)
        self.permeability_min_border_doubleSpinBox.setMaximum(1000.000000000000000)
        self.permeability_min_border_doubleSpinBox.setValue(0.000100000000000)

        self.horizontalLayout_19.addWidget(self.permeability_min_border_doubleSpinBox)

        self.permeability_max_border_label = QLabel(self.groupBox_5)
        self.permeability_max_border_label.setObjectName(u"permeability_max_border_label")

        self.horizontalLayout_19.addWidget(self.permeability_max_border_label)

        self.permeability_max_border_doubleSpinBox = QDoubleSpinBox(self.groupBox_5)
        self.permeability_max_border_doubleSpinBox.setObjectName(u"permeability_max_border_doubleSpinBox")
        self.permeability_max_border_doubleSpinBox.setEnabled(False)
        self.permeability_max_border_doubleSpinBox.setDecimals(4)
        self.permeability_max_border_doubleSpinBox.setMaximum(1000.000000000000000)
        self.permeability_max_border_doubleSpinBox.setValue(100.000000000000000)

        self.horizontalLayout_19.addWidget(self.permeability_max_border_doubleSpinBox)


        self.verticalLayout_12.addWidget(self.groupBox_5)

        self.insert_thresholds_button = QPushButton(self.optimize_params_block)
        self.insert_thresholds_button.setObjectName(u"insert_thresholds_button")
        self.insert_thresholds_button.setEnabled(False)

        self.verticalLayout_12.addWidget(self.insert_thresholds_button)


        self.verticalLayout_14.addWidget(self.optimize_params_block)

        self.calculate_block = QGroupBox(self.scrollAreaWidgetContents)
        self.calculate_block.setObjectName(u"calculate_block")
        self.calculate_block.setMinimumSize(QSize(0, 0))
        self.verticalLayout_10 = QVBoxLayout(self.calculate_block)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.calculate_opt_parameters_button = QPushButton(self.calculate_block)
        self.calculate_opt_parameters_button.setObjectName(u"calculate_opt_parameters_button")
        self.calculate_opt_parameters_button.setEnabled(False)

        self.verticalLayout_10.addWidget(self.calculate_opt_parameters_button)

        self.groupBox_6 = QGroupBox(self.calculate_block)
        self.groupBox_6.setObjectName(u"groupBox_6")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.groupBox_6.sizePolicy().hasHeightForWidth())
        self.groupBox_6.setSizePolicy(sizePolicy4)
        self.groupBox_6.setMinimumSize(QSize(0, 0))
        self.verticalLayout_16 = QVBoxLayout(self.groupBox_6)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.horizontalLayout_24 = QHBoxLayout()
        self.horizontalLayout_24.setObjectName(u"horizontalLayout_24")
        self.skin_result_label = QLabel(self.groupBox_6)
        self.skin_result_label.setObjectName(u"skin_result_label")

        self.horizontalLayout_24.addWidget(self.skin_result_label)

        self.skin_result_spinbox = QDoubleSpinBox(self.groupBox_6)
        self.skin_result_spinbox.setObjectName(u"skin_result_spinbox")
        self.skin_result_spinbox.setEnabled(False)
        self.skin_result_spinbox.setReadOnly(True)
        self.skin_result_spinbox.setMaximum(30.000000000000000)

        self.horizontalLayout_24.addWidget(self.skin_result_spinbox)


        self.verticalLayout_16.addLayout(self.horizontalLayout_24)

        self.horizontalLayout_23 = QHBoxLayout()
        self.horizontalLayout_23.setObjectName(u"horizontalLayout_23")
        self.permeability_result_label = QLabel(self.groupBox_6)
        self.permeability_result_label.setObjectName(u"permeability_result_label")

        self.horizontalLayout_23.addWidget(self.permeability_result_label)

        self.permeability_result_spinbox = QDoubleSpinBox(self.groupBox_6)
        self.permeability_result_spinbox.setObjectName(u"permeability_result_spinbox")
        self.permeability_result_spinbox.setEnabled(False)
        self.permeability_result_spinbox.setReadOnly(True)
        self.permeability_result_spinbox.setDecimals(4)
        self.permeability_result_spinbox.setMaximum(1000.000000000000000)

        self.horizontalLayout_23.addWidget(self.permeability_result_spinbox)


        self.verticalLayout_16.addLayout(self.horizontalLayout_23)

        self.horizontalLayout_22 = QHBoxLayout()
        self.horizontalLayout_22.setObjectName(u"horizontalLayout_22")
        self.frac_length_result_label = QLabel(self.groupBox_6)
        self.frac_length_result_label.setObjectName(u"frac_length_result_label")

        self.horizontalLayout_22.addWidget(self.frac_length_result_label)

        self.frac_length_result_spinbox = QDoubleSpinBox(self.groupBox_6)
        self.frac_length_result_spinbox.setObjectName(u"frac_length_result_spinbox")
        self.frac_length_result_spinbox.setEnabled(False)
        self.frac_length_result_spinbox.setReadOnly(True)
        self.frac_length_result_spinbox.setDecimals(2)
        self.frac_length_result_spinbox.setMaximum(100000.000000000000000)

        self.horizontalLayout_22.addWidget(self.frac_length_result_spinbox)


        self.verticalLayout_16.addLayout(self.horizontalLayout_22)


        self.verticalLayout_10.addWidget(self.groupBox_6)


        self.verticalLayout_14.addWidget(self.calculate_block)

        self.report_group = QGroupBox(self.scrollAreaWidgetContents)
        self.report_group.setObjectName(u"report_group")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.report_group.sizePolicy().hasHeightForWidth())
        self.report_group.setSizePolicy(sizePolicy5)
        self.report_group.setMinimumSize(QSize(0, 180))
        self.verticalLayout_6 = QVBoxLayout(self.report_group)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.text_report = QTextEdit(self.report_group)
        self.text_report.setObjectName(u"text_report")
        sizePolicy5.setHeightForWidth(self.text_report.sizePolicy().hasHeightForWidth())
        self.text_report.setSizePolicy(sizePolicy5)
        self.text_report.setMinimumSize(QSize(0, 0))
        self.text_report.setMaximumSize(QSize(16777215, 16777215))
        self.text_report.setReadOnly(True)

        self.verticalLayout_6.addWidget(self.text_report)


        self.verticalLayout_14.addWidget(self.report_group)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_3.addWidget(self.scrollArea)


        self.horizontalLayout_5.addWidget(self.left_panel)

        self.tab_widget = QTabWidget(self.centralwidget)
        self.tab_widget.setObjectName(u"tab_widget")
        sizePolicy5.setHeightForWidth(self.tab_widget.sizePolicy().hasHeightForWidth())
        self.tab_widget.setSizePolicy(sizePolicy5)
        self.tab_widget.setMinimumSize(QSize(0, 0))
        self.timeseries_tab = QWidget()
        self.timeseries_tab.setObjectName(u"timeseries_tab")
        self.verticalLayout = QVBoxLayout(self.timeseries_tab)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.preprocessing_groupBoxs = QGroupBox(self.timeseries_tab)
        self.preprocessing_groupBoxs.setObjectName(u"preprocessing_groupBoxs")
        sizePolicy4.setHeightForWidth(self.preprocessing_groupBoxs.sizePolicy().hasHeightForWidth())
        self.preprocessing_groupBoxs.setSizePolicy(sizePolicy4)
        self.preprocessing_groupBoxs.setMinimumSize(QSize(0, 0))
        self.preprocessing_groupBoxs.setMaximumSize(QSize(16777215, 75))
        self.horizontalLayout = QHBoxLayout(self.preprocessing_groupBoxs)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.ml_filter_btn = QPushButton(self.preprocessing_groupBoxs)
        self.ml_filter_btn.setObjectName(u"ml_filter_btn")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.ml_filter_btn.sizePolicy().hasHeightForWidth())
        self.ml_filter_btn.setSizePolicy(sizePolicy6)

        self.horizontalLayout.addWidget(self.ml_filter_btn)

        self.extrapolate_btn = QPushButton(self.preprocessing_groupBoxs)
        self.extrapolate_btn.setObjectName(u"extrapolate_btn")
        sizePolicy6.setHeightForWidth(self.extrapolate_btn.sizePolicy().hasHeightForWidth())
        self.extrapolate_btn.setSizePolicy(sizePolicy6)

        self.horizontalLayout.addWidget(self.extrapolate_btn)

        self.interp_btn = QPushButton(self.preprocessing_groupBoxs)
        self.interp_btn.setObjectName(u"interp_btn")
        sizePolicy6.setHeightForWidth(self.interp_btn.sizePolicy().hasHeightForWidth())
        self.interp_btn.setSizePolicy(sizePolicy6)

        self.horizontalLayout.addWidget(self.interp_btn)

        self.outlier_btn = QPushButton(self.preprocessing_groupBoxs)
        self.outlier_btn.setObjectName(u"outlier_btn")
        sizePolicy6.setHeightForWidth(self.outlier_btn.sizePolicy().hasHeightForWidth())
        self.outlier_btn.setSizePolicy(sizePolicy6)

        self.horizontalLayout.addWidget(self.outlier_btn)

        self.reset_plots_btn = QPushButton(self.preprocessing_groupBoxs)
        self.reset_plots_btn.setObjectName(u"reset_plots_btn")
        sizePolicy6.setHeightForWidth(self.reset_plots_btn.sizePolicy().hasHeightForWidth())
        self.reset_plots_btn.setSizePolicy(sizePolicy6)

        self.horizontalLayout.addWidget(self.reset_plots_btn)


        self.verticalLayout.addWidget(self.preprocessing_groupBoxs)

        self.groupBox = QGroupBox(self.timeseries_tab)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setMaximumSize(QSize(16777215, 75))
        self.horizontalLayout_6 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.cb_burde_curve_dock = QCheckBox(self.groupBox)
        self.cb_burde_curve_dock.setObjectName(u"cb_burde_curve_dock")

        self.horizontalLayout_6.addWidget(self.cb_burde_curve_dock)

        self.cb_debit_dock = QCheckBox(self.groupBox)
        self.cb_debit_dock.setObjectName(u"cb_debit_dock")

        self.horizontalLayout_6.addWidget(self.cb_debit_dock)

        self.cb_pressure_dock = QCheckBox(self.groupBox)
        self.cb_pressure_dock.setObjectName(u"cb_pressure_dock")

        self.horizontalLayout_6.addWidget(self.cb_pressure_dock)

        self.cb_calc_XY_dock = QCheckBox(self.groupBox)
        self.cb_calc_XY_dock.setObjectName(u"cb_calc_XY_dock")

        self.horizontalLayout_6.addWidget(self.cb_calc_XY_dock)


        self.verticalLayout.addWidget(self.groupBox)

        self.dim_plot = QWidget(self.timeseries_tab)
        self.dim_plot.setObjectName(u"dim_plot")
        sizePolicy7 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(0)
        sizePolicy7.setHeightForWidth(self.dim_plot.sizePolicy().hasHeightForWidth())
        self.dim_plot.setSizePolicy(sizePolicy7)

        self.verticalLayout.addWidget(self.dim_plot)

        self.tab_widget.addTab(self.timeseries_tab, "")
        self.data_tab = QWidget()
        self.data_tab.setObjectName(u"data_tab")
        self.verticalLayout_8 = QVBoxLayout(self.data_tab)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.data_table = QTableView(self.data_tab)
        self.data_table.setObjectName(u"data_table")

        self.verticalLayout_8.addWidget(self.data_table)

        self.export_data_table_btn = QPushButton(self.data_tab)
        self.export_data_table_btn.setObjectName(u"export_data_table_btn")

        self.verticalLayout_8.addWidget(self.export_data_table_btn)

        self.tab_widget.addTab(self.data_tab, "")
        self.type_curves_tab = QWidget()
        self.type_curves_tab.setObjectName(u"type_curves_tab")
        self.verticalLayout_9 = QVBoxLayout(self.type_curves_tab)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")

        self.verticalLayout_9.addLayout(self.horizontalLayout_4)

        self.type_curves_plot_placeholder = QWidget(self.type_curves_tab)
        self.type_curves_plot_placeholder.setObjectName(u"type_curves_plot_placeholder")
        sizePolicy5.setHeightForWidth(self.type_curves_plot_placeholder.sizePolicy().hasHeightForWidth())
        self.type_curves_plot_placeholder.setSizePolicy(sizePolicy5)

        self.verticalLayout_9.addWidget(self.type_curves_plot_placeholder)

        self.tab_widget.addTab(self.type_curves_tab, "")
        self.results_tab = QWidget()
        self.results_tab.setObjectName(u"results_tab")
        self.vboxLayout = QVBoxLayout(self.results_tab)
        self.vboxLayout.setObjectName(u"vboxLayout")
        self.results_text = QTextEdit(self.results_tab)
        self.results_text.setObjectName(u"results_text")
        sizePolicy7.setHeightForWidth(self.results_text.sizePolicy().hasHeightForWidth())
        self.results_text.setSizePolicy(sizePolicy7)

        self.vboxLayout.addWidget(self.results_text)

        self.export_report_btn = QPushButton(self.results_tab)
        self.export_report_btn.setObjectName(u"export_report_btn")

        self.vboxLayout.addWidget(self.export_report_btn)

        self.tab_widget.addTab(self.results_tab, "")

        self.horizontalLayout_5.addWidget(self.tab_widget)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
#if QT_CONFIG(shortcut)
        self.load_file_label.setBuddy(self.preprocessing_groupBoxs)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(MainWindow)

        self.tab_widget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.left_panel.setTitle("")
        self.groupBox_3.setTitle(QCoreApplication.translate("MainWindow", u"\u0414\u0438\u043d\u0430\u043c\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b \u0441\u043a\u0432\u0430\u0436\u0438\u043d\u044b", None))
        self.load_file_button.setText(QCoreApplication.translate("MainWindow", u"\u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c .csv/.las \u0444\u0430\u0439\u043b", None))
        self.load_file_label.setText(QCoreApplication.translate("MainWindow", u"\u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u0435 \u0444\u0430\u0439\u043b", None))
        self.insert_data_from_buffer_button.setText(QCoreApplication.translate("MainWindow", u"\u0412\u0441\u0442\u0430\u0432\u043a\u0430 \u0438\u0437 \u0431\u0443\u0444\u0435\u0440\u0430 \u043e\u0431\u043c\u0435\u043d\u0430", None))
        self.reset_data_button.setText(QCoreApplication.translate("MainWindow", u"\u0421\u0431\u0440\u043e\u0441\u0438\u0442\u044c \u0434\u0430\u043d\u043d\u044b\u0435", None))
        self.export_session_btn.setText(QCoreApplication.translate("MainWindow", u"\u042d\u043a\u0441\u043f\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u0435\u0441\u0441\u0438\u044e", None))
        self.import_session_btn.setText(QCoreApplication.translate("MainWindow", u"\u0418\u043c\u043f\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u0435\u0441\u0441\u0438\u044e", None))
        self.static_params_group.setTitle(QCoreApplication.translate("MainWindow", u"\u0421\u0442\u0430\u0442\u0438\u0447\u043d\u044b\u0435 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b \u043f\u043b\u0430\u0441\u0442\u0430 \u0438 \u0441\u043a\u0432\u0430\u0436\u0438\u043d\u044b", None))
        self.well_length_label.setText(QCoreApplication.translate("MainWindow", u"\u0414\u043b\u0438\u043d\u0430 \u0441\u043a\u0432\u0430\u0436\u0438\u043d\u044b, \u043c", None))
        self.well_height_label.setText(QCoreApplication.translate("MainWindow", u"\u0422\u043e\u043b\u0449\u0438\u043d\u0430 \u0441\u043a\u0432\u0430\u0436\u0438\u043d\u044b, \u043c", None))
        self.viscosity_label.setText(QCoreApplication.translate("MainWindow", u"\u0412\u044f\u0437\u043a\u043e\u0441\u0442\u044c, \u0441\u041f", None))
        self.volume_coef_label.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0431\u044a\u0435\u043c\u043d\u044b\u0439 \u043a\u043e\u044d\u0444\u0444\u0438\u0446\u0438\u0435\u043d\u0442", None))
        self.porosity_label.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0440\u0438\u0441\u0442\u043e\u0441\u0442\u044c", None))
        self.frac_amount_label.setText(QCoreApplication.translate("MainWindow", u"\u041a\u043e\u043b-\u0432\u043e \u0442\u0440\u0435\u0449\u0438\u043d", None))
        self.compressibility_label.setText(QCoreApplication.translate("MainWindow", u"\u0421\u0436\u0438\u043c\u0430\u0435\u043c\u043e\u0441\u0442\u044c \u0441\u0438\u0441\u0442\u0435\u043c\u044b, \u0430\u0442\u043c^-1", None))
        self.reservoir_pressure_label.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043b\u0430\u0441\u0442\u043e\u0432\u043e\u0435 \u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435, \u043a\u0433\u0441/\u0441\u043c^2", None))
        self.debit_label_support.setText(QCoreApplication.translate("MainWindow", u"\u041d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e \u0443\u043a\u0430\u0437\u0430\u0442\u044c \u0434\u0435\u0431\u0438\u0442:", None))
        self.debit_status_label.setText(QCoreApplication.translate("MainWindow", u"\u041d\u0435\u0442", None))
        self.debit_label.setText(QCoreApplication.translate("MainWindow", u"\u0414\u0435\u0431\u0438\u0442 ", None))
        self.insert_static_params_button.setText(QCoreApplication.translate("MainWindow", u"\u0412\u0432\u0435\u0441\u0442\u0438 \u0441\u0442\u0430\u0442\u0438\u0447\u043d\u044b\u0435 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b", None))
        self.optimize_params_block.setTitle(QCoreApplication.translate("MainWindow", u"\u041e\u043f\u0442\u0438\u043c\u0438\u0437\u0438\u0440\u0443\u0435\u043c\u044b\u0435 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u043b\u0443\u0434\u043b\u0438\u043d\u0430 \u0442\u0440\u0435\u0449\u0438\u043d\u044b, \u043c", None))
        self.frac_length_min_border_label.setText(QCoreApplication.translate("MainWindow", u"\u041c\u0438\u043d. \u0433\u0440\u0430\u043d\u0438\u0446\u0430", None))
        self.frac_length_max_border_label.setText(QCoreApplication.translate("MainWindow", u"\u041c\u0430\u043a\u0441. \u0433\u0440\u0430\u043d\u0438\u0446\u0430", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u043e\u043d\u0438\u0446\u0430\u0435\u043c\u043e\u0441\u0442\u044c, \u043c\u0414", None))
        self.permeability_min_border_label.setText(QCoreApplication.translate("MainWindow", u"\u041c\u0438\u043d. \u0433\u0440\u0430\u043d\u0438\u0446\u0430", None))
        self.permeability_max_border_label.setText(QCoreApplication.translate("MainWindow", u"\u041c\u0430\u043a\u0441. \u0433\u0440\u0430\u043d\u0438\u0446\u0430", None))
        self.insert_thresholds_button.setText(QCoreApplication.translate("MainWindow", u"\u0412\u0432\u0435\u0441\u0442\u0438 \u0433\u0440\u0430\u043d\u0438\u0446\u044b \u043e\u043f\u0442\u0438\u043c\u0438\u0437\u0430\u0446\u0438\u0438", None))
        self.calculate_block.setTitle(QCoreApplication.translate("MainWindow", u"\u041e\u043f\u0435\u0440\u0430\u0446\u0438\u044f \u0440\u0430\u0441\u0447\u0435\u0442\u0430", None))
        self.calculate_opt_parameters_button.setText(QCoreApplication.translate("MainWindow", u"\u0420\u0430\u0441\u0447\u0438\u0442\u0430\u0442\u044c \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b", None))
        self.groupBox_6.setTitle(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u043b\u0443\u0447\u0435\u043d\u043d\u044b\u0435 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b", None))
        self.skin_result_label.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043a\u0438\u043d-\u0444\u0430\u043a\u0442\u043e\u0440", None))
        self.permeability_result_label.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u043e\u043d\u0438\u0446\u0430\u0435\u043c\u043e\u0441\u0442\u044c, \u043c\u0414", None))
        self.frac_length_result_label.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u043b\u0443\u0434\u043b\u0438\u043d\u0430 \u0442\u0440\u0435\u0449\u0438\u043d\u044b, \u043c", None))
        self.report_group.setTitle(QCoreApplication.translate("MainWindow", u"\u041e\u0442\u0447\u0451\u0442", None))
        self.preprocessing_groupBoxs.setTitle(QCoreApplication.translate("MainWindow", u"\u041e\u043f\u0435\u0440\u0430\u0446\u0438\u0438 \u043d\u0430\u0434 \u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435\u043c \u0438 \u0434\u0435\u0431\u0438\u0442\u043e\u043c", None))
        self.ml_filter_btn.setText(QCoreApplication.translate("MainWindow", u"\u0421\u0433\u043b\u0430\u0434\u0438\u0442\u044c", None))
        self.extrapolate_btn.setText(QCoreApplication.translate("MainWindow", u"\u042d\u043a\u0441\u0442\u0440\u0430\u043f\u043e\u043b\u0438\u0440\u043e\u0432\u0430\u0442\u044c", None))
        self.interp_btn.setText(QCoreApplication.translate("MainWindow", u"\u0412\u043e\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c \u043f\u0440\u043e\u043f\u0443\u0441\u043a\u0438", None))
        self.outlier_btn.setText(QCoreApplication.translate("MainWindow", u"\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0432\u044b\u0431\u0440\u043e\u0441\u044b", None))
        self.reset_plots_btn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0442\u043c\u0435\u043d\u0438\u0442\u044c \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f", None))
        self.groupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u0413\u0440\u0430\u0444\u0438\u043a\u0438 \u0434\u043b\u044f \u043e\u0442\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u044f", None))
        self.cb_burde_curve_dock.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u043d\u0430\u044f \u0411\u0443\u0440\u0434\u0435 (dP/dt)", None))
        self.cb_debit_dock.setText(QCoreApplication.translate("MainWindow", u"\u0413\u0440\u0430\u0444\u0438\u043a \u0434\u0435\u0431\u0438\u0442\u0430", None))
        self.cb_pressure_dock.setText(QCoreApplication.translate("MainWindow", u"\u0413\u0440\u0430\u0444\u0438\u043a \u0434\u0430\u0432\u043b\u0435\u043d\u0438\u044f", None))
        self.cb_calc_XY_dock.setText(QCoreApplication.translate("MainWindow", u"\u0411\u0435\u0437\u0440\u0430\u0437\u043c\u0435\u0440\u043d\u044b\u0435 X-Y", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.timeseries_tab), QCoreApplication.translate("MainWindow", u"\u041e\u043f\u0435\u0440\u0430\u0446\u0438\u0438 \u0438 \u0433\u0440\u0430\u0444\u0438\u043a\u0438", None))
        self.export_data_table_btn.setText(QCoreApplication.translate("MainWindow", u"\u042d\u043a\u0441\u043f\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0434\u0430\u043d\u043d\u044b\u0435", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.data_tab), QCoreApplication.translate("MainWindow", u"\u0422\u0430\u0431\u043b\u0438\u0447\u043d\u043e\u0435 \u043f\u0440\u0435\u0434\u0441\u0442\u0430\u0432\u043b\u0435\u043d\u0438\u0435", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.type_curves_tab), QCoreApplication.translate("MainWindow", u"\u042d\u0442\u0430\u043b\u043e\u043d\u043d\u044b\u0435 \u043a\u0440\u0438\u0432\u044b\u0435", None))
        self.export_report_btn.setText(QCoreApplication.translate("MainWindow", u"\u042d\u043a\u0441\u043f\u043e\u0440\u0442 \u043e\u0442\u0447\u0435\u0442\u0430", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.results_tab), QCoreApplication.translate("MainWindow", u"\u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u044b", None))
    # retranslateUi

