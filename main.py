from PySide6.QtWidgets import (QLabel, QTableView, QApplication, QMainWindow, QFileDialog, QMessageBox, 
                               QComboBox, QSpinBox, QPushButton, QWidget, QVBoxLayout, QHeaderView,                               
                               QHBoxLayout, QTabWidget, QTextEdit, QGroupBox, QGridLayout, QDialog,
                               QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem

import sys
import logging
import numpy as np
from typing import List, Dict, Tuple

# Configure logging to show solver progress
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

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
    plot_autosplit_line,
    export_processing_to_csv,
    PasteDataDialog,
    )
import pyqtgraph as pg
from core.app_state import AppState
from storage.reference_repository import ReferenceCurveDBManager
from config import settings
from solver import Solver
from core.dimensionless import calculate_x, calculate_y
from utils import format_pydantic_error

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
    raw_to_processing,
    )
from processing.autosplitter import get_split_info
from ui.autosplit_dialog import AutosplitDialog



class MyApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.app_state = AppState()
        self.ref_curve_db = ReferenceCurveDBManager(db_path=settings.REF_DATABASE_PATH)
        self.logger = logging.getLogger(__name__)
        self._autosplit_info = None  # Информация о разделении КСД/КВД
        
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
        self.setup_data_table_elements()
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
                
                # Проверка на автосплиттер
                try:
                    split_info = get_split_info(raw.t, raw.P)
                except Exception as e:
                    self.logger.warning(f"Ошибка автосплиттера: {e}")
                    split_info = None
                
                if split_info is not None:
                    try:
                        # Показываем диалог выбора
                        mode = AutosplitDialog.show_dialog(self, split_info)
                        
                        if mode == AutosplitDialog.MODE_KSD:
                            split_idx = split_info.get('index', len(raw.t) // 2)
                            raw.t = raw.t[:split_idx]
                            raw.P = raw.P[:split_idx]
                            # Проверяем Q перед срезом
                            if hasattr(raw, 'Q') and raw.Q is not None:
                                raw.Q = raw.Q[:split_idx]
                            self.show_in_text_report(
                                f"Выбран режим КСД: использованы точки 0-{split_idx}"
                            )
                        elif mode == AutosplitDialog.MODE_KVD:
                            split_idx = split_info.get('index', len(raw.t) // 2)
                            raw.t = raw.t[split_idx:]
                            raw.P = raw.P[split_idx:]
                            # Проверяем Q перед срезом
                            if hasattr(raw, 'Q') and raw.Q is not None:
                                raw.Q = raw.Q[split_idx:]
                            self.show_in_text_report(
                                f"Выбран режим КВД: использованы точки {split_idx}-end"
                            )
                        elif mode == AutosplitDialog.MODE_BOTH:
                            self.show_in_text_report(
                                f"⚠ Использованы все данные (КСД + КВД). "
                                f"Подбор может быть некорректным!"
                            )
                            self._autosplit_info = split_info
                        elif mode == AutosplitDialog.MODE_IGNORE:
                            self.show_in_text_report("Автосплиттер отключен.")
                            self._autosplit_info = None
                        else:
                            self._autosplit_info = None
                    except Exception as e:
                        self.logger.error(f"Ошибка в диалоге автосплиттера: {e}")
                        self._autosplit_info = None
                else:
                    self._autosplit_info = None

                self.app_state.raw_dynamic_data = raw
                
                # Отображаем линию разделения если есть
                if self._autosplit_info is not None:
                    self._draw_autosplit_line()

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
        
            # Проверка на автосплиттер
            try:
                split_info = get_split_info(raw_data.t, raw_data.P)
            except Exception as e:
                self.logger.warning(f"Ошибка автосплиттера: {e}")
                split_info = None
            
            if split_info is not None:
                try:
                    # Показываем диалог выбора
                    mode = AutosplitDialog.show_dialog(self, split_info)
                    
                    if mode == AutosplitDialog.MODE_KSD:
                        # Оставляем только КСД (до точки разделения)
                        split_idx = split_info.get('index', len(raw_data.t) // 2)
                        raw_data.t = raw_data.t[:split_idx]
                        raw_data.P = raw_data.P[:split_idx]
                        # Проверяем Q перед срезом
                        if hasattr(raw_data, 'Q') and raw_data.Q is not None:
                            raw_data.Q = raw_data.Q[:split_idx]
                        self.show_in_text_report(
                            f"Выбран режим КСД: использованы точки 0-{split_idx} "
                            f"(t < {split_info.get('time', 0):.2f})"
                        )
                        
                    elif mode == AutosplitDialog.MODE_KVD:
                        # Оставляем только КВД (после точки разделения)
                        split_idx = split_info.get('index', len(raw_data.t) // 2)
                        raw_data.t = raw_data.t[split_idx:]
                        raw_data.P = raw_data.P[split_idx:]
                        # Проверяем Q перед срезом
                        if hasattr(raw_data, 'Q') and raw_data.Q is not None:
                            raw_data.Q = raw_data.Q[split_idx:]
                        self.show_in_text_report(
                            f"Выбран режим КВД: использованы точки {split_idx}-{len(raw_data.t) + split_idx} "
                            f"(t >= {split_info.get('time', 0):.2f})"
                        )
                        
                    elif mode == AutosplitDialog.MODE_BOTH:
                        # Оставляем все, но показываем предупреждение
                        self.show_in_text_report(
                            f"⚠ Предупреждение: использованы все данные (КСД + КВД). "
                            f"Точка разделения: t = {split_info.get('time', 0):.2f}. "
                            f"Подбор параметров может быть некорректным!"
                        )
                        # Сохраняем инфо о разделении для визуализации
                        self._autosplit_info = split_info
                        
                    elif mode == AutosplitDialog.MODE_IGNORE:
                        # Игнорируем разделение
                        self.show_in_text_report("Автосплиттер отключен. Использованы все данные.")
                        self._autosplit_info = None
                        
                    else:
                        # Диалог закрыт без выбора - используем все данные
                        self.show_in_text_report("Выбор отменен. Использованы все данные.")
                        self._autosplit_info = None
                except Exception as e:
                    self.logger.error(f"Ошибка в диалоге автосплиттера: {e}", exc_info=True)
                    self.show_in_text_report(f"Ошибка обработки разделения: {e}. Использованы все данные.")
                    self._autosplit_info = None
            else:
                self._autosplit_info = None
            
            self.app_state.raw_dynamic_data = raw_data
            
            file_name = get_filename(file_path=file_path)
            self.ui.load_file_label.setText(file_name)
            self.show_in_text_report(f"Динамические данные успешны загружены из файла {file_name}.")
            
            # Отображаем линию разделения на графике если есть
            if hasattr(self, '_autosplit_info') and self._autosplit_info is not None:
                self._draw_autosplit_line()
            
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
        self.ui.calculate_opt_parameters_button.clicked.connect(self.calculate_optimal_parameters)
        
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
        self.ui.reset_plots_btn.clicked.connect(self.reset_preprocessing_dynamic_data)
        
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
    
    def reset_preprocessing_dynamic_data(self):
        self.app_state.processing_dynamic_data = raw_to_processing(self.app_state.raw_dynamic_data)
        self.recalculate_processing_dynamic_data()
        self.recalculate_dimensionless()
        self.refresh_ui()
    
    
    ## РАЗДЕЛ РАСЧЁТА ОПТИМАЛЬНЫХ ПАРАМЕТРОВ
    def calculate_optimal_parameters(self):
        """Execute the solver to find optimal S, k, L parameters."""
        # Проверяем наличие всех необходимых данных
        if self.app_state.processing_dynamic_data is None:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите и обработайте динамические данные.")
            return
        
        if self.app_state.static_params is None:
            QMessageBox.warning(self, "Ошибка", "Сначала введите статические параметры.")
            return
            
        if self.app_state.optimize_thresholds is None:
            QMessageBox.warning(self, "Ошибка", "Сначала задайте границы оптимизации.")
            return
        
        try:
            # Get data from app state
            dynamic_data = self.app_state.processing_dynamic_data
            static_params = self.app_state.static_params
            thresholds = self.app_state.optimize_thresholds
            
            # Calculate dimensionless parameters
            # We need to estimate initial k and L for X, Y calculation
            # Use middle of bounds as initial estimate
            k_init = (thresholds.k_min + thresholds.k_max) / 2
            L_init = (thresholds.L_min + thresholds.L_max) / 2
            
            x_fact = calculate_x(
                k=k_init,
                h=static_params.h,
                delta_p=dynamic_data.dP,
                mu=static_params.mu,
                B=static_params.B,
                Q=dynamic_data.Q,
            )
            
            y_fact = calculate_y(
                Q=dynamic_data.Q,
                B=static_params.B,
                t=dynamic_data.t,
                phi=static_params.phi,
                ct=static_params.ct,
                h=static_params.h,
                delta_p=dynamic_data.dP,
                L=L_init,
            )

            # Ensure positive values for log-scale processing
            mask = (x_fact > 0) & (y_fact > 0)
            x_fact = x_fact[mask]
            y_fact = y_fact[mask]
            
            if len(x_fact) < 10:
                QMessageBox.warning(
                    self, 
                    "Ошибка", 
                    "Недостаточно данных для расчёта. Проверьте входные данные."
                )
                return
            
            # Store dimensionless data in app state
            from core.models import DimensionlessData
            self.app_state.dimensionless = DimensionlessData(X=x_fact, Y=y_fact)
            
            # Run solver
            self.show_in_text_report("Запуск оптимизации...")
            solver = Solver()
            
            result = solver.solve_from_dimensionless(
                x_fact=x_fact,
                y_fact=y_fact,
                W_fixed=static_params.W,
                h_known=static_params.h,
                N_fixed=static_params.N if static_params.N > 0 else None,
                k_bounds=(thresholds.k_min, thresholds.k_max),
                L_bounds=(thresholds.L_min, thresholds.L_max),
                beam_width=5,
            )
            
            # Update UI with results
            self.ui.skin_result_spinbox.setValue(result.S_opt)
            self.ui.permeability_result_spinbox.setValue(result.k_opt)
            self.ui.frac_length_result_spinbox.setValue(result.L_opt)
            
            # Store result in app state
            from core.models import SolverState
            self.app_state.solver_state = SolverState(
                k_current=result.k_opt,
                L_current=result.L_opt,
                skin_current=result.S_opt,
                residual=result.error_value
            )
            
            self.show_in_text_report(
                f"Оптимизация завершена:\n"
                f"  Скин-фактор S = {result.S_opt:.4f}\n"
                f"  Проницаемость k = {result.k_opt:.6f} мД\n"
                f"  Полудлина трещины L = {result.L_opt:.4f} м\n"
                f"  Ошибка подбора = {result.error_value:.6f}"
            )
            
            # Refresh the plot to show reference curves if checkboxes are already checked
            self.update_dimensionless_plot()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка расчёта",
                f"Ошибка при оптимизации параметров:\n{str(e)}"
            )
            self.logger.error(f"Solver error: {e}", exc_info=True)
    
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
        self.ui.cb_main_ref_XY.stateChanged.connect(self.update_dimensionless_plot)
        self.ui.cb_neighbours_ref_XY.stateChanged.connect(self.update_dimensionless_plot)

    def _find_best_reference_curve(self, k_opt: float, L_opt: float, skin_opt: float, N_fixed: int = None, W_fixed: float = None):
        """
        Find the best matching reference curve based on optimization results.
        
        Args:
            k_opt: Optimized permeability
            L_opt: Optimized half-length
            skin_opt: Optimized skin factor
            N_fixed: Number of fractures (optional)
            W_fixed: Well length (optional)
            
        Returns:
            dict with 'X', 'Y', 'Skin', 'L' keys or None if not found
        """
        from core.reference_repo import ReferenceRepository
        from config import settings
        
        try:
            repo = ReferenceRepository(db_path=settings.REF_DATABASE_PATH)
            
            # Get available skins
            available_skins = repo.get_available_skins()
            
            if not available_skins:
                return None
            
            # Find closest skin value
            closest_skin = min(available_skins, key=lambda x: abs(x - skin_opt))
            
            # Get curves for this skin
            curve_ids = repo.get_curves_by_skin(closest_skin)
            
            if not curve_ids:
                return None
            
            # Get all static data to find best match for L
            conn = repo._get_connection()
            cursor = conn.cursor()
            
            best_curve = None
            best_diff = float('inf')
            
            for curve_id in curve_ids:
                cursor.execute(
                    "SELECT Skin, L, W, h, N FROM statics WHERE curve_id = ?",
                    (curve_id,)
                )
                row = cursor.fetchone()
                if row:
                    # Apply N and W filtering if provided
                    if N_fixed is not None and row['N'] != N_fixed:
                        continue
                    if W_fixed is not None and row['W'] != W_fixed:
                        continue
                    
                    # Calculate difference in L
                    diff = abs(row['L'] - L_opt)
                    if diff < best_diff:
                        best_diff = diff
                        best_curve = {
                            'curve_id': curve_id,
                            'Skin': row['Skin'],
                            'L': row['L'],
                            'W': row['W'],
                            'h': row['h'],
                            'N': row['N'],
                        }
            
            repo._close_connection()
            
            if best_curve:
                # Get X, Y data
                X, Y = repo.get_reference_curve(best_curve['curve_id'])
                best_curve['X'] = X
                best_curve['Y'] = Y
                
            return best_curve
            
        except Exception as e:
            self.logger.error(f"Error finding reference curve: {e}")
            return None

    def _find_neighbor_reference_curves(self, k_opt: float, L_opt: float, skin_opt: float, N_fixed: int = None, W_fixed: float = None):
        """
        Find neighbor reference curves: 2 with skin-1 and skin-2, and 2 with skin+1 and skin+2.
        Uses the same k and L parameters.
        
        Args:
            k_opt: Optimized permeability
            L_opt: Optimized half-length
            skin_opt: Optimized skin factor
            N_fixed: Number of fractures (optional)
            W_fixed: Well length (optional)
            
        Returns:
            List of dicts with 'X', 'Y', 'Skin', 'L' keys
        """
        from core.reference_repo import ReferenceRepository
        from config import settings
        
        neighbors = []
        
        try:
            repo = ReferenceRepository(db_path=settings.REF_DATABASE_PATH)
            
            # Get available skins
            available_skins = repo.get_available_skins()
            
            if not available_skins:
                return neighbors
            
            # Find skin values for neighbors: skin-2, skin-1, skin+1, skin+2
            skin_offsets = [-2, -1, 1, 2]
            target_skins = [skin_opt + offset for offset in skin_offsets]
            
            conn = repo._get_connection()
            cursor = conn.cursor()
            
            for target_skin in target_skins:
                # Find closest available skin to target
                closest_skin = min(available_skins, key=lambda x: abs(x - target_skin)) if available_skins else None
                
                if closest_skin is not None:
                    # Build query with optional N and W filtering
                    query = "SELECT curve_id, Skin, L, W, h, N FROM statics WHERE ABS(Skin - ?) < 0.001"
                    params = [target_skin]
                    
                    if N_fixed is not None:
                        query += " AND N = ?"
                        params.append(N_fixed)
                    if W_fixed is not None:
                        query += " AND W = ?"
                        params.append(W_fixed)
                    
                    query += " ORDER BY ABS(L - ?) LIMIT 1"
                    params.append(L_opt)
                    
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    if row:
                        # Check if we already have this skin in neighbors
                        skin_already_added = any(n['Skin'] == row['Skin'] for n in neighbors)
                        if not skin_already_added:
                            X, Y = repo.get_reference_curve(row['curve_id'])
                            neighbors.append({
                                'curve_id': row['curve_id'],
                                'X': X,
                                'Y': Y,
                                'Skin': row['Skin'],
                                'L': row['L'],
                                'W': row['W'],
                                'h': row['h'],
                                'N': row['N'],
                            })
            
            repo._close_connection()
            
        except Exception as e:
            self.logger.error(f"Error finding neighbor curves: {e}")
        
        return neighbors
    
    def refresh_ui(self):
        self.update_data_table()
        self.update_dim_plots()
        self.update_dimensionless_plot()
    
    def reset_ui(self):
        self.reset_plots()
        self.reset_data_table()

    def update_data_table(self):
        update_data_table_view(
            table_view=self.ui.data_table,
            processing=self.app_state.processing_dynamic_data,
            dimensionless=self.app_state.dimensionless,
        )
    
    def setup_data_table_elements(self):
        self.ui.export_data_table_btn.clicked.connect(self.export_data_table)
    
    def export_data_table(self):

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить данные",
            "",
            "CSV Files (*.csv)"
        )

        if not filepath:
            return

        export_processing_to_csv(
            filepath=filepath,
            processing=self.app_state.processing_dynamic_data,
            dimensionless=self.app_state.dimensionless,
        )
        
    def reset_data_table(self):
        clear_data_table(self.ui.data_table)
    
    def reset_plots(self):
        clear_plot(self.ui.p_graphic)
        clear_plot(self.ui.q_graphic)
        clear_plot(self.ui.dim_plot)
    
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
        
        # Get optimization results if available
        solver_state = self.app_state.solver_state
        k_opt = solver_state.k_current if solver_state else None
        L_opt = solver_state.L_current if solver_state else None
        skin_opt = solver_state.skin_current if solver_state else None
        
        # Get static params for N and W filtering
        static_params = self.app_state.static_params
        N_fixed = static_params.N if static_params else None
        W_fixed = static_params.W if static_params else None
        
        # Plot main reference curve (if checkbox is checked and we have optimization results)
        if self.ui.cb_main_ref_XY.isChecked() and k_opt and L_opt and skin_opt:
            ref_curve = self._find_best_reference_curve(k_opt, L_opt, skin_opt, N_fixed, W_fixed)
            if ref_curve:
                self._plot_reference_curve(
                    plot=plot,
                    X=ref_curve['X'],
                    Y=ref_curve['Y'],
                    skin=ref_curve['Skin'],
                    L=ref_curve['L'],
                    color=(255, 0, 0),
                    name=f"Эталонная кривая (S={ref_curve['Skin']:.1f}, L={ref_curve['L']:.1f})",
                )
        
        # Plot neighbor reference curves (if checkbox is checked and we have optimization results)
        if self.ui.cb_neighbours_ref_XY.isChecked() and k_opt and L_opt and skin_opt:
            neighbors = self._find_neighbor_reference_curves(k_opt, L_opt, skin_opt, N_fixed, W_fixed)
            # Colors for 4 neighbors: Skin-2, Skin-1, Skin+1, Skin+2
            neighbor_colors = [
                (0, 150, 0),    # Skin-2 - dark green
                (0, 200, 100),  # Skin-1 - light green
                (200, 150, 0),  # Skin+1 - orange
                (200, 50, 50),  # Skin+2 - red-orange
            ]
            for i, neighbor in enumerate(neighbors):
                if i < len(neighbor_colors):
                    color = neighbor_colors[i]
                else:
                    color = (150, 150, 150)  # gray for additional
                
                # Determine name suffix based on skin relative to optimal
                if neighbor['Skin'] < skin_opt:
                    skin_diff = int(skin_opt - neighbor['Skin'])
                    name_suffix = f"(Skin-{skin_diff})"
                else:
                    skin_diff = int(neighbor['Skin'] - skin_opt)
                    name_suffix = f"(Skin+{skin_diff})"
                    
                self._plot_reference_curve(
                    plot=plot,
                    X=neighbor['X'],
                    Y=neighbor['Y'],
                    skin=neighbor['Skin'],
                    L=neighbor['L'],
                    color=color,
                    name=f"Сосед {name_suffix} (S={neighbor['Skin']:.1f}, L={neighbor['L']:.1f})",
                )

    def _plot_reference_curve(self, plot: pg.PlotItem, X: np.ndarray, Y: np.ndarray, 
                               skin: float, L: float, color: tuple, name: str):
        """
        Plot a reference curve on the dimensionless plot.
        
        Args:
            plot: The plot item to draw on
            X: X coordinates of the reference curve
            Y: Y coordinates of the reference curve
            skin: Skin factor value
            L: Half-length value
            color: RGB color tuple
            name: Name for the legend
        """
        import pyqtgraph as pg
        
        mask = np.isfinite(X) & np.isfinite(Y)
        
        if not mask.any():
            return
        
        plot.plot(
            X[mask],
            Y[mask],
            pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine),
            name=name,
        )
    
    # АВТОСПЛИТТЕР
    def _draw_autosplit_line(self):
        """Отрисовка линии разделения КСД/КВД на графике давления."""
        if not hasattr(self, '_autosplit_info') or self._autosplit_info is None:
            return
        
        try:
            split_time = self._autosplit_info.get('time')
            split_pressure = self._autosplit_info.get('pressure')
            
            if split_time is None or split_pressure is None:
                return
            
            # Получаем график давления
            plot = self.ui.p_graphic
            if plot is None:
                return
            
            plot_autosplit_line(
                plot=self.ui.p_graphic,
                split_time=split_time,
                split_pressure=split_pressure,
            )
            
            self.logger.info(f"Отображена линия AUTO SPLIT: t={split_time:.2f}, P={split_pressure:.2f}")
        except Exception as e:
            self.logger.warning(f"Не удалось отрисовать линию разделения: {e}")
    
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
    def reset_all_data(self): # сброс всех данных
        self.app_state = AppState()
        self.enable_load_controls()
        self.disable_static_controls()
        self.disable_threshold_controls()
        self.disable_calculation_controls()
        self.ui.text_report.clear()
        self.reset_data_table()
        self.reset_plots()
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
