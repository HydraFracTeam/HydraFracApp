from PySide6.QtWidgets import (QLabel, QTableView, QApplication, QMainWindow, QFileDialog, QMessageBox, 
                               QComboBox, QSpinBox, QPushButton, QWidget, QVBoxLayout, QHeaderView,                               
                               QHBoxLayout, QTabWidget, QTextEdit, QGroupBox, QGridLayout, QDialog,
                               QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem

import sys
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
from scipy.interpolate import interp1d
import pickle
import os


from ui.ui import Ui_MainWindow

# from helpers.input_test import diag_dimensional
from old_helpers.ui_setup import setup_interface
# from helpers.utils import get_filename



class MyApp(QMainWindow):
    def __init__(self, test_mode: bool = False) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.test_mode = test_mode  # Флаг для отключения сообщений в тестах

        self.loaded_data = []  # Список WellTimeSeries объектов
        self.current_index = 0  # Индекс текущей скважины
        self.validation_data = []  # Данные для проверки качества интерполяции
        self.last_interpolated_mask_XY = None  # Маска восстановленных точек для выделения на X-Y
        self.last_interpolated_pressure = None  # Интерполированные значения давления (не изменяют исходные данные)
        self.last_extrapolated_XY = None  # Пара экстраполированных X,Y для отображения
        self.last_extrapolation_result = None  # Результат экстраполяции с метриками качества
        self.last_fitted_XY = None  # Подогнанные X,Y с коэффициентами поправки
        self.last_fit_coefficients = None  # Коэффициенты подгонки (a для X, a_y, b, c для Y)
        self.original_calc_XY = None  # Оригинальные расчётные X,Y (до подгонки)
        self.trained_interpolator = None  # Обученный интерполятор (может быть загружен из файла)
        self.trained_interpolator_path = None  # Путь к загруженной модели
        self.trained_interpolation_model = None  # Обученная модель интерполяции (DimensionlessCurveInterpolator)
        self.trained_interpolation_model_path = None  # Путь к загруженной модели интерполяции
        
        # Создаем  интерфейс с вкладками
        setup_interface(self)
        
        # Настраиваем обработчики событий
    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())
