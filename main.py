import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from ui import Ui_mainWindow # Assuming your generated UI file is ui_mainwindow.py

from helpers.parse_csv_params import parse_csv_params


class MyApp(QMainWindow, Ui_mainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.load_template_button.clicked.connect(self.load_template)

    def load_template(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Load CSV File", "./", "CSV Files (*.csv);;All Files (*)")
        
        data_df, error_msg = parse_csv_params(file_path)
        if error_msg:
            QMessageBox.information(self, "Error load", error_msg)

        print(data_df)
        
        
if __name__ == "__main__":
    app = QApplication()
    window = MyApp()
    window.show()
    app.exec()
