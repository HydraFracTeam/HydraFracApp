from PySide6.QtWidgets import (QLabel, QTableView, QApplication, QMainWindow, QFileDialog, QMessageBox, 
                               QComboBox, QSpinBox, QPushButton, QWidget, QVBoxLayout, 
                               QHBoxLayout, QTabWidget, QTextEdit, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem

import sys
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple, Any

from ui import Ui_mainWindow

from helpers.parse_well_data import parse_well_data
from helpers.ml_methods import (apply_ml_interpolation, apply_ml_filter, 
                               detect_outliers)
from helpers.dimensionless_analysis import convert_to_dimensionless_curves
from helpers.dimensionless_plotting import plot_dimensionless_grouped
from helpers.dimensionless_interpolating import DimensionlessCurveInterpolator
from schemas.well_data import WellTimeSeries
from helpers.ui_setup import (
    setup_professional_interface,
    setup_timeseries_tab,
    setup_grp_tab,
    setup_type_curves_tab,
    setup_results_tab,
    setup_data_tab
)

# Импорт констант из config.py
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    TAB_WIDGET_X, TAB_WIDGET_Y, TAB_WIDGET_WIDTH, TAB_WIDGET_HEIGHT, LEFT_PANEL_MAX_WIDTH,
    RMSE_EXCELLENT_THRESHOLD, RMSE_GOOD_THRESHOLD,
    DEFAULT_K, DEFAULT_MU, DEFAULT_B, DEFAULT_PHI, DEFAULT_C_T,
    DEFAULT_OUTLIER_THRESHOLD, DEFAULT_SAVGOL_WINDOW_LENGTH, DEFAULT_SAVGOL_POLYORDER,
    N_PARAMETERS_PER_POINT, REPORT_SEPARATOR_LENGTH,
    TYPE_CURVE_N_POINTS, TYPE_CURVE_TIME_MIN, TYPE_CURVE_TIME_MAX,
    INTERPOLATION_METHODS
)



class MyApp(QMainWindow, Ui_mainWindow):
    def __init__(self, test_mode: bool = False) -> None:
        super().__init__()
        self.setupUi(self)
        
        self.test_mode = test_mode  # Флаг для отключения сообщений в тестах
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        # Переименуем существующую кнопку и подключим обработчик
        try:
            self.load_template_button.setText("Загрузить основной файл")
        except Exception:
            pass
        self.load_template_button.clicked.connect(self.load_template)
        self.loaded_data = []  # Список WellTimeSeries объектов
        self.current_index = 0  # Индекс текущей скважины
        self.validation_data = []  # Данные для проверки качества интерполяции
        self.last_interpolated_mask_XY = None  # Маска восстановленных точек для выделения на X-Y
        self.last_extrapolated_XY = None  # Пара экстраполированных X,Y для отображения
        
        # Создаем профессиональный интерфейс с вкладками
        setup_professional_interface(self)
        
        # Настраиваем обработчики событий
        self.setup_event_handlers()
    
    @property
    def current_data(self) -> Optional[WellTimeSeries]:
        """Возвращает данные текущей скважины"""
        if self.loaded_data and 0 <= self.current_index < len(self.loaded_data):
            return self.loaded_data[self.current_index]
        return None

    def show_info(self, title: str, message: str) -> None:
        """Показывает информационное сообщение (только если не test_mode)"""
        if not self.test_mode:
            QMessageBox.information(self, title, message)
    
    def show_warning(self, title: str, message: str) -> None:
        """Показывает предупреждение (только если не test_mode)"""
        if not self.test_mode:
            QMessageBox.warning(self, title, message)
    
    def show_error(self, title: str, message: str) -> None:
        """Показывает сообщение об ошибке (только если не test_mode)"""
        if not self.test_mode:
            QMessageBox.critical(self, title, message)

    def _get_params(self, data_item: WellTimeSeries, 
                        default_k: float = DEFAULT_K, 
                        default_mu: float = DEFAULT_MU, 
                        default_B: float = DEFAULT_B,
                        default_phi: float = DEFAULT_PHI, 
                        default_c_t: float = DEFAULT_C_T) -> Dict[str, Any]:
        """Создает словарь параметров скважины для безразмерного анализа"""
        return {
            'k': default_k,
            'h': data_item.thickness,
            'mu': default_mu,
            'B': default_B,
            'phi': default_phi,
            'c_t': default_c_t,
            'L': data_item.fracture_length,
            'skin': data_item.skin,
            'N': data_item.fractures_count,
            'a_L': data_item.a_l_ratio,
            'dP': data_item.dP if data_item.dP is not None else None  # dP из CSV данных
        }
    
    def _get_quality_label(self, rmse: float, short: bool = False) -> str:
        """Возвращает текстовое описание качества интерполяции на основе RMSE"""
        if rmse < RMSE_EXCELLENT_THRESHOLD:
            return 'отлично' if short else 'Отлично'
        elif rmse < RMSE_GOOD_THRESHOLD:
            return 'хорошо' if short else 'Хорошо'
        else:
            return 'удовл.' if short else 'Удовлетворительно'
    
    def _create_no_interpolation_report(self) -> str:
        """Создает отчет о том, что интерполяция не требуется"""
        separator = "=" * REPORT_SEPARATOR_LENGTH
        report = separator + "\n"
        report += "ИНТЕРПОЛЯЦИЯ НЕ ТРЕБУЕТСЯ\n"
        report += separator + "\n\n"
        report += "Данные не содержат пропущенных значений (NaN).\n"
        report += f"Точек данных по давлению: {len(self.current_data.pressure)}\n"
        report += f"Точек данных по дебиту: {len(self.current_data.flow_rate)}\n"
        report += "\nВсе данные присутствуют, интерполяция не нужна.\n"
        report += separator + "\n"
        return report
    
    def _perform_interpolation(self, n_nan_pressure: int, n_nan_flow: int) -> Tuple[Dict[str, Any], Any]:
        """Выполняет интерполяцию безразмерных кривых"""
        params = self._get_params(self.current_data)
        
        # Конвертируем в безразмерные параметры
        from helpers.dimensionless_analysis import convert_to_dimensionless_curves
        dim_data = convert_to_dimensionless_curves(
            self.current_data.time, self.current_data.pressure, self.current_data.flow_rate, params, x_mode='alt'
        )
        
        # Используем интерполятор безразмерных кривых для восстановления пропусков
        from helpers.dimensionless_interpolating import DimensionlessCurveInterpolator
        
        # Для интерполяции используем текущие параметры
        param_grid = np.array([[self.current_data.skin, self.current_data.fractures_count, self.current_data.a_l_ratio]])
        Y_grid = dim_data.Y
        P_curves = np.asarray([dim_data.pressure / (dim_data.delta_p_i if dim_data.delta_p_i != 0 else 1.0)])
        
        interp = DimensionlessCurveInterpolator(methods=INTERPOLATION_METHODS)
        interp.fit(param_grid, Y_grid, P_curves)
        
        # Предсказываем для тех же параметров (восстанавливаем пропуски)
        pred_series = interp.predict(
            skin=self.current_data.skin,
            N=self.current_data.fractures_count,
            a_L=self.current_data.a_l_ratio
        )
        
        # Восстанавливаем физические величины из безразмерных
        # pred_series имеет индекс Y_grid, нужно интерполировать обратно на time
        pressure_values = pred_series.values if hasattr(pred_series, 'values') else np.asarray(pred_series)
        
        # Проверяем, что pred_series содержит достаточно точек
        if len(pressure_values) != len(self.current_data.time):
            # Если количество точек не совпадает, интерполируем на временную сетку
            from scipy.interpolate import interp1d
            Y_grid_values = pred_series.index.values
            # Интерполируем pD обратно на Y из dim_data, затем на time
            if len(pressure_values) > 1 and len(dim_data.Y) > 1:
                # Создаем интерполятор для маппинга Y_grid -> Y из данных
                interp_pd = interp1d(Y_grid_values, pressure_values, kind='linear', 
                                     bounds_error=False, fill_value='extrapolate')
                # Интерполируем на Y из данных
                pD_interp = interp_pd(dim_data.Y)
                pressure_values = pD_interp
            elif len(pressure_values) == 1:
                # Если только одна точка, дублируем её для всех временных точек
                pressure_values = np.full(len(self.current_data.time), pressure_values[0])
        
        self.current_data.pressure = pd.Series(pressure_values * dim_data.delta_p_i, index=self.current_data.time)
        
        # Получаем информацию о результатах интерполяции
        interp_info = interp.get_interpolation_info()
        
        # Сохраняем информацию для отображения в резюме графика
        self.last_interpolation_info = interp_info
        
        return interp_info, dim_data
    
    def _create_interpolation_report(self, n_nan_pressure: int, n_nan_flow: int, 
                                    interp_info: Dict[str, Any]) -> str:
        """Создает отчет о результатах интерполяции"""
        method_names = {
            'linear': 'Линейная регрессия',
            'rbf': 'RBF интерполяция (Thin Plate Spline)',
            'gp': 'Гауссовский процесс'
        }
        
        # Определяем, что было интерполировано
        interpolated_items = []
        if n_nan_pressure > 0:
            interpolated_items.append(f"давление ({n_nan_pressure} точек)")
        if n_nan_flow > 0:
            interpolated_items.append(f"дебит ({n_nan_flow} точек)")
        
        separator = "=" * REPORT_SEPARATOR_LENGTH
        report = separator + "\n"
        report += "РЕЗУЛЬТАТЫ ИНТЕРПОЛЯЦИИ БЕЗРАЗМЕРНЫХ КРИВЫХ\n"
        report += separator + "\n\n"
        
        # Что было интерполировано
        report += "Интерполировано:\n"
        if interpolated_items:
            report += "  ✓ Безразмерная кривая pD(Y)\n"
            for item in interpolated_items:
                report += f"  ✓ {item}\n"
        report += "\n"
        
        # Исходные данные
        report += "Исходные данные:\n"
        report += f"  Всего точек: {len(self.current_data.time)}\n"
        total_possible = len(self.current_data.time) * N_PARAMETERS_PER_POINT
        total_nan = n_nan_pressure + n_nan_flow
        coverage = (1 - total_nan / total_possible) * 100 if total_possible > 0 else 0
        report += f"  Полнота данных: {coverage:.1f}%\n"
        report += f"  Заполнено пропусков:\n"
        if n_nan_pressure > 0:
            report += f"    - Давление: {n_nan_pressure} точек ({n_nan_pressure/len(self.current_data.time)*100:.1f}%)\n"
        if n_nan_flow > 0:
            report += f"    - Дебит: {n_nan_flow} точек ({n_nan_flow/len(self.current_data.time)*100:.1f}%)\n"
        report += "\n"
        
        # Параметры скважины
        report += "Параметры скважины (использованы для интерполяции):\n"
        report += f"  Skin: {self.current_data.skin:.4f}\n"
        report += f"  N (кол-во трещин): {self.current_data.fractures_count}\n"
        report += f"  a/L: {self.current_data.a_l_ratio:.4f}\n"
        report += f"  L (длина трещины): {self.current_data.fracture_length:.2f} м\n"
        report += f"  h (толщина пласта): {self.current_data.thickness:.2f} м\n"
        report += "\n"
        
        # Параметры интерполяции
        report += "Параметры метода:\n"
        report += f"  Обучающих примеров: {interp_info['n_samples']}\n"
        report += f"  Точек на безразмерной кривой: {interp_info['n_points']}\n\n"
        
        # Сравнение методов
        report += "СРАВНЕНИЕ МЕТОДОВ ИНТЕРПОЛЯЦИИ\n"
        report += "-" * REPORT_SEPARATOR_LENGTH + "\n"
        report += f"{'Метод':<42} {'RMSE':<12} {'Статус'}\n"
        report += "-" * REPORT_SEPARATOR_LENGTH + "\n"
        
        # Сортируем методы по RMSE
        sorted_methods = sorted(interp_info['rmse_scores'].items(), key=lambda x: x[1])
        
        for i, (method, rmse) in enumerate(sorted_methods, 1):
            method_display = method_names.get(method, method)
            marker = "✓ ВЫБРАН" if method == interp_info['best_method'] else f"#{i}"
            report += f"{method_display:<42} {rmse:<12.3f} {marker}\n"
        
        report += "-" * REPORT_SEPARATOR_LENGTH + "\n\n"
        
        # Итоговая информация
        best_rmse = interp_info['rmse_scores'].get(interp_info['best_method'], 0)
        report += "ИТОГОВЫЙ РЕЗУЛЬТАТ:\n"
        report += f"  Метод: {method_names.get(interp_info['best_method'], interp_info['best_method'])}\n"
        report += f"  RMSE: {best_rmse:.3f}\n"
        quality = self._get_quality_label(best_rmse)
        report += f"  Качество: {quality}\n"
        report += "\n" + separator + "\n"
        
        return report
    
    def setup_event_handlers(self) -> None:
        """Настройка обработчиков событий"""
        # Временные ряды
        self.plot_btn.clicked.connect(self.on_plot_dimensionless_selected)
        self.interp_btn.clicked.connect(self.on_interpolate_data)
        self.ml_filter_btn.clicked.connect(self.on_ml_filter)
        self.outlier_btn.clicked.connect(self.on_detect_outliers)
        self.export_btn.clicked.connect(self.on_export_data)
        self.load_validation_button.clicked.connect(self.load_validation_file)
        # Экстраполяция
        if hasattr(self, 'extrapolate_btn'):
            self.extrapolate_btn.clicked.connect(self.on_extrapolate_xy)
        
        # Кнопка сброса графиков (если существует)
        if hasattr(self, 'reset_plots_btn'):
            self.reset_plots_btn.clicked.connect(self.on_reset_plots)
        # Смена скважины: сбрасываем график и маски
        if hasattr(self, 'well_combo_dim'):
            self.well_combo_dim.currentIndexChanged.connect(self.on_well_changed)
        
        # Анализ ГРП
        self.flow_regime_btn.clicked.connect(self.on_analyze_flow_regime)
        self.productivity_btn.clicked.connect(self.on_compute_productivity_index)
        self.transitions_btn.clicked.connect(self.on_detect_flow_regime_transitions)
        
        # Эталонные кривые
        self.bilinear_btn.clicked.connect(self.on_plot_bilinear)
        self.linear_btn.clicked.connect(self.on_plot_linear)
        self.pseudoradial_btn.clicked.connect(self.on_plot_pseudoradial)
        self.match_curves_btn.clicked.connect(self.on_match_type_curves)
        
        # Результаты
        self.export_report_btn.clicked.connect(self.on_export_report)

        self.data_tab = setup_data_tab(self)
        self.tab_widget.addTab(self.data_tab, "Загруженные данные")

    def load_template(self) -> None:
        """Загрузка CSV файла с данными разведки месторождений"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Загрузить файл данных", "./", 
                                                 "Data Files (*.csv *.parquet);;CSV Files (*.csv);;Parquet Files (*.parquet);;All Files (*)")
        if not file_path:
            return

        # Парсим данные скважины
        try:
            data, error_msg = parse_well_data(file_path)
            if error_msg is not None:
                self.show_warning("Ошибка загрузки", error_msg)
                return
        except Exception as e:
            self.show_warning("Ошибка загрузки", f"Неожиданная ошибка при загрузке файла: {str(e)}")
            return

        self.loaded_data = data
        self.current_index = 0
        
        # Обновляем список выбора скважин
        self.update_well_selection()
        
        # Обновляем отображение параметров ГРП
        self.update_grp_parameters()
        
        # Обновляем вкладку с загруженными данными
        self.update_data_tab()
        
        # Обновляем старые поля для совместимости
        current_item = self.current_data
        if current_item:
            self.update_interface_parameters()
        
        # Показываем информацию о загруженных данных
        total_points = sum(len(item.time) for item in data)
        self.show_info("Данные загружены", 
                      f"Загружено {len(data)} групп данных\n"
                      f"Всего измерений: {total_points}\n"
                      f"Текущая скважина: {self.well_combo_dim.currentText()}")
        
        # Запускаем диагностику асинхронно
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self.run_data_diagnostics(file_path))
        
        # Обновляем комбо в новой вкладке
        self.well_combo_dim.clear()
        for i, item in enumerate(self.loaded_data):
            self.well_combo_dim.addItem(f"Скважина {i+1} (Skin={item.skin:.2f})")

    def load_validation_file(self) -> None:
        """Загрузка файла для проверки качества интерполяции."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Загрузить файл для проверки", "./", 
                                                 "Data Files (*.csv *.parquet);;CSV Files (*.csv);;Parquet Files (*.parquet);;All Files (*)")
        if not file_path:
            return

        try:
            data, error_msg = parse_well_data(file_path)
            if error_msg is not None:
                self.show_warning("Ошибка загрузки", error_msg)
                return
        except Exception as e:
            self.show_warning("Ошибка загрузки", f"Неожиданная ошибка при загрузке файла: {str(e)}")
            return

        self.validation_data = data
        self.show_info("Файл для проверки", 
                      f"Загружено {len(data)} групп данных для проверки\n"
                      f"Всего измерений: {sum(len(item.time) for item in data)}")
    
    def run_data_diagnostics(self, file_path: str) -> None:
        """Запускает диагностику загруженных данных"""
        try:
            print("\n" + "="*60)
            print(f"ДИАГНОСТИКА ДАННЫХ: {file_path}")
            print("="*60)
            
            # Импортируем функцию диагностики
            from helpers.input_test import diag_dimensional
            
            # Читаем CSV для диагностики
            import pandas as pd
            df = pd.read_csv(file_path)
            
            # Конвертируем в формат для diag_dimensional если нужно
            # Функция ожидает колонки: 'X', 'Y', 'P', 'Q', 't'
            if not all(col in df.columns for col in ['X', 'Y', 'P', 'Q', 't']):
                # Преобразуем из формата WellTimeSeries
                if self.loaded_data and len(self.loaded_data) > 0:
                    item = self.loaded_data[0]
                    # Конвертируем в безразмерные параметры
                    from helpers.dimensionless_analysis import convert_to_dimensionless_curves
                    params = self._get_params(item)
                    dim_data = convert_to_dimensionless_curves(
                        item.time, item.pressure, item.flow_rate, params, x_mode='alt'
                    )
                    
                    # Создаем DataFrame в нужном формате
                    df_diag = pd.DataFrame({
                        'X': dim_data.X,
                        'Y': dim_data.Y,
                        'P': dim_data.pressure,
                        'Q': dim_data.flow_rate,
                        'dP': dim_data.dP,
                        't': item.time
                    })
                else:
                    print("⚠️ Не удалось преобразовать данные для диагностики")
                    return
            else:
                df_diag = df
            
            # Запускаем диагностику (вывод идет в консоль)
            diag_dimensional(df_diag)
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"⚠️ Ошибка диагностики: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def update_interface_parameters(self) -> None:
        self.thickness_doubleSpinBox.setValue(self.current_data.thickness)
        self.skin_doubleSpinBox.setValue(self.current_data.skin)
        self.width_doubleSpinBox.setValue(self.current_data.fracture_width)
        self.n_spinBox.setValue(self.current_data.fractures_count)
        self.aL_doubleSpinBox.setValue(self.current_data.a_l_ratio)
    def update_data_tab(self) -> None:
        """Обновляет таблицу на вкладке 'Загруженные данные'"""
        if not self.loaded_data:
            self.data_info_label.setText("Нет загруженных данных")
            self.data_table.setModel(None)
            return

        # Преобразуем данные текущей скважины в DataFrame
        current_item = self.current_data
        df = pd.DataFrame({
            "time": current_item.time,
            "pressure": current_item.pressure,
            "rate": current_item.flow_rate
        })

        # Создаем модель для QTableView
        model = QStandardItemModel(df.shape[0], df.shape[1])
        model.setHorizontalHeaderLabels(df.columns)

        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                item = QStandardItem(str(df.iat[row, col]))
                item.setEditable(False)
                model.setItem(row, col, item)

        self.data_table.setModel(model)
        self.data_info_label.setText(f"Отображены данные скважины {self.current_index + 1} — {len(df)} строк")

        
    def update_well_selection(self) -> None:
        """Обновляет список выбора скважин"""
        self.well_combo_dim.clear()
        
        for i, item in enumerate(self.loaded_data):
            item_name = f"Скважина {i+1} (Skin={item.skin:.3f}, N={item.fractures_count})"
            self.well_combo_dim.addItem(item_name)
        
        if self.loaded_data:
            self.well_combo_dim.setCurrentIndex(self.current_index)
    
    def update_grp_parameters(self) -> None:
        """Обновляет отображение параметров ГРП"""
        current_item = self.current_data
        if current_item is None:
            return
            
        self.skin_value_label.setText(f"Skin: {current_item.skin:.3f}")
        self.thickness_value_label.setText(f"Толщина: {current_item.thickness:.1f} м")
        self.fractures_value_label.setText(f"Трещины: {current_item.fractures_count}")
        self.fracture_width_label.setText(f"Ширина трещины: {current_item.fracture_width:.3f} м")
        self.fracture_length_label.setText(f"Длина трещины: {current_item.fracture_length:.1f} м")
        self.al_ratio_label.setText(f"a/L: {current_item.a_l_ratio:.3f}")
    
    def on_interpolate_data(self) -> None:
        """Интерполяция данных безразмерных кривых"""
        if self.current_data is None:
            return
        
        # Проверяем, есть ли пропуски в данных
        has_nan = (self.current_data.pressure.isna().any() or 
                   self.current_data.flow_rate.isna().any())
        
        if not has_nan:
            # Данные уже полные, интерполяция не требуется
            report = self._create_no_interpolation_report()
            
            if hasattr(self, 'results_text'):
                self.results_text.setPlainText(report)
            
            self.show_info("Интерполяция", 
                          "Данные уже полные, интерполяция не требуется")
            return
        
        try:
            # Подсчитываем количество пропусков
            pressure_is_nan_mask = self.current_data.pressure.isna().values if hasattr(self.current_data.pressure, 'isna') else None
            n_nan_pressure = int(np.nansum(pressure_is_nan_mask)) if pressure_is_nan_mask is not None else self.current_data.pressure.isna().sum()
            n_nan_flow = self.current_data.flow_rate.isna().sum()
            
            # Сохраняем маску пропусков для подсветки на X-Y графике
            try:
                self.last_interpolated_mask_XY = pressure_is_nan_mask.copy() if pressure_is_nan_mask is not None else None
            except Exception:
                self.last_interpolated_mask_XY = None

            # Выполняем интерполяцию
            interp_info, _ = self._perform_interpolation(n_nan_pressure, n_nan_flow)
            
            # Формируем отчет
            report = self._create_interpolation_report(n_nan_pressure, n_nan_flow, interp_info)
            
            # Выводим в текстовое поле результатов
            if hasattr(self, 'results_text'):
                self.results_text.setPlainText(report)
            
            self.on_plot_dimensionless_selected()
            
            # Показываем информационное сообщение
            method_names = {
                'linear': 'Линейная регрессия',
                'rbf': 'RBF интерполяция (Thin Plate Spline)',
                'gp': 'Гауссовский процесс'
            }
            best_rmse = interp_info['rmse_scores'].get(interp_info['best_method'], 0)
            quality = self._get_quality_label(best_rmse)
            self.show_info("Интерполяция", 
                          f"Данные интерполированы методом безразмерных кривых\n\n"
                          f"Выбранный метод: {method_names.get(interp_info['best_method'], interp_info['best_method'])}\n"
                          f"RMSE: {best_rmse:.3f}\n"
                          f"Качество: {quality}")
        except Exception as e:
            self.show_warning("Ошибка", f"Ошибка интерполяции: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    def on_reset_plots(self) -> None:
        """Сброс всех графиков и чекбоксов"""
        # Очищаем график
        if hasattr(self, 'dimensionless_plot'):
            self.dimensionless_plot.clear()
            self.dimensionless_plot.setLabel('bottom', 'X (безразмерный фильтрационный параметр)')
            self.dimensionless_plot.setLabel('left', 'Безразмерный параметр')
            self.dimensionless_plot.setTitle("Безразмерные кривые МГРП")
            self.dimensionless_plot.showGrid(x=True, y=True)
        
        # Снимаем все чекбоксы
        if hasattr(self, 'cb_dim_pD'):
            self.cb_dim_pD.setChecked(False)
        if hasattr(self, 'cb_dim_dpD'):
            self.cb_dim_dpD.setChecked(False)
        if hasattr(self, 'cb_dim_tD'):
            self.cb_dim_tD.setChecked(False)
        if hasattr(self, 'cb_dim_CD'):
            self.cb_dim_CD.setChecked(False)
        if hasattr(self, 'cb_XY_plot'):
            self.cb_XY_plot.setChecked(False)
        if hasattr(self, 'cb_calc_XY'):
            self.cb_calc_XY.setChecked(False)
        if hasattr(self, 'cb_type_gry'):
            self.cb_type_gry.setChecked(False)
        if hasattr(self, 'cb_type_cinco'):
            self.cb_type_cinco.setChecked(False)
        if hasattr(self, 'cb_type_valko'):
            self.cb_type_valko.setChecked(False)
        if hasattr(self, 'cb_gfunc'):
            self.cb_gfunc.setChecked(False)
        if hasattr(self, 'cb_mbt'):
            self.cb_mbt.setChecked(False)
        if hasattr(self, 'cb_real_p'):
            self.cb_real_p.setChecked(False)
        if hasattr(self, 'cb_real_q'):
            self.cb_real_q.setChecked(False)
        
        # Очищаем отчёт
        if hasattr(self, 'text_report'):
            self.text_report.clear()
        
        if not self.test_mode:
            self.show_info("Графики очищены", "Все графики и чекбоксы сброшены")

        # Сбрасываем внутренние состояния подсветки/экстраполяции
        self.last_interpolated_mask_XY = None
        self.last_extrapolated_XY = None

    def on_well_changed(self, index: int) -> None:
        """Обработка смены выбранной скважины."""
        self.current_index = index
        self.last_interpolated_mask_XY = None
        self.last_extrapolated_XY = None
        # Обновляем инфо и очищаем графики/чекбоксы
        self.update_grp_parameters()
        self.update_data_tab()
        if hasattr(self, 'dimensionless_plot'):
            self.dimensionless_plot.clear()
            self.dimensionless_plot.setLabel('bottom', 'X (безразмерный фильтрационный параметр)')
            self.dimensionless_plot.setLabel('left', 'Безразмерный параметр')
            self.dimensionless_plot.setTitle("Безразмерные кривые МГРП")
            self.dimensionless_plot.showGrid(x=True, y=True)

    def on_extrapolate_xy(self) -> None:
        """Экстраполяция и наложение X–Y кривой на график."""
        if self.current_data is None:
            return
        try:
            # Готовим параметры скважины
            params = self._get_params(self.current_data)
            # Генерируем кривую X–Y по физической модели
            from helpers.ml_methods import generate_xy_from_params
            X_ext, Y_ext = generate_xy_from_params({
                'skin': params['skin'],
                'N': params['N'],
                'a_L': params['a_L']
            }, n_points=128)
            self.last_extrapolated_XY = (X_ext, Y_ext)
            # Перестраиваем график с наложением экстраполяции
            self.on_plot_dimensionless_selected()
            self.show_info("Экстраполяция", "Экстраполированная кривая X–Y добавлена на график")
        except Exception as e:
            self.show_warning("Ошибка экстраполяции", f"Не удалось выполнить экстраполяцию: {str(e)}")
    
    def on_plot_dimensionless_selected(self) -> None:
        """Обработка нажатия на кнопку 'Построить график'."""
        self.dimensionless_plot.clear()
        self.text_report.clear()

        current_item = self.current_data
        if current_item is None:
            self.text_report.setText("❌ Нет данных для построения.")
            return

        try:
            # Параметры скважины
            params = self._get_params(current_item)
            
            # 1️⃣ Конвертация в безразмерные параметры
            dim_data = convert_to_dimensionless_curves(
                current_item.time, current_item.pressure, current_item.flow_rate, params, x_mode='alt'
            )

            # 2️⃣ Определяем, какие группы графиков выбраны
            checked_groups = {
                # Реальные параметры
                'real_params': self.cb_real_p.isChecked() or self.cb_real_q.isChecked(),
                'cb_real_p': self.cb_real_p.isChecked(),
                'cb_real_q': self.cb_real_q.isChecked(),
                
                # Безразмерные кривые
                'dimensionless': (self.cb_dim_pD.isChecked() or self.cb_dim_dpD.isChecked() or 
                                 self.cb_dim_tD.isChecked() or self.cb_dim_CD.isChecked()),
                'cb_dim_pD': self.cb_dim_pD.isChecked(),
                'cb_dim_dpD': self.cb_dim_dpD.isChecked(),
                'cb_dim_tD': self.cb_dim_tD.isChecked(),
                'cb_dim_CD': self.cb_dim_CD.isChecked(),
                'cb_XY_plot': hasattr(self, 'cb_XY_plot') and self.cb_XY_plot.isChecked(),
                'cb_calc_XY': hasattr(self, 'cb_calc_XY') and self.cb_calc_XY.isChecked(),
                
                # Типовые кривые
                'type_curves': (self.cb_type_gry.isChecked() or self.cb_type_cinco.isChecked() or 
                               self.cb_type_valko.isChecked()),
                'cb_type_gry': self.cb_type_gry.isChecked(),
                'cb_type_cinco': self.cb_type_cinco.isChecked(),
                'cb_type_valko': self.cb_type_valko.isChecked(),
                
                # Специальные пространства (если есть)
                'special': (hasattr(self, 'cb_gfunc') and self.cb_gfunc.isChecked()) or \
                          (hasattr(self, 'cb_mbt') and self.cb_mbt.isChecked()),
                'cb_gfunc': hasattr(self, 'cb_gfunc') and self.cb_gfunc.isChecked(),
                'cb_mbt': hasattr(self, 'cb_mbt') and self.cb_mbt.isChecked(),
            }
            
            # Проверяем, выбрано ли что-то для отображения
            has_any_selected = (checked_groups.get('real_params', False) or
                              checked_groups.get('dimensionless', False) or
                              checked_groups.get('cb_XY_plot', False) or
                              checked_groups.get('type_curves', False) or
                              checked_groups.get('special', False))
            
            if not has_any_selected:
                self.text_report.setText("⚠️ Выберите хотя бы один график для отображения в чекбоксах.")
                return
            
            # 3️⃣ Подготовка данных для валидации
            validation_data = None
            if self.validation_data:
                try:
                    ref_item = self.validation_data[0]
                    ref_params = self._get_params(ref_item)
                    ref_dim = convert_to_dimensionless_curves(
                        ref_item.time, ref_item.pressure, ref_item.flow_rate, ref_params, x_mode='alt'
                    )
                    validation_data = {'ref_dim': ref_dim}
                except Exception as e:
                    self.text_report.append(f"⚠️ Ошибка подготовки данных валидации: {e}")
            
            # 4️⃣ Используем новую функцию для отображения сгруппированных графиков
            # Передаём X и Y из данных, если они есть
            X_data = current_item.X if hasattr(current_item, 'X') and current_item.X is not None else None
            Y_data = current_item.Y if hasattr(current_item, 'Y') and current_item.Y is not None else None
            show_calc_XY = hasattr(self, 'cb_calc_XY') and self.cb_calc_XY.isChecked()

            # Предупреждение: выбран график X-Y из данных, но данных X,Y нет
            if checked_groups.get('cb_XY_plot', False) and (X_data is None or Y_data is None):
                self.show_warning("X-Y график", "Входные X,Y отсутствуют в данных. Будут использованы расчётные значения.")
            
            plot_dimensionless_grouped(
                plot_widget=self.dimensionless_plot,
                dim_data=dim_data,
                time=current_item.time,
                pressure=current_item.pressure,
                flow_rate=current_item.flow_rate,
                checked_groups=checked_groups,
                validation_data=validation_data,
                X_data=X_data,
                Y_data=Y_data,
                show_calculated_XY=show_calc_XY,
                interpolated_mask_XY=(self.last_interpolated_mask_XY if self.last_interpolated_mask_XY is not None else None),
                extrapolated_XY=(self.last_extrapolated_XY if self.last_extrapolated_XY is not None else None)
            )
            
            self.text_report.append("✅ График построен успешно")
            
            # Добавляем краткое резюме, если была проведена интерполяция
            if hasattr(self, 'last_interpolation_info') and self.last_interpolation_info:
                interp_info = self.last_interpolation_info
                method_names = {
                    'linear': 'Линейная регрессия',
                    'rbf': 'RBF',
                    'gp': 'GP'
                }
                best_rmse = interp_info['rmse_scores'].get(interp_info['best_method'], 0)
                quality = self._get_quality_label(best_rmse, short=True)
                self.text_report.append(
                    f"📊 Интерполяция: {method_names.get(interp_info['best_method'], interp_info['best_method'])}, "
                    f"RMSE={best_rmse:.3f} ({quality})"
                )
            
        except Exception as e:
            self.text_report.setText(f"❌ Ошибка построения графика: {str(e)}")
            import traceback
            print(traceback.format_exc())        

    def on_ml_filter(self) -> None:
        """ML-фильтрация данных"""
        if self.current_data is None:
            return
            
        try:
            filtered = apply_ml_filter(self.current_data.pressure, 'savitzky_golay', 
                                     window_length=DEFAULT_SAVGOL_WINDOW_LENGTH, 
                                     polyorder=DEFAULT_SAVGOL_POLYORDER)
            self.current_data.pressure = filtered
            self.on_plot_dimensionless_selected()
            self.show_info("ML фильтрация", "Данные отфильтрованы с помощью ML")
        except Exception as e:
            self.show_warning("Ошибка", f"Ошибка ML фильтрации: {str(e)}")
            
    def on_detect_outliers(self) -> None:
        """Обнаружение выбросов"""
        if self.current_data is None:
            return

        try:
            outliers = detect_outliers(self.current_data.pressure, 'iqr', threshold=DEFAULT_OUTLIER_THRESHOLD)
            outlier_count = outliers.sum()
            
            self.show_info("Обнаружение выбросов", f"Найдено {outlier_count} выбросов")
            
            # Обновляем график
            self.on_plot_dimensionless_selected()
        except Exception as e:
            self.show_warning("Ошибка", f"Ошибка обнаружения выбросов: {str(e)}")
    
    def plot_outliers_with_highlight(self, outliers: pd.Series, plot_type: str) -> None:
        """Построение графика с выделенными выбросами"""
        self.plot_widget.clear()
        
        if plot_type == "Давление vs Время":
            # Обычные точки
            normal_mask = ~outliers
            self.plot_widget.plot(self.current_data.pressure[normal_mask],
                                self.current_data.time[normal_mask],
                                pen='b', symbol='o', symbolSize=5)
            
            # Выбросы
            if outliers.any():
                self.plot_widget.plot(self.current_data.pressure[outliers],
                                    self.current_data.time[outliers],
                                    pen=None, symbol='x', symbolSize=10, symbolBrush='r')
            
            self.plot_widget.setLabel('bottom', 'Давление, атм')
            self.plot_widget.setLabel('left', 'Время, ч')
            self.plot_widget.setTitle('Давление vs Время (красные X - выбросы)')
            
        else:  # Дебит vs Время
            normal_mask = ~outliers
            self.plot_widget.plot(self.current_data.flow_rate[normal_mask],
                                self.current_data.time[normal_mask],
                                pen='g', symbol='s', symbolSize=5)
            
            if outliers.any():
                self.plot_widget.plot(self.current_data.flow_rate[outliers],
                                    self.current_data.time[outliers],
                                    pen=None, symbol='x', symbolSize=10, symbolBrush='r')
            
            self.plot_widget.setLabel('bottom', 'Дебит, м³/сут')
            self.plot_widget.setLabel('left', 'Время, ч')
            self.plot_widget.setTitle('Дебит vs Время (красные X - выбросы)')
    
    def on_export_data(self) -> None:
        """Экспорт данных"""
        if self.current_data is None:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт данных", "", "CSV файлы (*.csv)")

        if file_path:
            try:
                # Создаем DataFrame для экспорта
                export_df = pd.DataFrame({
                    'Time': self.current_data.time,
                    'Pressure': self.current_data.pressure,
                    'FlowRate': self.current_data.flow_rate
                })
                export_df.to_csv(file_path, index=False)
                self.show_info("Экспорт", "Данные успешно экспортированы")
            except Exception as e:
                self.show_warning("Ошибка экспорта", f"Не удалось экспортировать данные: {str(e)}")
    
    def on_analyze_flow_regime(self) -> None:
        """Анализ режима течения"""
        if self.current_data is None:
            return
            
        from helpers.grp_analysis import analyze_flow_regime
        analysis = analyze_flow_regime(self.current_data)
        
        result_text = f"""
Анализ режима течения:
Тип режима: {analysis.regime_type}
Уверенность: {analysis.confidence:.2f}
Характерное время: {analysis.characteristic_time or 'Не определено'}

Параметры:
{chr(10).join([f'{k}: {v}' for k, v in analysis.parameters.items()])}
"""
        self.show_info("Анализ режима течения", result_text)

    def on_compute_productivity_index(self) -> None:
        """Вычисление индекса продуктивности"""
        if self.current_data is None:
            return

        from helpers.grp_analysis import compute_productivity_index
        productivity = compute_productivity_index(self.current_data)

        result_text = f"""
Индекс продуктивности скважины:
Индекс продуктивности: {productivity['productivity_index']:.4f}
Эффективность ГРП: {productivity['fracture_efficiency']:.4f}
Средний дебит: {productivity['average_flow_rate']:.2f} м³/сут
Среднее давление: {productivity['average_pressure']:.2f} атм
Влияние скин-эффекта: {productivity['skin_impact']:.4f}
Общая длина трещин: {productivity['total_fracture_length']:.2f} м
"""

        self.show_info("Индекс продуктивности", result_text)

    def on_detect_flow_regime_transitions(self) -> None:
        """Обнаружение переходов режимов"""
        if self.current_data is None:
            return

        from helpers.grp_analysis import detect_flow_regime_transitions
        transitions = detect_flow_regime_transitions(self.current_data)

        if transitions:
            result_text = f"Найдено {len(transitions)} переходов режимов течения:\n\n"
            for i, trans in enumerate(transitions, 1):
                result_text += f"Переход {i}:\n"
                result_text += f"Время: {trans['time']:.2f} ч\n"
                result_text += f"Давление: {trans['pressure']:.2f} атм\n"
                result_text += f"Дебит: {trans['flow_rate']:.2f} м³/сут\n"
                result_text += f"Изменение производной: {trans['derivative_change']:.4f}\n\n"
        else:
            result_text = "Переходы режимов течения не обнаружены"

        self.show_info("Переходы режимов", result_text)

    def on_plot_bilinear(self) -> None:
        """Построение кривой билинейного течения"""
        if self.current_data is None or self.type_curves_widget is None:
            return

        from helpers.grp_analysis import generate_type_curves
        time_range = np.logspace(TYPE_CURVE_TIME_MIN, TYPE_CURVE_TIME_MAX, TYPE_CURVE_N_POINTS)
        curves = generate_type_curves(self.current_data.skin, self.current_data.fractures_count,
                                     self.current_data.a_l_ratio, time_range)

        self.type_curves_widget.clear()
        time_curve, pressure_curve = curves['bilinear']
        self.type_curves_widget.plot(time_curve, pressure_curve, pen='b', name='Билинейное течение')
        self.type_curves_widget.setLabel('left', 'Давление, атм')
        self.type_curves_widget.setLabel('bottom', 'Время, ч')
        self.type_curves_widget.setTitle('Билинейное течение')

    def on_plot_linear(self) -> None:
        """Построение кривой линейного течения"""
        if self.current_data is None or self.type_curves_widget is None:
            return

        from helpers.grp_analysis import generate_type_curves
        time_range = np.logspace(TYPE_CURVE_TIME_MIN, TYPE_CURVE_TIME_MAX, TYPE_CURVE_N_POINTS)
        curves = generate_type_curves(self.current_data.skin, self.current_data.fractures_count,
                                     self.current_data.a_l_ratio, time_range)

        self.type_curves_widget.clear()
        time_curve, pressure_curve = curves['linear']
        self.type_curves_widget.plot(time_curve, pressure_curve, pen='g', name='Линейное течение')
        self.type_curves_widget.setLabel('left', 'Давление, атм')
        self.type_curves_widget.setLabel('bottom', 'Время, ч')
        self.type_curves_widget.setTitle('Линейное течение')

    def on_plot_pseudoradial(self) -> None:
        """Построение кривой псевдорадиального течения"""
        if self.current_data is None or self.type_curves_widget is None:
            return

        from helpers.grp_analysis import generate_type_curves
        time_range = np.logspace(TYPE_CURVE_TIME_MIN, TYPE_CURVE_TIME_MAX, TYPE_CURVE_N_POINTS)
        curves = generate_type_curves(self.current_data.skin, self.current_data.fractures_count,
                                     self.current_data.a_l_ratio, time_range)

        self.type_curves_widget.clear()
        time_curve, pressure_curve = curves['pseudoradial']
        self.type_curves_widget.plot(time_curve, pressure_curve, pen='r', name='Псевдорадиальное течение')
        self.type_curves_widget.setLabel('left', 'Давление, атм')
        self.type_curves_widget.setLabel('bottom', 'Время, ч')
        self.type_curves_widget.setTitle('Псевдорадиальное течение')

    def on_match_type_curves(self) -> None:
        """Сопоставление с эталонными кривыми"""
        if self.current_data is None:
            return

        from helpers.grp_analysis import match_type_curves
        match_result = match_type_curves(self.current_data)

        result_text = f"""
Сопоставление с эталонными кривыми:
Лучшее совпадение: {match_result.curve_type}
Качество совпадения: {match_result.match_quality:.2f}

Оцененные параметры:
{chr(10).join([f'{k}: {v}' for k, v in match_result.estimated_parameters.items()])}
"""

        self.show_info("Сопоставление кривых", result_text)

    def on_export_report(self) -> None:
        """Экспорт отчета"""
        if self.current_data is None:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт отчета", "", "Текстовые файлы (*.txt)")

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("ОТЧЕТ АНАЛИЗА ДАННЫХ ГРП\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Скважина: Skin={self.current_data.skin:.3f}, "
                           f"N={self.current_data.fractures_count}, "
                           f"a/L={self.current_data.a_l_ratio:.3f}\n\n")

                    # Анализ режима течения
                    from helpers.grp_analysis import analyze_flow_regime
                    analysis = analyze_flow_regime(self.current_data)
                    f.write(f"Режим течения: {analysis.regime_type}\n")
                    f.write(f"Уверенность: {analysis.confidence:.2f}\n")
                    f.write(f"Характерное время: {analysis.characteristic_time or 'Не определено'}\n\n")

                    # Индекс продуктивности
                    from helpers.grp_analysis import compute_productivity_index
                    productivity = compute_productivity_index(self.current_data)
                    f.write("Индекс продуктивности:\n")
                    f.write(f"  Индекс продуктивности: {productivity['productivity_index']:.4f}\n")
                    f.write(f"  Эффективность ГРП: {productivity['fracture_efficiency']:.4f}\n")
                    f.write(f"  Средний дебит: {productivity['average_flow_rate']:.2f} м³/сут\n")
                    f.write(f"  Среднее давление: {productivity['average_pressure']:.2f} атм\n\n")

                self.show_info("Экспорт отчета", "Отчет успешно экспортирован")
            except Exception as e:
                self.show_warning("Ошибка экспорта", f"Не удалось экспортировать отчет: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())
