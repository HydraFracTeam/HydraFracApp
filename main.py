from PySide6.QtWidgets import (QLabel, QTableView, QApplication, QMainWindow, QFileDialog, QMessageBox, 
                               QComboBox, QSpinBox, QPushButton, QWidget, QVBoxLayout, QHeaderView,                               
                               QHBoxLayout, QTabWidget, QTextEdit, QGroupBox, QGridLayout, QDialog,
                               QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem

import sys
import numpy as np
from typing import List, Dict, Tuple


from ui.ui import Ui_MainWindow
from core.app_state import AppState
from utils import format_pydantic_error

# pydantic
from schemas.static_params import StaticParams
from schemas.optimize_thresholds import OptimizeThresholds
from core.models import ProcessingDynamicData
import processing.dimensional_transfrorms as dm_transformation
from processing.loaders import csv_loader, las_loader
from utils import get_file_suffix, get_filename
from old_helpers.ui_setup import setup_interface



class MyApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.app_state = AppState()
        
        self._load_controls: List[QWidget] = [
            self.ui.load_file_button,
            self.ui.insert_data_from_buffer_button,
        ]
        self._static_controls: List[QWidget] = [
            self.ui.well_length_spinbox,
            self.ui.well_height_spinBox,
            self.ui.viscosity_spinBox,
            self.ui.volume_coef_spinBox,
            self.ui.porosity_spinBox,
            self.ui.frac_amount_spinBox,
            self.ui.compressibility_spinBox,
            self.ui.reservoir_pressure_spinbox,
            self.ui.insert_static_params_button,
        ]
        self._threshold_controls: List[QWidget] = [
            self.ui.frac_length_min_border_doubleSpinBox,
            self.ui.frac_length_max_border_doubleSpinBox,
            self.ui.permeability_min_border_doubleSpinBox,
            self.ui.permeability_max_border_doubleSpinBox,
            self.ui.insert_thresholds_button,
        ]
        self._calculation_controls: List[QWidget] = [
            self.ui.calculate_opt_parameters_button,
            self.ui.skin_result_spinbox,
            self.ui.frac_length_result_spinbox,
            self.ui.permeability_result_spinbox,
        ]
        
               
        # Соединяем ui элементы и соответствующие функции
        self.setup_load_dynamic_data_menu()
        self.setup_static_data_menu()
        self.setup_threshold_menu()
        # Создаем  интерфейс с вкладками
        setup_interface(self)
    
    
    ## РАЗДЕЛ ЗАГРУЗКИ ДИНАМИЧЕСКИХ ДАННЫХ
    def setup_load_dynamic_data_menu(self):
        self.ui.load_file_button.clicked.connect(self.load_dynamic_data_from_file)
        self.ui.reset_data_button.clicked.connect(self.reset_all_data)
        ## todo позже добавить вставку из буфера через отдельное окошко, как будет все готово
        # self.ui.insert_data_from_buffer_button.connect(...)
    
    def load_dynamic_data_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл с данным",
            "",
            "Файлы с данными (*.csv *.las)"
        )

        # Если пользователь нажал "Отмена", file_path будет пустым
        if not file_path:
            return

        suffix = get_file_suffix(file_path)
        try:
            if suffix == ".csv":
                raw_data = csv_loader.load_dynamic_data_from_csv(file_path)

            elif suffix == ".las":
                raw_data = las_loader.load_dynamic_data_from_las(file_path)
            else:
                raise ValueError("Загружать можно только .csv или .las файлы.")
        
            self.app_state.raw_dynamic_data = raw_data
            
            file_name = get_filename(file_path=file_path)
            self.ui.load_file_label.setText(file_name)
            self.show_in_text_report(f"Динамические данные успешны загружены из файла {file_name}.")
            self.enable_static_controls()
            self.disable_load_controls()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка загрузки динамических данных",
                format_pydantic_error(e)
            )
            return
    
    ## РАЗДЕЛ РАБОТЫ СО СТАТИЧНЫМИ ПАРАМЕТРАМИ

    def setup_static_data_menu(self):
        self.ui.insert_static_params_button.clicked.connect(self.get_static_params)

    def get_static_params(self):

        raw = self.app_state.raw_dynamic_data
        if raw is None:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите динамические данные.")
            return

        static_data = {
            "W": self.ui.well_length_spinbox.value(),
            "h": self.ui.well_height_spinBox.value(),
            "mu": self.ui.viscosity_spinBox.value(),
            "phi": self.ui.porosity_spinBox.value(),
            "B": self.ui.volume_coef_spinBox.value(),
            "ct": self.ui.compressibility_spinBox.value(),
            "N": self.ui.frac_amount_spinBox.value(),
            "P0": self.ui.reservoir_pressure_spinbox.value(),
        }

        # если дебит был не в динамике 
        if not raw.is_Q_in_dynamic_input:
            static_data["Q_constant"] = self.ui.debit_doubleSpinBox.value()

        try:
            params = StaticParams(**static_data)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка ввода параметров",
                format_pydantic_error(e)
            )
            return
        
        self.app_state.static_params = params
        # пересчитываем дебит для вводных данных после валидации статики
        if not raw.is_Q_in_dynamic_input:
            self.app_state.raw_dynamic_data.Q = np.full(
                len(self.app_state.raw_dynamic_data.t),
                static_data["Q_constant"],
                dtype=float
            )

        self.show_in_text_report("Статические параметры успешно введены.")
    
        self.disable_static_controls()
        self.enable_threshold_controls()

    ## РАЗДЕЛ ГРАНИЦ ОПТИМИЗАЦИИ
    def setup_threshold_menu(self):
        self.ui.insert_thresholds_button.clicked.connect(self.get_thresholds)
    
    def get_thresholds(self):

        if self.app_state.static_params is None:
            QMessageBox.warning(self, "Ошибка", "Сначала введите статические параметры.")
            return

        data = {
            "L_min": self.ui.frac_length_min_border_doubleSpinBox.value(),
            "L_max": self.ui.frac_length_max_border_doubleSpinBox.value(),
            "k_min": self.ui.permeability_min_border_doubleSpinBox.value(),
            "k_max": self.ui.permeability_max_border_doubleSpinBox.value(),
        }

        try:
            thresholds = OptimizeThresholds(**data)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка ввода границ",
                format_pydantic_error(e)
            )
            return

        self.app_state.optimize_thresholds = thresholds

        normalized_Q = dm_transformation.normalize_Q_by_n(
            Q_total=self.app_state.raw_dynamic_data.Q,
            N = self.app_state.static_params.N,
        )
        calculated_dP = dm_transformation.calculate_dP(
            P = self.app_state.raw_dynamic_data.P,
            P0 = self.app_state.static_params.P0,
        )
        self.app_state.processing_dynamic_data = ProcessingDynamicData(
            t = self.app_state.raw_dynamic_data.t,
            P = self.app_state.raw_dynamic_data.P,
            Q = normalized_Q,
            dP=calculated_dP,
        )
        print(self.app_state.processing_dynamic_data)

        self.show_in_text_report("Границы оптимизации успешно заданы.")
        self.show_in_text_report("Ввод данных успешен. Проверить динамические данные можете на вкладке 'Табличное представление'")
        self.disable_threshold_controls()
        self.enable_calculation_controls()
    
    ## ВКЛЮЧЕНИЕ/ВЫКЛЮЧЕНИЕ UI ЭЛЕМЕНТОВ
    def enable_load_controls(self) -> None:
        for elem in self._load_controls:
            elem.setEnabled(True)
        
    def disable_load_controls(self) -> None:
        for elem in self._load_controls:
            elem.setEnabled(False)
    
    def enable_static_controls(self) -> None:
        for spinbox in self._static_controls:
            spinbox.setEnabled(True)
        if self.app_state.raw_dynamic_data and not self.app_state.raw_dynamic_data.is_Q_in_dynamic_input:
            self.ui.debit_status_label.setText("Да")
            self.ui.debit_doubleSpinBox.setEnabled(True)
            
    def disable_static_controls(self) -> None:
        for spinbox in self._static_controls:
            spinbox.setEnabled(False)
        self.ui.debit_status_label.setText("Нет")
        self.ui.debit_doubleSpinBox.setEnabled(False)
        
    def enable_threshold_controls(self) -> None:
        for elem in self._threshold_controls:
            elem.setEnabled(True)
        
    def disable_threshold_controls(self) -> None:
        for elem in self._threshold_controls:
            elem.setEnabled(False)
            
    def enable_calculation_controls(self) -> None:
        for elem in self._calculation_controls:
            elem.setEnabled(True)
        
    def disable_calculation_controls(self) -> None:
        for elem in self._calculation_controls:
            elem.setEnabled(False)
    
        
    ## ПРОЧЕЕ / ВСПОМОГАТЕЛЬНОЕ
    def reset_all_data(self):
        self.app_state = AppState()
        self.enable_load_controls()
        self.disable_static_controls()
        self.disable_threshold_controls()
        self.disable_calculation_controls()
        self.ui.text_report.clear()
        self.ui.load_file_label.setText("Файл не загружен")
            
    def show_in_text_report(self, text: str) -> None:
        self.ui.text_report.append(text)
    
            

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())
