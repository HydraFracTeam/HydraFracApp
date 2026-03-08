from PySide6.QtWidgets import (QLabel, QTableView, QApplication, QMainWindow, QFileDialog, QMessageBox, 
                               QComboBox, QSpinBox, QPushButton, QWidget, QVBoxLayout, QHeaderView,                               
                               QHBoxLayout, QTabWidget, QTextEdit, QGroupBox, QGridLayout, QDialog,
                               QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem

import sys
from typing import List, Dict, Tuple



from ui.ui import Ui_MainWindow
from core.app_state import AppState
from core.models import RawDynamicData 

from processing.loaders import csv_loader, las_loader
from utils import get_file_suffix, get_filename
from old_helpers.ui_setup import setup_interface



class MyApp(QMainWindow):
    def __init__(self, test_mode: bool = False) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.app_state = AppState()
        
        
        self._common_static_params: List[QSpinBox] = [
            self.ui.well_length_spinbox,
            self.ui.well_height_spinBox,
            self.ui.viscosity_spinBox,
            self.ui.volume_coef_spinBox,
            self.ui.porosity_spinBox,
            self.ui.frac_amount_spinBox,
            self.ui.compressibility_spinBox,
        ]
               
        # Соединяем ui элементы и соответствующие функции
        self.setup_load_dynamic_data_menu()
        # Создаем  интерфейс с вкладками
        setup_interface(self)
    
    def setup_load_dynamic_data_menu(self):
        self.ui.load_file_button.clicked.connect(self.load_dynamic_data_from_file)
        self.ui.reset_data_button.clicked.connect(self.reset_all_data)
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
        
            self.app_state.raw_dynamic = raw_data
            
            file_name = get_filename(file_path=file_path)
            self.ui.load_file_label.setText(file_name)
            self.show_in_text_report(f"Динамические данные успешны загружены из файла {file_name}.")
            self.enable_static_params()
            self.disable_load_menu_buttons()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка загрузки динамических данных",
                str(e)
            )
            return
    
        
    def show_in_text_report(self, text: str) -> None:
        self.ui.text_report.append(text)
        
    
    def enable_load_menu_buttons(self) -> None:
        self.ui.load_file_button.setEnabled(True)
        self.ui.insert_data_from_buffer_button.setEnabled(True)
        
    
    def disable_load_menu_buttons(self) -> None:
        self.ui.load_file_button.setEnabled(False)
        self.ui.insert_data_from_buffer_button.setEnabled(False)
    
    def enable_static_params(self) -> None:
        for spinbox in self._common_static_params:
            spinbox.setEnabled(True)
        if self.app_state.raw_dynamic and not self.app_state.raw_dynamic.is_Q_in_dynamic_input:
            self.ui.debit_status_label.setText("Да")
            self.ui.debit_doubleSpinBox.setEnabled(True)
            
    def disable_static_params(self) -> None:
        for spinbox in self._common_static_params:
            spinbox.setEnabled(False)
        self.ui.debit_status_label.setText("Нет")
        self.ui.debit_doubleSpinBox.setEnabled(False)
        
    def reset_all_data(self):
        self.app_state = AppState()
        self.enable_load_menu_buttons()
        self.disable_static_params()
        self.ui.text_report.clear()
        self.ui.load_file_label.setText("Файл не загружен")
    
            

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())
