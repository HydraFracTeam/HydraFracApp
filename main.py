from PySide6.QtWidgets import (QLabel, QTableView, QApplication, QMainWindow, QFileDialog, QMessageBox, 
                               QComboBox, QSpinBox, QPushButton, QWidget, QVBoxLayout, QHeaderView,                               
                               QHBoxLayout, QTabWidget, QTextEdit, QGroupBox, QGridLayout, QDialog,
                               QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem

import sys
from pathlib import Path



from ui.ui import Ui_MainWindow
from core.app_state import AppState

from processing.loaders import csv_loader
from utils import get_file_suffix
from old_helpers.ui_setup import setup_interface



class MyApp(QMainWindow):
    def __init__(self, test_mode: bool = False) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.app_state = AppState()
        
        # Соединяем ui элементы и соответствующие функции
        self.setup_load_menu()
        # Создаем  интерфейс с вкладками
        setup_interface(self)
    
    def setup_load_menu(self):
        self.ui.load_file_button.clicked.connect(self.load_dynamic_data_from_file)
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
            self.ui.text_report.append("Динамические данные успешны загружены. \
                                       \n Можно переходить к вводу статичных параметров.")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка загрузки динамических данных",
                str(e)
            )
            return
            

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())
