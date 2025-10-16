import sys
import pandas as pd
import numpy as np
from PySide6.QtWidgets import QLabel, QApplication, QMainWindow, QFileDialog, QMessageBox, QComboBox, QPushButton, QWidget, QVBoxLayout, QHBoxLayout
from ui import Ui_mainWindow

from helpers.parse_csv_params import parse_csv_params
from helpers.physics import compute_transmissivity, compute_pore_volume
from helpers.timeseries import compute_derivative, interpolate_series, smooth_series

try:
    import pyqtgraph as pg
except Exception:
    pg = None


class MyApp(QMainWindow, Ui_mainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.load_template_button.clicked.connect(self.load_template)
        self.df_ts = None
        self.time_column = None  # Фиксированная колонка времени
        self.has_real_time = False  # Флаг наличия реального времени

        # Контейнер для графиков и управления
        self.plot_container = QWidget(self.centralwidget)
        self.plot_container.setGeometry(350, 20, 830, 680)
        self.plot_vlayout = QVBoxLayout(self.plot_container)
        self.plot_vlayout.setContentsMargins(0, 0, 0, 0)

        # Панель управления
        controls = QWidget(self.plot_container)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Выбор временной колонки (фиксируется при загрузке)
        self.time_label = QLabel("Время:", controls)
        self.data_combo = QComboBox(controls)  # Выбор показателя для отображения
        self.plot_btn = QPushButton("Построить", controls)
        self.deriv_btn = QPushButton("Производная", controls)
        self.interp_btn = QPushButton("Интерполяция", controls)
        self.smooth_btn = QPushButton("Сгладить", controls)
        
        controls_layout.addWidget(self.time_label)
        controls_layout.addWidget(self.data_combo)
        controls_layout.addWidget(self.plot_btn)
        controls_layout.addWidget(self.deriv_btn)
        controls_layout.addWidget(self.interp_btn)
        controls_layout.addWidget(self.smooth_btn)
        self.plot_vlayout.addWidget(controls)

        # Площадка графика
        if pg is not None:
            self.plot_widget = pg.PlotWidget(self.plot_container)
            self.plot = self.plot_widget.plot()
            
            # НАСТРОЙКА ВЕРТИКАЛЬНОГО ГРАФИКА (время по Y)
            self.plot_widget.setLabel('left', 'Время/Измерения')
            self.plot_widget.setLabel('bottom', 'Значения')
            self.plot_widget.invertY(True)  # Время идет сверху вниз
            
            self.plot_vlayout.addWidget(self.plot_widget)
        else:
            self.plot_widget = None

        # Сигналы
        self.plot_btn.clicked.connect(self.on_plot)
        self.deriv_btn.clicked.connect(self.on_derivative)
        self.interp_btn.clicked.connect(self.on_interpolate)
        self.smooth_btn.clicked.connect(self.on_smooth)

    def load_template(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Load CSV File", "./", "CSV Files (*.csv);;All Files (*)")
        if not file_path:
            return

        # 1) Попытка разобрать параметры для скалярных расчётов
        required_params, data_df, error_msg = parse_csv_params(file_path)
        if error_msg is None and required_params is not None:
            self.k_doubleSpinBox.setValue(float(required_params.k))
            self.h_doubleSpinBox.setValue(float(required_params.h))
            self.phi_doubleSpinBox.setValue(float(required_params.phi))
            t_scalar = compute_transmissivity(required_params.k, required_params.h)
            vp_scalar = compute_pore_volume(required_params.phi, required_params.h)
            QMessageBox.information(self, "Расчёт выполнен", f"T = {t_scalar}; Vp = {vp_scalar}")
        else:
            if error_msg:
                QMessageBox.information(self, "Info", f"Схема параметров не применима: {error_msg}")

        # 2) Загрузка временного ряда
        try:
            df = pd.read_csv(file_path)
        except Exception as exc:
            QMessageBox.information(self, "Error load", f"Ошибка чтения CSV: {exc}")
            return

        # Автоматически находим колонку времени
        time_columns = [c for c in df.columns if str(c).lower().find("time") >= 0 or str(c).lower().find("date") >= 0]
        if time_columns:
            self.time_column = time_columns[0]
            self.has_real_time = True
            # Парсим даты
            try:
                df[self.time_column] = pd.to_datetime(df[self.time_column], errors="coerce")
            except Exception:
                pass
            QMessageBox.information(self, "Info", f"Найдена временная колонка: {self.time_column}")
        else:
            # Если нет временной колонки, создаем последовательные номера
            self.time_column = "Измерения"
            self.has_real_time = False
            df[self.time_column] = np.arange(len(df))
            QMessageBox.information(self, "Info", "Временная колонка не найдена, используются последовательные измерения")

        self.df_ts = df
        
        # Заполняем комбобокс только колонками данных (исключая время)
        data_columns = [col for col in df.columns if col != self.time_column]
        self.data_combo.clear()
        self.data_combo.addItems(data_columns)
        
        # Автовыбор первого показателя
        if data_columns:
            self.data_combo.setCurrentIndex(0)

        if self.plot_widget is None:
            QMessageBox.information(self, "Нет графика", "pyqtgraph не установлен.")
        
    def _get_data(self):
        """Возвращает время и выбранный показатель"""
        if self.df_ts is None or self.time_column is None:
            return None, None
        data_column = self.data_combo.currentText()
        if not data_column:
            return None, None
        time_data = self.df_ts[self.time_column]
        value_data = self.df_ts[data_column]
        return time_data, value_data

    def _plot_data(self, values, times, title: str = ""):
        """Отрисовка графика: значения по X, время по Y"""
        if self.plot_widget is None:
            return
        self.plot_widget.clear()
        
        # Преобразуем время в числовой формат
        if self.has_real_time and np.issubdtype(getattr(times, "dtype", type(times)), np.datetime64):
            time_vals = times.view("int64") / 1e9  # Конвертируем в секунды
        else:
            time_vals = pd.to_numeric(times, errors="coerce").to_numpy()
            
        value_vals = pd.to_numeric(values, errors="coerce").to_numpy()
        
        # ВЕРТИКАЛЬНЫЙ ГРАФИК: значения по X, время по Y
        self.plot_widget.plot(value_vals, time_vals, pen='y')
        
        # Настройка подписей
        self.plot_widget.setLabel('bottom', f"{self.data_combo.currentText()}")
        y_label = self.time_column if self.has_real_time else "Номер измерения"
        self.plot_widget.setLabel('left', y_label)
        
        if title:
            self.plot_widget.setTitle(title)

    def on_plot(self):
        times, values = self._get_data()
        if times is None:
            return
        self._plot_data(values, times, title=f"{self.data_combo.currentText()} vs {self.time_column}")

    def on_derivative(self):
        times, values = self._get_data()
        if times is None:
            return
        
        if self.has_real_time:
            # Для временных данных
            if isinstance(times, pd.Series) and np.issubdtype(times.dtype, np.datetime64):
                values_series = pd.Series(values.values, index=pd.to_datetime(times))
                deriv = compute_derivative(values_series, method="time")
                self._plot_data(deriv.values, times, title=f"Производная {self.data_combo.currentText()}")
            else:
                QMessageBox.warning(self, "Ошибка", "Ошибка обработки временных данных")
        else:
            # Для последовательных измерений - производная по индексу
            deriv = compute_derivative(values, method="linear")
            self._plot_data(deriv, times, title=f"Производная {self.data_combo.currentText()}")

    def on_interpolate(self):
        times, values = self._get_data()
        if times is None:
            return
        
        if self.has_real_time:
            # Для временных данных
            if isinstance(times, pd.Series) and np.issubdtype(times.dtype, np.datetime64):
                values_series = pd.Series(values.values, index=pd.to_datetime(times))
                interpolated = interpolate_series(values_series, method="time")
                self._plot_data(interpolated.values, times, title=f"Интерполяция {self.data_combo.currentText()}")
            else:
                QMessageBox.warning(self, "Ошибка", "Ошибка обработки временных данных")
        else:
            # Для последовательных измерений - линейная интерполяция
            interpolated = interpolate_series(values, method="linear")
            self._plot_data(interpolated, times, title=f"Интерполяция {self.data_combo.currentText()}")

    def on_smooth(self):
        times, values = self._get_data()
        if times is None:
            return
        
        smoothed = smooth_series(values, window=5)
        self._plot_data(smoothed, times, title=f"Сглаживание {self.data_combo.currentText()}")
        
if __name__ == "__main__":
    app = QApplication()
    window = MyApp()
    window.show()
    app.exec()