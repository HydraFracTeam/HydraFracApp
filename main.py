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
from ui import ( 
    setup_add_interface, 
    update_data_table_view, 
    clear_data_table,
    plot_pressure, 
    plot_debit,
    plot_xy,
    plot_burde,
    clear_plot,
    PasteDataDialog,
    )
import pyqtgraph as pg
from core.app_state import AppState
from storage.reference_repository import ReferenceCurveDBManager
from config import settings

# pydantic
from schemas import StaticParams
from schemas.optimize_thresholds import OptimizeThresholds
# модельки
from core.models import DimensionlessData, SolverState
# хелперы, расчеты
from core.dimensionless import calculate_x, calculate_y
from helpers import (
    calculate_L_value, 
    calculate_k_value,
    )
from utils import get_file_suffix, get_filename
from utils import format_pydantic_error
# загрузки данных
from processing.loaders import csv_loader, las_loader
from processing import (
    rebuild_processing_dynamic,
    interpolate_pressure,
    interpolate_debit,
    extrapolate_pressure,
    extrapolate_time,
    extrapolate_debit,
    extend_masks_to_time_grid,
    remove_pressure_outliers,
    smooth_pressure,
    )


class MyApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.app_state = AppState()
        self.ref_curve_db = ReferenceCurveDBManager(db_path=settings.REF_DATABASE_PATH)

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
        self.connect_graphic_checkboxes()
        self.setup_preprocessing_controls()
        # Создаем  интерфейс с вкладками
        setup_add_interface(self)

    
    ## РАЗДЕЛ ЗАГРУЗКИ ДИНАМИЧЕСКИХ ДАННЫХ
    def setup_load_dynamic_data_menu(self):
        self.ui.load_file_button.clicked.connect(self.load_dynamic_data_from_file)
        self.ui.reset_data_button.clicked.connect(self.reset_all_data)
        self.ui.insert_data_from_buffer_button.clicked.connect(self.insert_data_from_buffer)
            
    def insert_data_from_buffer(self):

        dialog = PasteDataDialog(self)

        if dialog.exec():

            try:
                raw = dialog.get_data()

                self.app_state.raw_dynamic_data = raw

                self.show_in_text_report(
                    "Динамические данные успешно вставлены из буфера."
                )

                self.enable_static_controls()
                self.disable_load_controls()

            except Exception as e:

                QMessageBox.warning(
                    self,
                    "Ошибка данных",
                    format_pydantic_error(e)
                )
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

    def read_static_from_ui(self):
        static_dict = {
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
        if not self.app_state.raw_dynamic_data.is_Q_in_dynamic_input:
            static_dict["Q_constant"] = self.ui.debit_doubleSpinBox.value()
        
        return StaticParams(**static_dict)
        
    def get_static_params(self):
        raw = self.app_state.raw_dynamic_data
        if raw is None:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите динамические данные.")
            return

        try:
            static_params = self.read_static_from_ui()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка ввода параметров",
                format_pydantic_error(e)
            )
            return
        
        self.app_state.static_params = static_params
        # пересчитываем дебит для вводных данных после валидации статики
        if not raw.is_Q_in_dynamic_input and static_params.Q_constant is not None: # заходим, только если создали Q_constant ранее
            self.app_state.raw_dynamic_data.Q = np.full(
                len(self.app_state.raw_dynamic_data.t),
                static_params.Q_constant,
                dtype=float
            )

        self.show_in_text_report("Статические параметры успешно введены.")
    
        self.disable_static_controls()
        self.enable_threshold_controls()

    ## РАЗДЕЛ ГРАНИЦ ОПТИМИЗАЦИИ
    def setup_threshold_menu(self):
        self.ui.insert_thresholds_button.clicked.connect(self.get_thresholds)
        
    def read_thresholds_from_ui(self) -> OptimizeThresholds:

        optimize_dict = {
            "L_min": self.ui.frac_length_min_border_doubleSpinBox.value(),
            "L_max": self.ui.frac_length_max_border_doubleSpinBox.value(),
            "k_min": self.ui.permeability_min_border_doubleSpinBox.value(),
            "k_max": self.ui.permeability_max_border_doubleSpinBox.value(),
        }

        return OptimizeThresholds(**optimize_dict)
   
        
    def get_thresholds(self):

        if self.app_state.static_params is None:
            QMessageBox.warning(self, "Ошибка", "Сначала введите статические параметры.")
            return

        try:
            thresholds = self.read_thresholds_from_ui()

        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка ввода границ",
                format_pydantic_error(e)
            )
            return

        # считаем начальные значения для k и L
        self.app_state.optimize_thresholds = thresholds
        
        # создаем объект solver_state с начальными значениями
        self._init_solver_state()
        
        # сохраняем динамические данные для работы
        self.recalculate_processing_dynamic_data()
        
        # расчитаем промежуточные XY после ввода
        self.recalculate_dimensionless()
        
        self.show_in_text_report("Границы оптимизации успешно заданы.")
        self.refresh_ui() # обновление таблицы
        self.show_in_text_report("Ввод данных успешен. Проверить динамические данные можете на вкладке 'Табличное представление'")
        
        self.disable_threshold_controls()
        self.enable_calculation_controls()
        
    ## Предобработка данных через UI
    def setup_preprocessing_controls(self):
        self.ui.interp_btn.clicked.connect(self.interpolate_processing_dynamic_data)
        self.ui.extrapolate_btn.clicked.connect(self.extrapolate_processing_dynamic_data)
        self.ui.ml_filter_btn.clicked.connect(self.smooth_processing_dynamic_data)
        self.ui.outlier_btn.clicked.connect(self.remove_outliers_in_processing_dynamic_data)
        
    def interpolate_processing_dynamic_data(self):
        from copy import deepcopy
        processing = deepcopy(self.app_state.processing_dynamic_data)
        processing = extend_masks_to_time_grid(processing)
        processing = interpolate_pressure(processing)
        processing = interpolate_debit(processing)
        
        self.app_state.processing_dynamic_data = processing
        self.recalculate_processing_dynamic_data()
        self.recalculate_dimensionless()
        self.refresh_ui()
    
    def extrapolate_processing_dynamic_data(self):
        from copy import deepcopy
        processing = deepcopy(self.app_state.processing_dynamic_data)
        processing = extrapolate_time(processing)
        processing = extend_masks_to_time_grid(processing)
        processing = extrapolate_pressure(processing)
        processing = extrapolate_debit(processing)
        
        self.app_state.processing_dynamic_data = processing
        self.recalculate_processing_dynamic_data()
        self.recalculate_dimensionless()
        self.refresh_ui()
    
    def smooth_processing_dynamic_data(self):
        from copy import deepcopy
        processing = deepcopy(self.app_state.processing_dynamic_data)
        processing = smooth_pressure(processing)
        
        self.app_state.processing_dynamic_data = processing
        
        self.recalculate_processing_dynamic_data()
        self.recalculate_dimensionless()
        self.refresh_ui()
    
    def remove_outliers_in_processing_dynamic_data(self):
        from copy import deepcopy
        processing = deepcopy(self.app_state.processing_dynamic_data)
        processing = remove_pressure_outliers(processing)
        
        self.app_state.processing_dynamic_data = processing
        
        self.recalculate_processing_dynamic_data()
        self.recalculate_dimensionless()
        self.refresh_ui()
    
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
    
    # ОБНОВЛЕНИЕ ГРАФИКОВ, ТАБЛИЦ
    def connect_graphic_checkboxes(self):
        self.ui.cb_calc_XY.stateChanged.connect(self.update_dimensionless_plot)
        self.ui.cb_burde_curve.stateChanged.connect(self.update_dimensionless_plot)
    
    def refresh_ui(self):
        self.update_data_table()
        self.update_dim_plots()
        self.update_dimensionless_plot()
    

    def update_data_table(self):
        update_data_table_view(
            table_view=self.ui.data_table,
            processing=self.app_state.processing_dynamic_data,
            dimensionless=self.app_state.dimensionless,
        )
        
    def reset_data_table(self):
        clear_data_table(self.ui.data_table)
    
    def update_dim_plots(self):
        plot_pressure(
            plot = self.ui.p_graphic,
            t = self.app_state.processing_dynamic_data.t,
            P = self.app_state.processing_dynamic_data.P,
            P_interpolated_mask=self.app_state.processing_dynamic_data.P_interpolated_mask,
            P_extrapolated_mask=self.app_state.processing_dynamic_data.P_extrapolated_mask,
        )
        plot_debit(
            plot = self.ui.q_graphic,
            t = self.app_state.processing_dynamic_data.t,
            Q = self.app_state.processing_dynamic_data.Q,
            Q_interpolated_mask=self.app_state.processing_dynamic_data.Q_interpolated_mask,
            Q_extrapolated_mask=self.app_state.processing_dynamic_data.Q_extrapolated_mask,
        )

    
    def reset_dim_plots(self):
        clear_plot(self.ui.p_graphic)
        clear_plot(self.ui.q_graphic)
    
    def update_dimensionless_plot(self):

        plot: pg.PlotItem = self.ui.dim_plot
        plot.clear()

        if self.ui.cb_calc_XY.isChecked():
            if not self.app_state.dimensionless:
                return

            plot_xy(
                plot=plot,
                X=self.app_state.dimensionless.X,
                Y=self.app_state.dimensionless.Y,
            )

        if self.ui.cb_burde_curve.isChecked():
            if not self.app_state.processing_dynamic_data:
                return

            plot_burde(
                plot=plot,
                t=self.app_state.processing_dynamic_data.t,
                burde=self.app_state.processing_dynamic_data.burde,
            )
    
    ## ВЫЗОВ РАСЧЕТОВ
    def recalculate_dimensionless(self):
        dyn = self.app_state.processing_dynamic_data
        static = self.app_state.static_params
        solver = self.app_state.solver_state

        self.app_state.dimensionless = DimensionlessData(
            X=calculate_x(
                delta_p=dyn.dP,
                k=solver.k_current,
                h=static.h,
                mu=static.mu,
                B=static.B,
                Q=dyn.Q,
            ),

            Y=calculate_y(
                Q=dyn.Q,
                t=dyn.t,
                B=static.B,
                delta_p=dyn.dP,
                phi=static.phi,
                ct=static.ct,
                h=static.h,
                L=solver.L_current,
            )
        )
        
    def recalculate_processing_dynamic_data(self):
        raw = self.app_state.raw_dynamic_data
        static = self.app_state.static_params
        dyn = self.app_state.processing_dynamic_data
        
        self.app_state.processing_dynamic_data = rebuild_processing_dynamic(
            raw_data=raw,
            static_data=static,
            current_processing_data=dyn,
        )
    
        
        
    ## ПРОЧЕЕ / ВСПОМОГАТЕЛЬНОЕ
    def reset_all_data(self):
        self.app_state = AppState()
        self.enable_load_controls()
        self.disable_static_controls()
        self.disable_threshold_controls()
        self.disable_calculation_controls()
        self.ui.text_report.clear()
        self.reset_data_table()
        self.reset_dim_plots()
        self.ui.load_file_label.setText("Файл не загружен")
            
    def show_in_text_report(self, text: str) -> None:
        self.ui.text_report.append(text)
    
    def _init_solver_state(self):
        th = self.app_state.optimize_thresholds

        self.app_state.solver_state = SolverState(
            k_current=calculate_k_value(th.k_min, th.k_max),
            L_current=calculate_L_value(th.L_min, th.L_max),
            skin_current=-1,
            residual=-1
        )
    
            

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())
