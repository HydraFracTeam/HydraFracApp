from PySide6.QtCore import QObject, Signal

from processing.loaders import csv_loader, las_loader
from utils import get_file_suffix


class LoadWorker(QObject):

    finished = Signal(object, str)
    error = Signal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            suffix = get_file_suffix(self.file_path)

            if suffix == ".csv":
                raw = csv_loader.load_dynamic_data_from_csv(self.file_path)

            elif suffix == ".las":
                raw = las_loader.load_dynamic_data_from_las(self.file_path)

            else:
                raise ValueError("Поддерживаются только .csv и .las")

            self.finished.emit(raw, self.file_path)
        except Exception as e:
            self.error.emit(str(e))
