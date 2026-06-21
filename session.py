from PySide6.QtWidgets import (QLabel, QTableView, QApplication, QMainWindow, QFileDialog, QMessageBox, 
                               QComboBox, QSpinBox, QPushButton, QWidget, QVBoxLayout, QHeaderView,                               
                               QHBoxLayout, QTabWidget, QTextEdit, QGroupBox, QGridLayout, QDialog,
                               QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QStandardItemModel, QStandardItem

import sys
import logging
import numpy as np
from typing import List, Dict, Tuple
from pyqtgraph.dockarea import Dock

# Configure logging to show solver progress
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

from ui.ui import Ui_MainWindow
from ui.compare_dialog import CompareDialog
from ui import ( 
    setup_dock_area, 
    plot_pressure, 
    plot_debit,
    plot_burde,
    clear_plot,
    plot_autosplit_line,
    PasteDataDialog,
    fill_state_to_ui,
    plot_reference_family,
    )
from ui.table_data_builder import (
    build_dimensional_dataframe,
    build_dimensionless_dataframe,
    update_data_table_view,
    clear_data_table,
)
import pyqtgraph as pg
from core.app_state import AppState
from core.reference_repo import ReferenceRepository
from config import settings
from solver.solver_wrapper import SolverResult
from solver import Solver
from solver.solver_worker import SolverWorker
from core.dimensionless import calculate_x, calculate_y
from utils import export_dataframe_to_csv, format_pydantic_error

# pydantic
from schemas import StaticParams
from schemas.optimize_thresholds import OptimizeThresholds
# модельки
from core.models import (DimensionlessData,
                         SolverState,
                         MainRefCurve,
                         NeighbourRefCurve,
                         ReferenceCurves,
                         RefStaticParams,
                         ProcessingOperationResult,
                         RuntimeSettings,
)                        
from helpers import (
    calculate_L_value, 
    calculate_k_value,
    copy_processing_data,
    )
from utils import get_file_suffix, get_filename, export_dataframe_to_csv
# загрузки данных
from processing.loaders import csv_loader, las_loader
from ui.report_service import ReportService
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
from processing.autosplit_service import apply_autosplit
from ui.autosplit_dialog import AutosplitDialog
from sessions import load_state, save_state


class SessionWidget(QWidget):
    solutions_ready = Signal(object)
    
    def __init__(self, session_number: int):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.app_state = AppState()
        self.report = ReportService(self.ui.text_report)
        self.logger = logging.getLogger(__name__)
        self._autosplit_info = None  # Информация о разделении КСД/КВД
        self.solver_thread = None # заготовки для вызова солвера при расчете параметров
        self.solver_worker = None
        self.ref_repo = ReferenceRepository(db_path=settings.REF_DATABASE_PATH)
        self.session_number = session_number
        # Заполняем комбобокс количества трещин из БД
        self._populate_N_combobox()
        
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
            self.ui.frac_amount_combobox,
            self.ui.compressibility_spinBox,
            self.ui.reservoir_pressure_spinbox,
            self.ui.insert_static_params_button,
        ]
        self._threshold_controls: List[QWidget] = [
            self.ui.frac_length_min_border_doubleSpinBox,
            self.ui.frac_length_max_border_doubleSpinBox,
            self.ui.permeability_min_border_doubleSpinBox,
            self.ui.permeability_max_border_doubleSpinBox,
            self.ui.misfit_threshold_doubleSpinBox,
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
        self.setup_dock_visibility_checkboxes()
        self.setup_preprocessing_controls()
        self.setup_data_table_elements()
        self.ui.add_settings_button.clicked.connect(self.on_runtime_settings_changed)
        # Создаем интерфейс с DockArea
        setup_dock_area(self)
    
    # ЗАПОЛНЕНИЕ КОМБОБОКСОВ
    def _populate_N_combobox(self):
        """Заполнить комбобокс количества трещин из БД."""
        try:
            n_values = self.ref_repo.get_available_N_values()
            self.ui.frac_amount_combobox.clear()
            for n in n_values:
                self.ui.frac_amount_combobox.addItem(str(n), n)
        except Exception as e:
            self.report.warning(f"Не удалось загрузить список N: {e}")

   
    ## РАЗДЕЛ ЗАГРУЗКИ ДИНАМИЧЕСКИХ ДАННЫХ
    def setup_load_dynamic_data_menu(self):
        self.ui.load_file_button.clicked.connect(self.load_dynamic_data_from_file)
        self.ui.reset_data_button.clicked.connect(self.reset_all_data)
        self.ui.insert_data_from_buffer_button.clicked.connect(self.insert_data_from_buffer)
        
        self.ui.export_session_btn.clicked.connect(self.export_session)
        self.ui.import_session_btn.clicked.connect(self.import_session)
            
    def insert_data_from_buffer(self):
        dialog = PasteDataDialog(self)
        if dialog.exec():
            try:
                raw = dialog.get_data()

                # Автосплиттер
                try:
                    split_info = get_split_info(raw.t, raw.P)
                except Exception as e:
                    self.report.warning(f"Ошибка автосплиттера: {e}")
                    split_info = None

                if split_info is not None:
                    try:
                        mode = AutosplitDialog.show_dialog(self, split_info)
                        if mode:
                            raw, msg, self._autosplit_info = apply_autosplit(raw, split_info, mode)
                            if msg:
                                self.report.info(msg)
                        else:
                            self._autosplit_info = None
                    except Exception as e:
                        self.report.error(f"Ошибка в диалоге автосплиттера: {e}")
                        self._autosplit_info = None
                else:
                    self._autosplit_info = None

                self.app_state.raw_dynamic_data = raw

                if self._autosplit_info is not None:
                    self._draw_autosplit_line()

                self.report.success("Динамические данные успешно вставлены из буфера.")

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
        
            # Автосплиттер
            try:
                split_info = get_split_info(raw_data.t, raw_data.P)
            except Exception as e:
                self.report.warning(f"Ошибка автосплиттера: {e}")
                split_info = None

            if split_info is not None:
                try:
                    mode = AutosplitDialog.show_dialog(self, split_info)
                    if mode:
                        raw_data, msg, self._autosplit_info = apply_autosplit(raw_data, split_info, mode)
                        if msg:
                            self.report.info(msg)
                    else:
                        self.report.info("Выбор отменен. Использованы все данные.")
                        self._autosplit_info = None
                except Exception as e:
                    self.report.error(f"Ошибка обработки разделения: {e}. Использованы все данные.")
                    self._autosplit_info = None
            else:
                self._autosplit_info = None
            
            self.app_state.raw_dynamic_data = raw_data
            
            file_name = get_filename(file_path=file_path)
            self.ui.load_file_label.setText(file_name)
            self.report.success(f"Динамические данные успешны загружены из файла {file_name}.")
            
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
    
    def export_session(self):
        if self.app_state.raw_dynamic_data is None:
            QMessageBox.warning(self, "Ошибка", "Нет данных для сохранения.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить сессию",
            "",
            "Flow Session (*.fflow)"
        )

        if not path:
            return

        try:
            save_state(self.app_state, path)
            self.report.success(f"Сессия сохранена: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{str(e)}")
    
    def import_session(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить сессию",
            "",
            "Flow Session (*.fflow)"
        )

        if not path:
            return

        try:
            self.app_state = load_state(path)
            # заполнение UI из state
            fill_state_to_ui(self.ui, self.app_state)

            # КРИТИЧНО: восстановление производных данных
            if self.app_state.processing_dynamic_data and self.app_state.static_params:
                self.recalculate_processing_dynamic_data()

            if self.app_state.processing_dynamic_data and self.app_state.solver_state:
                self.recalculate_dimensionless()

            # обновление UI
            self.refresh_ui()

            # включение нужных контролов
            self.disable_load_controls()

            if self.app_state.static_params:
                self.disable_static_controls()
                self.enable_threshold_controls()

            if self.app_state.optimize_thresholds:
                self.disable_threshold_controls()
                self.enable_calculation_controls()

            self.report.success(f"Сессия загружена: {path}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить:\n{str(e)}")
     
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
            "N": int(self.ui.frac_amount_combobox.currentText()),
            "P0": self.ui.reservoir_pressure_spinbox.value(),
        }

        if static_dict["P0"] < np.max(self.app_state.raw_dynamic_data.P):
            raise ValueError("Пластовое давление скважины должно быть больше всех значений ряда давления P. Проверьте параметр.")
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

        msg = (
            f"Статические параметры: W={static_params.W}, h={static_params.h}, "
            f"μ={static_params.mu}, φ={static_params.phi}, B={static_params.B}, "
            f"ct={static_params.ct}, N={static_params.N}, P0={static_params.P0}"
        )
        if static_params.Q_constant is not None:
            msg += f", Q={static_params.Q_constant}"

        # пересчитываем dP, burde, нормализацию Q — нужно всегда
        self.recalculate_processing_dynamic_data()

        if self.app_state.optimize_thresholds is not None:
            # границы уже введены — пересчитываем XY и обновляем графики/таблицу
            self.recalculate_dimensionless()
            self.refresh_ui()
            self.report.success(msg)
            self.report.success("Данные пересчитаны с новыми статическими параметрами. Проверьте графики и таблицу.")
        else:
            self.report.success(msg)
            self.report.success("Статические параметры сохранены. После ввода границ данные будут пересчитаны.")
    
        # self.disable_static_controls()
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
            "misfit_threshold": self.ui.misfit_threshold_doubleSpinBox.value(),
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
        
        self.report.success(
            f"Границы оптимизации: L [{thresholds.L_min}..{thresholds.L_max}] м, "
            f"k [{thresholds.k_min}..{thresholds.k_max}] мД, "
            f"misfit_threshold = {thresholds.misfit_threshold}"
        )
        self.report.success("Ввод данных успешен. Проверить динамические данные можете на вкладке 'Табличное представление'")
        self.refresh_ui() # обновление таблицы
        
        # self.disable_threshold_controls()
        self.enable_calculation_controls()
        
    ## Предобработка данных через UI
    def setup_preprocessing_controls(self):
        self.ui.interp_btn.clicked.connect(self.interpolate_processing_dynamic_data)
        self.ui.extrapolate_btn.clicked.connect(self.extrapolate_processing_dynamic_data)
        self.ui.ml_filter_btn.clicked.connect(self.smooth_processing_dynamic_data)
        self.ui.outlier_btn.clicked.connect(self.remove_outliers_in_processing_dynamic_data)
        self.ui.reset_plots_btn.clicked.connect(self.reset_preprocessing_dynamic_data)
        
    def interpolate_processing_dynamic_data(self):
        self._apply_preprocessing(
            extend_masks_to_time_grid,
            interpolate_pressure,
            interpolate_debit,
        )

    def extrapolate_processing_dynamic_data(self):
        self._apply_preprocessing(
            extrapolate_time,
            extend_masks_to_time_grid,
            extrapolate_pressure,
            extrapolate_debit,
        )

    def smooth_processing_dynamic_data(self):
        self._apply_preprocessing(smooth_pressure)

    def remove_outliers_in_processing_dynamic_data(self):
        self._apply_preprocessing(remove_pressure_outliers)
   
    def _apply_preprocessing(self, *actions):
        """
        Pipeline:
        data copy -> apply actions -> save -> recalc -> refresh UI

        Любая ошибка:
        - останавливает pipeline
        - пишет в report
        - показывает QMessageBox
        """

        import traceback

        processing = copy_processing_data(self.app_state.processing_dynamic_data)

        try:
            for action in actions:     
                result = action(processing)
                if isinstance(result, ProcessingOperationResult):
                    processing = result.data

                    for detail in result.details:
                        self.report.info(detail)

                # backward compatibility
                else:
                    processing = result

            self.app_state.processing_dynamic_data = processing

            self.recalculate_processing_dynamic_data()
            self.recalculate_dimensionless()

            self.refresh_ui()

        except Exception as e:

            action_name = getattr(
                action,
                "__name__",
                "unknown_operation",
            )

            error_text = (
                f"Ошибка предобработки "
                f"({action_name}): {str(e)}"
            )

            # UI report
            self.report.error(error_text)

            # developer log
            self.logger.error(
                error_text,
                exc_info=True,
            )
            # popup
            QMessageBox.critical(
                self,
                "Ошибка предобработки",
                error_text,
            )

            # optional full traceback
            traceback.print_exc()
            
    def reset_preprocessing_dynamic_data(self):
        self.app_state.processing_dynamic_data = raw_to_processing(self.app_state.raw_dynamic_data)
        self.recalculate_processing_dynamic_data()
        self.recalculate_dimensionless()
        self.refresh_ui()
        self.report.info(
            "\nПредобработка сброшена. Восстановлены исходные динамические данные.\n"
        )

    ## РАЗДЕЛ РАСЧЁТА ОПТИМАЛЬНЫХ ПАРАМЕТРОВ
    def calculate_optimal_parameters(self):
        """Execute the solver to find optimal S, k, L parameters."""
        self.sync_runtime_settings_from_ui()
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
            self.solver_thread = QThread()
            self.solver_worker = SolverWorker(self.app_state)

            self.solver_worker.moveToThread(self.solver_thread)

            self.solver_thread.started.connect(self.solver_worker.run)

            self.solver_worker.finished.connect(self._on_solver_done)
            self.solver_worker.error.connect(self._on_solver_error)

            self.solver_worker.finished.connect(self.solver_thread.quit)
            self.solver_worker.finished.connect(self.solver_worker.deleteLater)
            self.solver_thread.finished.connect(self.solver_thread.deleteLater)
            
            self.solver_thread.start()
            self.disable_load_controls()
            self.disable_static_controls()
            self.disable_threshold_controls()
            self.disable_calculation_controls()
            self.report.solver("Солвер запущен, идет расчет...")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка расчёта",
                f"Ошибка при оптимизации параметров:\n{str(e)}"
            )
            self.report.error(f"Ошибка солвера: {e}")
            
    def _on_solver_error(self, msg):
        QMessageBox.critical(self, "Ошибка расчёта", msg)
        self.report.error(f"Ошибка солвера: {msg}")
    
    def _on_solver_done(self, results):
        self.enable_load_controls()
        self.enable_static_controls()
        self.enable_threshold_controls()
        self.enable_calculation_controls()
        self.ui.calculate_opt_parameters_button.setEnabled(True)
        
        misfit_threshold = self.app_state.optimize_thresholds.misfit_threshold
        filtered = [r for r in results if r.error_value <= misfit_threshold]
        
        if not filtered:
            best_misfit = min(r.error_value for r in results) if results else float('inf')
            QMessageBox.warning(
                self,
                "Нет решения",
                f"Лучшее misfit = {best_misfit:.6f} превышает порог {misfit_threshold}.\n"
                "Проверьте параметры (длину скважины, кол-во трещин, диапазоны ограничений, порог misfit)."
            )
            return

        result: SolverResult = filtered[0]
        self.report.solver(
            f"Результат солвера получены. \n"
            f"Лучшее решение: \n"
            f"Skin-фактор: {result.S_opt};\n"
            f"Проницаемость k: {result.k_opt};\n"
            f"Полудлина трещины: {result.L_opt};\n"
            f"Misfit: {result.error_value:.6f} (порог: {misfit_threshold})."
        )
        
        self.ui.skin_result_spinbox.setValue(result.S_opt)
        self.ui.permeability_result_spinbox.setValue(result.k_opt)
        self.ui.frac_length_result_spinbox.setValue(result.L_opt)

        self.app_state.solver_state = SolverState(
            k_current=result.k_opt,
            L_current=result.L_opt,
            skin_current=result.S_opt,
            residual=result.error_value
        )

        self.recalculate_dimensionless()
        for i, r in enumerate(results):
            self._build_reference_curves(
                r,
                update_global=(i == 0)
            )

        self.update_dim_plots()

        dialog = CompareDialog(
            results,
            self.app_state,
            self,
            session_number=self.session_number,
        )

        dialog.exec() 
        self.solutions_ready.emit(results)
    
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
    
    # УПРАВЛЕНИЕ ВИДИМОСТЬЮ ДОКОВ
    def setup_dock_visibility_checkboxes(self):
        """Подключает чекбоксы к показу/скрытию доков."""
        self.ui.cb_pressure_dock.stateChanged.connect(
            lambda state: self._toggle_dock(self.ui.dock_pressure, state)
        )
        self.ui.cb_debit_dock.stateChanged.connect(
            lambda state: self._toggle_dock(self.ui.dock_debit, state)
        )
        self.ui.cb_calc_XY_dock.stateChanged.connect(
            lambda state: self._toggle_dock(self.ui.dock_xy, state)
        )
        self.ui.cb_burde_curve_dock.stateChanged.connect(
            lambda state: self._toggle_dock(self.ui.dock_burde, state)
        )

    def _toggle_dock(self, dock: Dock, state):
        """Показать/скрыть док по состоянию чекбокса."""
        from PySide6.QtCore import Qt
        if state == Qt.CheckState.Checked.value:
            dock.show()
        else:
            dock.hide()

    def _build_reference_curves(
        self,
        result: SolverResult,
        update_global: bool = False,
    ):
        """
        Собирает ReferenceCurves из результата солвера.
        """
        try:
            static_params = self.app_state.static_params
            N_fixed = static_params.N
            W_fixed = static_params.W
            skin_opt = result.S_opt
            L_opt = result.L_opt

            # Главная кривая
            main_dict = self.ref_repo.find_best_curve(
                skin_opt,
                L_opt,
                N=N_fixed,
                W=W_fixed
            )

            main_curve = None

            if main_dict is not None:
                main_curve = MainRefCurve(
                    dimensionless=DimensionlessData(
                        X=main_dict['X'],
                        Y=main_dict['Y'],
                    ),
                    static_params=RefStaticParams(
                        Skin=main_dict['Skin'],
                        h=main_dict['h'],
                        N=int(main_dict['N']),
                        W=main_dict['W'],
                        L=main_dict['L'],
                        aL=main_dict["aL"],
                    ),
                )

            # Соседи
            neighbors_list = self.ref_repo.find_neighbor_curves(
                skin_opt,
                L_opt,
                N=N_fixed,
                W=W_fixed
            )

            neighbours = []

            for nb in neighbors_list:

                skin_diff = nb['Skin'] - skin_opt
                skin_offset = int(round(skin_diff))

                neighbours.append(
                    NeighbourRefCurve(
                        dimensionless=DimensionlessData(
                            X=nb['X'],
                            Y=nb['Y'],
                        ),
                        skin_offset=skin_offset,
                    )
                )

            curves = ReferenceCurves(
                main=main_curve,
                neighbours=neighbours if neighbours else None,
            )

            # сохраняем ВНУТРЬ конкретного результата
            result.reference_curves = curves

            # обновляем главное окно только если нужно
            if update_global:
                self.app_state.reference_curves = curves

            return curves

        except Exception as e:

            result.reference_curves = None

            self.report.warning(
                f"Не удалось собрать референсные кривые: {e}"
            )

            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось собрать отображение референсных кривых!"
            )

            if update_global:
                self.app_state.reference_curves = None

            return None
            
    def refresh_ui(self):
        self.update_data_tables()
        self.update_dim_plots()
    
    def reset_ui(self):
        self.reset_plots()
        self.reset_data_tables()

    def update_data_tables(self):
        processing = self.app_state.processing_dynamic_data
        dimensionless = self.app_state.dimensionless
        if processing is not None:
            dimensional_df = build_dimensional_dataframe(processing)
            update_data_table_view(self.ui.dim_data_table, dimensional_df)
        else:
            clear_data_table(self.ui.dim_data_table)
        if dimensionless is not None:
            dimensionless_df = build_dimensionless_dataframe(dimensionless)
            update_data_table_view(self.ui.dimless_data_table, dimensionless_df)
        else:
            clear_data_table(self.ui.dimless_data_table)
        
    def setup_data_table_elements(self):
        self.ui.export_dim_data_table_btn.clicked.connect(self.export_dimensional_table)
        self.ui.export_dimless_data_table_btn.clicked.connect(self.export_dimensionless_table)
    
    def export_dimensional_table(self):
        processing = self.app_state.processing_dynamic_data
        if processing is None:
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить размерные данные",
            "",
            "CSV Files (*.csv)"
        )
        if not filepath:
            return
        df = build_dimensional_dataframe(processing)
        export_dataframe_to_csv(filepath, df)
    
    def export_dimensionless_table(self):
        dimensionless = self.app_state.dimensionless
        if dimensionless is None:
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить безразмерные данные",
            "",
            "CSV Files (*.csv)"
        )
        if not filepath:
            return
        df = build_dimensionless_dataframe(dimensionless)

        export_dataframe_to_csv(filepath,df,)
        
    def reset_data_tables(self):
        clear_data_table(self.ui.dim_data_table)
        clear_data_table(self.ui.dimless_data_table)
    
    def reset_plots(self):
        clear_plot(self.ui.plot_pressure)
        clear_plot(self.ui.plot_debit)
        clear_plot(self.ui.plot_xy)
        clear_plot(self.ui.plot_burde)

    def update_dim_plots(self):
        plot_pressure(
            plot=self.ui.plot_pressure,
            t=self.app_state.processing_dynamic_data.t,
            P=self.app_state.processing_dynamic_data.P,
            P_interpolated_mask=self.app_state.processing_dynamic_data.P_interpolated_mask,
            P_extrapolated_mask=self.app_state.processing_dynamic_data.P_extrapolated_mask,
            runtime_settings=self.app_state.runtime_settings,
        )
        plot_debit(
            plot=self.ui.plot_debit,
            t=self.app_state.processing_dynamic_data.t,
            Q=self.app_state.processing_dynamic_data.Q,
            Q_interpolated_mask=self.app_state.processing_dynamic_data.Q_interpolated_mask,
            Q_extrapolated_mask=self.app_state.processing_dynamic_data.Q_extrapolated_mask,
            runtime_settings=self.app_state.runtime_settings,
        )
        self.update_xy_plot()
        self.update_burde_plot()

    def update_xy_plot(self):
        """Перерисовка XY-дока: факт + опционально эталон + соседи."""
        plot_reference_family(
            plot=self.ui.plot_xy,
            factual_dimensionless=self.app_state.dimensionless,
            reference_curves=self.app_state.reference_curves,
            runtime_settings=self.app_state.runtime_settings,
        )

    def update_burde_plot(self):
        """Перерисовка дока Бурде."""
        plot: pg.PlotItem = self.ui.plot_burde
        plot.clear()
        if self.app_state.processing_dynamic_data and self.app_state.processing_dynamic_data.burde is not None:
            plot_burde(
                plot=plot,
                t=self.app_state.processing_dynamic_data.t,
                burde=self.app_state.processing_dynamic_data.burde,
                runtime_settings=self.app_state.runtime_settings,
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
            
            self.report.info(f"Отображена линия AUTO SPLIT: t={split_time:.2f}, P={split_pressure:.2f}")
        except Exception as e:
            self.report.warning(f"Не удалось отрисовать линию разделения: {e}")
    
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
        self.report.clear()
        self.reset_data_tables()
        self.reset_plots()
        self.ui.load_file_label.setText("Файл не загружен")
        
    def _init_solver_state(self):
        th = self.app_state.optimize_thresholds

        self.app_state.solver_state = SolverState(
            k_current=calculate_k_value(th.k_min, th.k_max),
            L_current=calculate_L_value(th.L_min, th.L_max),
            skin_current=-1,
            residual=-1
        )
        
    # ДОП. НАСТРОЙКИ
    def sync_runtime_settings_from_ui(self):
        rs = self.app_state.runtime_settings
        rs.downsample_threshold = self.ui.downsample_treshold_spinbox.value()
        rs.downsample_points_per_decade = self.ui.downsample_points_per_decade_spinbox.value()
        rs.overlap_percentage = self.ui.overlap_percantage_spinbox.value()

    def on_runtime_settings_changed(self):

        self.sync_runtime_settings_from_ui()
        print(self.app_state.runtime_settings.overlap_percentage)
        self.report.info("Runtime settings обновлены")
        try:
            self.refresh_ui()
        except:
            pass
