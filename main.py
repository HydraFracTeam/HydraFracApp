import sys
import pandas as pd
import numpy as np
from PySide6.QtWidgets import (QLabel, QApplication, QMainWindow, QFileDialog, QMessageBox, 
                               QComboBox, QSpinBox, QPushButton, QWidget, QVBoxLayout, 
                               QHBoxLayout, QTabWidget, QTextEdit, QGroupBox, QGridLayout)
from ui import Ui_mainWindow

from helpers.parse_well_data import parse_well_csv, extract_well_parameters, analyze_well_groups
from helpers.physics import compute_transmissivity, compute_pore_volume
from helpers.timeseries import compute_derivative, interpolate_series, smooth_series
from helpers.grp_analysis import (analyze_flow_regime, match_type_curves, 
                                 compute_well_productivity_index, detect_flow_regime_transitions)
from helpers.ml_methods import (apply_ml_interpolation, apply_ml_filter, 
                               clean_data, detect_outliers, AdvancedInterpolator)
from schemas.well_data import WellTimeSeries

try:
    import pyqtgraph as pg
except Exception:
    pg = None


class MyApp(QMainWindow, Ui_mainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.load_template_button.clicked.connect(self.load_template)
        self.well_data_list = []  # Список WellTimeSeries объектов
        self.current_well_index = 0  # Индекс текущей скважины
        self.current_plot_type = "pressure"  # Тип текущего графика
        
        # Создаем профессиональный интерфейс с вкладками
        self.setup_professional_interface()
        
        # Настраиваем обработчики событий
        self.setup_event_handlers()
    
    @property
    def current_well_data(self):
        """Возвращает данные текущей скважины"""
        if self.well_data_list and 0 <= self.current_well_index < len(self.well_data_list):
            return self.well_data_list[self.current_well_index]
        return None

    @property
    def well_data(self):
        """Алиас для current_well_data для совместимости"""
        return self.current_well_data

    def setup_professional_interface(self):
        """Создает профессиональный интерфейс с вкладками для анализа ГРП"""
        # Основной контейнер с вкладками
        self.tab_widget = QTabWidget(self.centralwidget)
        self.tab_widget.setGeometry(350, 20, 850, 700)
        
        # Вкладка 1: Временные ряды
        self.timeseries_tab = QWidget()
        self.tab_widget.addTab(self.timeseries_tab, "Временные ряды")
        self.setup_timeseries_tab()
        
        # Вкладка 2: Анализ ГРП
        self.grp_tab = QWidget()
        self.tab_widget.addTab(self.grp_tab, "Анализ ГРП")
        self.setup_grp_tab()
        
        # Вкладка 3: Эталонные кривые
        self.type_curves_tab = QWidget()
        self.tab_widget.addTab(self.type_curves_tab, "Эталонные кривые")
        self.setup_type_curves_tab()
        
        # Вкладка 4: Результаты анализа
        self.results_tab = QWidget()
        self.tab_widget.addTab(self.results_tab, "Результаты")
        self.setup_results_tab()
    
    def setup_timeseries_tab(self):
        """Настройка вкладки временных рядов"""
        layout = QVBoxLayout(self.timeseries_tab)
        
        # Панель управления графиками
        controls_group = QGroupBox("Управление графиками")
        controls_layout = QGridLayout(controls_group)
        
        # Выбор скважины
        self.well_selection_combo = QComboBox()
        self.well_selection_combo.setToolTip("Выберите скважину для анализа")
        
        # Выбор типа графика
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems([
            "Давление vs Время",
            "Дебит vs Время", 
            "Производная давления",
            "Производная дебита",
            "Давление vs Дебит",
            "Безразмерные параметры (X-Y)",
            "Логарифмический P(t) с инверсией",
            "Логарифмический Q(t)",
            "Логарифмическая производная P"
        ])
        
        # Кнопки анализа
        self.plot_btn = QPushButton("Построить график")
        self.smooth_btn = QPushButton("Сгладить данные")
        self.interp_btn = QPushButton("Интерполяция")
        self.ml_interp_btn = QPushButton("ML интерполяция")
        self.ml_filter_btn = QPushButton("ML фильтрация")
        self.outlier_btn = QPushButton("Обнаружить выбросы")
        self.export_btn = QPushButton("Экспорт данных")
        
        controls_layout.addWidget(QLabel("Скважина:"), 0, 0)
        controls_layout.addWidget(self.well_selection_combo, 0, 1)
        controls_layout.addWidget(QLabel("Тип графика:"), 0, 2)
        controls_layout.addWidget(self.plot_type_combo, 0, 3)
        controls_layout.addWidget(self.plot_btn, 1, 0)
        controls_layout.addWidget(self.smooth_btn, 1, 1)
        controls_layout.addWidget(self.interp_btn, 1, 2)
        controls_layout.addWidget(self.ml_interp_btn, 1, 3)
        controls_layout.addWidget(self.ml_filter_btn, 2, 0)
        controls_layout.addWidget(self.outlier_btn, 2, 1)
        controls_layout.addWidget(self.export_btn, 2, 2)
        
        layout.addWidget(controls_group)
        
        # Область для графиков
        if pg is not None:
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setLabel('bottom', 'Значение')
            self.plot_widget.setLabel('left', 'Время, ч')
            self.plot_widget.showGrid(x=True, y=True)
            layout.addWidget(self.plot_widget)
        else:
            self.plot_widget = None
            layout.addWidget(QLabel("pyqtgraph не установлен"))
    
    def setup_grp_tab(self):
        """Настройка вкладки анализа ГРП"""
        layout = QVBoxLayout(self.grp_tab)
        
        # Панель параметров ГРП
        params_group = QGroupBox("Параметры ГРП")
        params_layout = QGridLayout(params_group)
        
        # Отображение параметров из загруженных данных
        self.skin_value_label = QLabel("Skin: -")
        self.thickness_value_label = QLabel("Толщина: -")
        self.fractures_value_label = QLabel("Трещины: -")
        self.fracture_width_label = QLabel("Ширина трещины: -")
        self.fracture_length_label = QLabel("Длина трещины: -")
        self.al_ratio_label = QLabel("a/L: -")
        
        params_layout.addWidget(self.skin_value_label, 0, 0)
        params_layout.addWidget(self.thickness_value_label, 0, 1)
        params_layout.addWidget(self.fractures_value_label, 0, 2)
        params_layout.addWidget(self.fracture_width_label, 1, 0)
        params_layout.addWidget(self.fracture_length_label, 1, 1)
        params_layout.addWidget(self.al_ratio_label, 1, 2)
        
        layout.addWidget(params_group)
        
        # Кнопки анализа
        analysis_group = QGroupBox("Анализ")
        analysis_layout = QHBoxLayout(analysis_group)
        
        self.flow_regime_btn = QPushButton("Анализ режима течения")
        self.productivity_btn = QPushButton("Индекс продуктивности")
        self.transitions_btn = QPushButton("Переходы режимов")
        
        analysis_layout.addWidget(self.flow_regime_btn)
        analysis_layout.addWidget(self.productivity_btn)
        analysis_layout.addWidget(self.transitions_btn)
        
        layout.addWidget(analysis_group)
        
        # Область для результатов
        self.grp_results_text = QTextEdit()
        self.grp_results_text.setMaximumHeight(200)
        layout.addWidget(self.grp_results_text)
    
    def setup_type_curves_tab(self):
        """Настройка вкладки эталонных кривых"""
        layout = QVBoxLayout(self.type_curves_tab)
        
        # Панель управления
        controls_group = QGroupBox("Эталонные кривые")
        controls_layout = QHBoxLayout(controls_group)
        
        self.bilinear_btn = QPushButton("Билинейное течение")
        self.linear_btn = QPushButton("Линейное течение")
        self.pseudoradial_btn = QPushButton("Псевдорадиальное течение")
        self.match_curves_btn = QPushButton("Сопоставить с данными")
        
        controls_layout.addWidget(self.bilinear_btn)
        controls_layout.addWidget(self.linear_btn)
        controls_layout.addWidget(self.pseudoradial_btn)
        controls_layout.addWidget(self.match_curves_btn)
        
        layout.addWidget(controls_group)
        
        # График эталонных кривых
        if pg is not None:
            self.type_curves_widget = pg.PlotWidget()
            self.type_curves_widget.setLabel('left', 'Дебит, м³/сут')
            self.type_curves_widget.setLabel('bottom', 'Время, ч')
            self.type_curves_widget.setLogMode(True, True)  # Log-log масштаб
            self.type_curves_widget.showGrid(x=True, y=True)
            layout.addWidget(self.type_curves_widget)
        else:
            self.type_curves_widget = None
            layout.addWidget(QLabel("pyqtgraph не установлен"))
    
    def setup_results_tab(self):
        """Настройка вкладки результатов анализа"""
        layout = QVBoxLayout(self.results_tab)
        
        # Область для отображения результатов
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)
        
        # Кнопка экспорта отчета
        self.export_report_btn = QPushButton("Экспорт отчета")
        layout.addWidget(self.export_report_btn)
    
    def setup_event_handlers(self):
        """Настройка обработчиков событий"""
        # Временные ряды
        self.well_selection_combo.currentIndexChanged.connect(self.on_well_selection_changed)
        self.plot_btn.clicked.connect(self.on_plot_timeseries)
        self.smooth_btn.clicked.connect(self.on_smooth_data)
        self.interp_btn.clicked.connect(self.on_interpolate_data)
        self.ml_interp_btn.clicked.connect(self.on_ml_interpolate)
        self.ml_filter_btn.clicked.connect(self.on_ml_filter)
        self.outlier_btn.clicked.connect(self.on_detect_outliers)
        self.export_btn.clicked.connect(self.on_export_data)
        
        # Анализ ГРП
        self.flow_regime_btn.clicked.connect(self.on_analyze_flow_regime)
        self.productivity_btn.clicked.connect(self.on_compute_productivity)
        self.transitions_btn.clicked.connect(self.on_detect_transitions)
        
        # Эталонные кривые
        self.bilinear_btn.clicked.connect(self.on_plot_bilinear)
        self.linear_btn.clicked.connect(self.on_plot_linear)
        self.pseudoradial_btn.clicked.connect(self.on_plot_pseudoradial)
        self.match_curves_btn.clicked.connect(self.on_match_curves)
        
        # Результаты
        self.export_report_btn.clicked.connect(self.on_export_report)

    def load_template(self):
        """Загрузка CSV файла с данными разведки месторождений"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Загрузить файл данных", "./", 
                                                 "Data Files (*.csv *.parquet);;CSV Files (*.csv);;Parquet Files (*.parquet);;All Files (*)")
        if not file_path:
            return

        # Парсим данные скважины
        try:
            well_data_list, error_msg = parse_well_csv(file_path)
            if error_msg is not None:
                QMessageBox.warning(self, "Ошибка загрузки", error_msg)
                return
        except Exception as e:
            QMessageBox.warning(self, "Ошибка загрузки", f"Неожиданная ошибка при загрузке файла: {str(e)}")
            return

        self.well_data_list = well_data_list
        self.current_well_index = 0
        
        # Обновляем список выбора скважин
        self.update_well_selection()
        
        # Обновляем отображение параметров ГРП
        self.update_grp_parameters()
        
        # Обновляем старые поля для совместимости
        current_well = self.current_well_data
        if current_well:
            self.k_doubleSpinBox.setValue(0.001)  # Примерное значение
            self.h_doubleSpinBox.setValue(current_well.thickness)
            self.phi_doubleSpinBox.setValue(0.2)  # Примерное значение
            
            # Обновляем параметры ГРП в старом интерфейсе
            self.skin_doubleSpinBox.setValue(current_well.skin)
            self.n_spinBox.setValue(current_well.fractures_count)
            self.aL_doubleSpinBox.setValue(current_well.a_l_ratio)
        
        # Показываем информацию о загруженных данных
        total_points = sum(len(well.time) for well in well_data_list)
        QMessageBox.information(self, "Данные загружены", 
                              f"Загружено {len(well_data_list)} групп данных\n"
                              f"Всего измерений: {total_points}\n"
                              f"Текущая скважина: {self.well_selection_combo.currentText()}")
        
        # Автоматически строим первый график
        self.on_plot_timeseries()
    
    def update_well_selection(self):
        """Обновляет список выбора скважин"""
        self.well_selection_combo.clear()
        
        for i, well_data in enumerate(self.well_data_list):
            well_name = f"Скважина {i+1} (Skin={well_data.skin:.3f}, N={well_data.fractures_count})"
            self.well_selection_combo.addItem(well_name)
        
        if self.well_data_list:
            self.well_selection_combo.setCurrentIndex(self.current_well_index)
    
    def on_well_selection_changed(self, index):
        """Обработчик изменения выбора скважины"""
        if 0 <= index < len(self.well_data_list):
            self.current_well_index = index
            self.update_grp_parameters()
            # Автоматически обновляем график
            self.on_plot_timeseries()
    
    def update_grp_parameters(self):
        """Обновляет отображение параметров ГРП"""
        current_well = self.current_well_data
        if current_well is None:
            return
            
        self.skin_value_label.setText(f"Skin: {current_well.skin:.3f}")
        self.thickness_value_label.setText(f"Толщина: {current_well.thickness:.1f} м")
        self.fractures_value_label.setText(f"Трещины: {current_well.fractures_count}")
        self.fracture_width_label.setText(f"Ширина трещины: {current_well.fracture_width:.3f} м")
        self.fracture_length_label.setText(f"Длина трещины: {current_well.fracture_length:.1f} м")
        self.al_ratio_label.setText(f"a/L: {current_well.a_l_ratio:.3f}")
    
    # Обработчики событий для временных рядов
    def on_plot_timeseries(self):
        """Построение графиков временных рядов"""
        current_well = self.current_well_data
        if current_well is None or self.plot_widget is None:
            return
            
        plot_type = self.plot_type_combo.currentText()
        self.plot_widget.clear()
        
        try:
            if plot_type == "Давление vs Время":
                # Проверяем данные на корректность
                if current_well.pressure.isna().all():
                    QMessageBox.warning(self, "Ошибка", "Данные давления содержат только NaN значения")
                    return
                
                # Убираем NaN значения
                valid_mask = ~(current_well.time.isna() | current_well.pressure.isna())
                time_clean = current_well.time[valid_mask]
                pressure_clean = current_well.pressure[valid_mask]
                
                if len(time_clean) == 0:
                    QMessageBox.warning(self, "Ошибка", "Нет корректных данных для построения графика")
                    return
                
                self.plot_widget.plot(pressure_clean, time_clean, pen='b', symbol='o')
                self.plot_widget.setLabel('bottom', 'Давление, атм')
                self.plot_widget.setLabel('left', 'Время, ч')
                self.plot_widget.setTitle('Давление vs Время')
                
            elif plot_type == "Дебит vs Время":
                # Проверяем данные на корректность
                if current_well.flow_rate.isna().all():
                    QMessageBox.warning(self, "Ошибка", "Данные дебита содержат только NaN значения")
                    return
                
                # Убираем NaN значения
                valid_mask = ~(current_well.time.isna() | current_well.flow_rate.isna())
                time_clean = current_well.time[valid_mask]
                flow_rate_clean = current_well.flow_rate[valid_mask]
                
                if len(time_clean) == 0:
                    QMessageBox.warning(self, "Ошибка", "Нет корректных данных для построения графика")
                    return
                
                self.plot_widget.plot(flow_rate_clean, time_clean, pen='g', symbol='s')
                self.plot_widget.setLabel('bottom', 'Дебит, м³/сут')
                self.plot_widget.setLabel('left', 'Время, ч')
                self.plot_widget.setTitle('Дебит vs Время')
                
            elif plot_type == "Производная давления":
                from helpers.grp_analysis import compute_pressure_derivative
                try:
                    dp_dt = compute_pressure_derivative(current_well)
                    
                    # Проверяем, что производная была вычислена
                    if dp_dt.empty:
                        QMessageBox.warning(self, "Ошибка", "Не удалось вычислить производную давления. Проверьте данные.")
                        return
                    
                    # Убираем NaN значения
                    valid_mask = ~(current_well.time.isna() | dp_dt.isna() | np.isinf(dp_dt))
                    time_clean = current_well.time[valid_mask]
                    dp_dt_clean = dp_dt[valid_mask]
                    
                    if len(time_clean) == 0:
                        QMessageBox.warning(self, "Ошибка", "Нет корректных данных для производной давления")
                        return
                    
                    # Используем более безопасный символ для графика
                    self.plot_widget.plot(dp_dt_clean, time_clean, pen='r', symbol='o', symbolSize=4)
                    self.plot_widget.setLabel('bottom', 'dP/dt, атм/ч')
                    self.plot_widget.setLabel('left', 'Время, ч')
                    self.plot_widget.setTitle('Производная давления')
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", f"Ошибка вычисления производной давления: {str(e)}")
                    
            elif plot_type == "Производная дебита":
                from helpers.grp_analysis import compute_flow_rate_derivative
                try:
                    dq_dt = compute_flow_rate_derivative(current_well)
                    
                    # Проверяем, что производная была вычислена
                    if dq_dt.empty:
                        QMessageBox.warning(self, "Ошибка", "Не удалось вычислить производную дебита. Проверьте данные.")
                        return
                    
                    # Убираем NaN значения
                    valid_mask = ~(current_well.time.isna() | dq_dt.isna() | np.isinf(dq_dt))
                    time_clean = current_well.time[valid_mask]
                    dq_dt_clean = dq_dt[valid_mask]
                    
                    if len(time_clean) == 0:
                        QMessageBox.warning(self, "Ошибка", "Нет корректных данных для производной дебита")
                        return
                    
                    # Используем более безопасный символ для графика
                    self.plot_widget.plot(dq_dt_clean, time_clean, pen='m', symbol='s', symbolSize=4)
                    self.plot_widget.setLabel('bottom', 'dQ/dt, м³/сут/ч')
                    self.plot_widget.setLabel('left', 'Время, ч')
                    self.plot_widget.setTitle('Производная дебита')
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", f"Ошибка вычисления производной дебита: {str(e)}")
                    
            elif plot_type == "Давление vs Дебит":
                # Проверяем данные на корректность
                valid_mask = ~(current_well.pressure.isna() | current_well.flow_rate.isna() | 
                              np.isinf(current_well.pressure) | np.isinf(current_well.flow_rate))
                pressure_clean = current_well.pressure[valid_mask]
                flow_rate_clean = current_well.flow_rate[valid_mask]
                
                if len(pressure_clean) == 0:
                    QMessageBox.warning(self, "Ошибка", "Нет корректных данных для построения графика")
                    return
                
                # Используем более безопасный символ для графика
                self.plot_widget.plot(pressure_clean, flow_rate_clean, pen='c', symbol='o', symbolSize=4)
                self.plot_widget.setLabel('bottom', 'Давление, атм')
                self.plot_widget.setLabel('left', 'Дебит, м³/сут')
                self.plot_widget.setTitle('Давление vs Дебит')
                
            elif plot_type == "Безразмерные параметры (X-Y)":
                # Убираем NaN значения
                valid_mask = ~(current_well.time.isna() | current_well.pressure.isna() | current_well.flow_rate.isna())
                time_clean = current_well.time[valid_mask]
                pressure_clean = current_well.pressure[valid_mask]
                flow_rate_clean = current_well.flow_rate[valid_mask]

                if len(time_clean) == 0:
                    QMessageBox.warning(self, "Ошибка", "Нет корректных данных для построения графика")
                    return

                # Вычисляем безразмерные параметры
                X, Y = compute_dimensionless_parameters(current_well, time_clean, pressure_clean, flow_rate_clean)

                # Устанавливаем логарифмические оси
                set_logarithmic_axes(self.plot_widget)

                # Строим график
                self.plot_widget.plot(X, Y, pen='m', symbol='o', symbolSize=4)
                self.plot_widget.setLabel('bottom', 'X - безразмерный фильтрационный параметр')
                self.plot_widget.setLabel('left', 'Y - безразмерный ёмкостной параметр')
                self.plot_widget.setTitle('Безразмерные параметры ГРП (логарифмический масштаб)')

            elif plot_type == "Логарифмический P(t) с инверсией":
                # Убираем NaN значения
                valid_mask = ~(current_well.time.isna() | current_well.pressure.isna())
                time_clean = current_well.time[valid_mask]
                pressure_clean = current_well.pressure[valid_mask]

                if len(time_clean) == 0:
                    QMessageBox.warning(self, "Ошибка", "Нет корректных данных для построения графика")
                    return

                # Устанавливаем логарифмические оси
                set_logarithmic_axes(self.plot_widget)

                # Строим график давления по времени
                self.plot_widget.plot(time_clean, pressure_clean, pen='b', symbol='o')

                # Инвертируем Y-ось (давление уменьшается со временем)
                invert_y_axis(self.plot_widget)

                self.plot_widget.setLabel('bottom', 'Время, ч (лог)')
                self.plot_widget.setLabel('left', 'Давление, атм (лог, инвертировано)')
                self.plot_widget.setTitle('Логарифмический график давления с инверсией')

            elif plot_type == "Логарифмический Q(t)":
                # Убираем NaN значения
                valid_mask = ~(current_well.time.isna() | current_well.flow_rate.isna())
                time_clean = current_well.time[valid_mask]
                flow_rate_clean = current_well.flow_rate[valid_mask]

                if len(time_clean) == 0:
                    QMessageBox.warning(self, "Ошибка", "Нет корректных данных для построения графика")
                    return

                # Устанавливаем логарифмические оси
                set_logarithmic_axes(self.plot_widget)

                # Строим график дебита по времени
                self.plot_widget.plot(time_clean, flow_rate_clean, pen='g', symbol='s')
                self.plot_widget.setLabel('bottom', 'Время, ч (лог)')
                self.plot_widget.setLabel('left', 'Дебит, м³/сут (лог)')
                self.plot_widget.setTitle('Логарифмический график дебита')

            elif plot_type == "Логарифмическая производная P":
                from helpers.grp_analysis import compute_pressure_derivative
                try:
                    dp_dt = compute_pressure_derivative(current_well)

                    # Убираем NaN значения
                    valid_mask = ~(current_well.time.isna() | dp_dt.isna() | np.isinf(dp_dt))
                    time_clean = current_well.time[valid_mask]
                    dp_dt_clean = dp_dt[valid_mask]

                    if len(time_clean) == 0:
                        QMessageBox.warning(self, "Ошибка", "Нет корректных данных для производной давления")
                        return

                    # Устанавливаем логарифмические оси
                    set_logarithmic_axes(self.plot_widget)

                    # Строим график производной давления
                    self.plot_widget.plot(time_clean, dp_dt_clean, pen='r', symbol='o', symbolSize=4)
                    self.plot_widget.setLabel('bottom', 'Время, ч (лог)')
                    self.plot_widget.setLabel('left', 'dP/dt, атм/ч (лог)')
                    self.plot_widget.setTitle('Логарифмическая производная давления')
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", f"Ошибка вычисления производной давления: {str(e)}")
                
        except Exception as e:
            QMessageBox.warning(self, "Ошибка построения графика", f"Ошибка: {str(e)}")
    
    def on_smooth_data(self):
        """Сглаживание данных"""
        if self.well_data is None:
            return
            
        plot_type = self.plot_type_combo.currentText()
        if plot_type in ["Давление vs Время", "Дебит vs Время"]:
            from helpers.timeseries import smooth_series
            
            if plot_type == "Давление vs Время":
                smoothed = smooth_series(self.well_data.pressure, window=5)
                self.well_data.pressure = smoothed
            else:
                smoothed = smooth_series(self.well_data.flow_rate, window=5)
                self.well_data.flow_rate = smoothed
                
            self.on_plot_timeseries()
            QMessageBox.information(self, "Сглаживание", "Данные сглажены")
    
    def on_interpolate_data(self):
        """Интерполяция данных"""
        if self.well_data is None:
            return
        
        # Интерполируем пропуски в данных
        self.well_data.pressure = interpolate_series(self.well_data.pressure)
        self.well_data.flow_rate = interpolate_series(self.well_data.flow_rate)
        
        self.on_plot_timeseries()
        QMessageBox.information(self, "Интерполяция", "Пропуски в данных интерполированы")
    
    def on_ml_interpolate(self):
        """ML-интерполяция данных"""
        if self.well_data is None:
            return
            
        plot_type = self.plot_type_combo.currentText()
        if plot_type in ["Давление vs Время", "Дебит vs Время"]:
            try:
                if plot_type == "Давление vs Время":
                    interpolated = apply_ml_interpolation(self.well_data.time, self.well_data.pressure, 'random_forest')
                    self.well_data.pressure = interpolated
                else:
                    interpolated = apply_ml_interpolation(self.well_data.time, self.well_data.flow_rate, 'random_forest')
                    self.well_data.flow_rate = interpolated
                    
                self.on_plot_timeseries()
                QMessageBox.information(self, "ML интерполяция", "Данные интерполированы с помощью ML")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Ошибка ML интерполяции: {str(e)}")
    
    def on_ml_filter(self):
        """ML-фильтрация данных"""
        if self.well_data is None:
            return
            
        plot_type = self.plot_type_combo.currentText()
        if plot_type in ["Давление vs Время", "Дебит vs Время"]:
            try:
                if plot_type == "Давление vs Время":
                    filtered = apply_ml_filter(self.well_data.pressure, 'savitzky_golay', window_length=5, polyorder=2)
                    self.well_data.pressure = filtered
                else:
                    filtered = apply_ml_filter(self.well_data.flow_rate, 'savitzky_golay', window_length=5, polyorder=2)
                    self.well_data.flow_rate = filtered
                    
                self.on_plot_timeseries()
                QMessageBox.information(self, "ML фильтрация", "Данные отфильтрованы с помощью ML")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Ошибка ML фильтрации: {str(e)}")
    
    def on_detect_outliers(self):
        """Обнаружение выбросов"""
        if self.well_data is None:
            return

        plot_type = self.plot_type_combo.currentText()
        if plot_type in ["Давление vs Время", "Дебит vs Время"]:
            try:
                if plot_type == "Давление vs Время":
                    outliers = detect_outliers(self.well_data.pressure, 'iqr', threshold=1.5)
                    outlier_count = outliers.sum()
                else:
                    outliers = detect_outliers(self.well_data.flow_rate, 'iqr', threshold=1.5)
                    outlier_count = outliers.sum()
                
                    self.plot_outliers_with_highlight(outliers, plot_type)
                QMessageBox.information(self, "Обнаружение выбросов", f"Найдено {outlier_count} выбросов")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Ошибка обнаружения выбросов: {str(e)}")
    
    def plot_outliers_with_highlight(self, outliers: pd.Series, plot_type: str):
        """Построение графика с выделенными выбросами"""
        self.plot_widget.clear()
        
        if plot_type == "Давление vs Время":
            # Обычные точки
            normal_mask = ~outliers
            self.plot_widget.plot(self.well_data.pressure[normal_mask],
                                self.well_data.time[normal_mask],
                                pen='b', symbol='o', symbolSize=5)
            
            # Выбросы
            if outliers.any():
                self.plot_widget.plot(self.well_data.pressure[outliers],
                                    self.well_data.time[outliers],
                                    pen=None, symbol='x', symbolSize=10, symbolBrush='r')
            
            self.plot_widget.setLabel('bottom', 'Давление, атм')
            self.plot_widget.setLabel('left', 'Время, ч')
            self.plot_widget.setTitle('Давление vs Время (красные X - выбросы)')
            
        else:  # Дебит vs Время
            normal_mask = ~outliers
            self.plot_widget.plot(self.well_data.flow_rate[normal_mask],
                                self.well_data.time[normal_mask],
                                pen='g', symbol='s', symbolSize=5)
            
            if outliers.any():
                self.plot_widget.plot(self.well_data.flow_rate[outliers],
                                    self.well_data.time[outliers],
                                    pen=None, symbol='x', symbolSize=10, symbolBrush='r')
            
            self.plot_widget.setLabel('bottom', 'Дебит, м³/сут')
            self.plot_widget.setLabel('left', 'Время, ч')
            self.plot_widget.setTitle('Дебит vs Время (красные X - выбросы)')
    
    def on_export_data(self):
        """Экспорт данных"""
        if self.well_data is None:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт данных", "", "CSV файлы (*.csv)")

        if file_path:
            try:
                # Создаем DataFrame для экспорта
                export_df = pd.DataFrame({
                    'Time': self.well_data.time,
                    'Pressure': self.well_data.pressure,
                    'FlowRate': self.well_data.flow_rate
                })
                export_df.to_csv(file_path, index=False)
                QMessageBox.information(self, "Экспорт", "Данные успешно экспортированы")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка экспорта", f"Не удалось экспортировать данные: {str(e)}")
    
    def on_analyze_flow_regime(self):
        """Анализ режима течения"""
        if self.well_data is None:
            return
            
        from helpers.grp_analysis import analyze_flow_regime
        analysis = analyze_flow_regime(self.well_data)
        
        result_text = f"""
Анализ режима течения:
Тип режима: {analysis.regime_type}
Уверенность: {analysis.confidence:.2f}
Характерное время: {analysis.characteristic_time or 'Не определено'}

Параметры:
{chr(10).join([f'{k}: {v}' for k, v in analysis.parameters.items()])}
"""

        QMessageBox.information(self, "Анализ режима течения", result_text)

    def on_compute_productivity(self):
        """Вычисление индекса продуктивности"""
        if self.well_data is None:
            return

        from helpers.grp_analysis import compute_well_productivity_index
        productivity = compute_well_productivity_index(self.well_data)

        result_text = f"""
Индекс продуктивности скважины:
Индекс продуктивности: {productivity['productivity_index']:.4f}
Эффективность ГРП: {productivity['fracture_efficiency']:.4f}
Средний дебит: {productivity['average_flow_rate']:.2f} м³/сут
Среднее давление: {productivity['average_pressure']:.2f} атм
Влияние скин-эффекта: {productivity['skin_impact']:.4f}
Общая длина трещин: {productivity['total_fracture_length']:.2f} м
"""

        QMessageBox.information(self, "Индекс продуктивности", result_text)

    def on_detect_transitions(self):
        """Обнаружение переходов режимов"""
        if self.well_data is None:
            return

        from helpers.grp_analysis import detect_flow_regime_transitions
        transitions = detect_flow_regime_transitions(self.well_data)

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

        QMessageBox.information(self, "Переходы режимов", result_text)

    def on_plot_bilinear(self):
        """Построение кривой билинейного течения"""
        if self.well_data is None or self.type_curves_widget is None:
            return

        from helpers.grp_analysis import generate_type_curves
        time_range = np.logspace(-1, 3, 100)
        curves = generate_type_curves(self.well_data.skin, self.well_data.fractures_count,
                                     self.well_data.a_l_ratio, time_range)

        self.type_curves_widget.clear()
        time_curve, pressure_curve = curves['bilinear']
        self.type_curves_widget.plot(time_curve, pressure_curve, pen='b', name='Билинейное течение')
        self.type_curves_widget.setLabel('left', 'Давление, атм')
        self.type_curves_widget.setLabel('bottom', 'Время, ч')
        self.type_curves_widget.setTitle('Билинейное течение')

    def on_plot_linear(self):
        """Построение кривой линейного течения"""
        if self.well_data is None or self.type_curves_widget is None:
            return

        from helpers.grp_analysis import generate_type_curves
        time_range = np.logspace(-1, 3, 100)
        curves = generate_type_curves(self.well_data.skin, self.well_data.fractures_count,
                                     self.well_data.a_l_ratio, time_range)

        self.type_curves_widget.clear()
        time_curve, pressure_curve = curves['linear']
        self.type_curves_widget.plot(time_curve, pressure_curve, pen='g', name='Линейное течение')
        self.type_curves_widget.setLabel('left', 'Давление, атм')
        self.type_curves_widget.setLabel('bottom', 'Время, ч')
        self.type_curves_widget.setTitle('Линейное течение')

    def on_plot_pseudoradial(self):
        """Построение кривой псевдорадиального течения"""
        if self.well_data is None or self.type_curves_widget is None:
            return

        from helpers.grp_analysis import generate_type_curves
        time_range = np.logspace(-1, 3, 100)
        curves = generate_type_curves(self.well_data.skin, self.well_data.fractures_count,
                                     self.well_data.a_l_ratio, time_range)

        self.type_curves_widget.clear()
        time_curve, pressure_curve = curves['pseudoradial']
        self.type_curves_widget.plot(time_curve, pressure_curve, pen='r', name='Псевдорадиальное течение')
        self.type_curves_widget.setLabel('left', 'Давление, атм')
        self.type_curves_widget.setLabel('bottom', 'Время, ч')
        self.type_curves_widget.setTitle('Псевдорадиальное течение')

    def on_match_curves(self):
        """Сопоставление с эталонными кривыми"""
        if self.well_data is None:
            return

        from helpers.grp_analysis import match_type_curves
        match_result = match_type_curves(self.well_data)

        result_text = f"""
Сопоставление с эталонными кривыми:
Лучшее совпадение: {match_result.curve_type}
Качество совпадения: {match_result.match_quality:.2f}

Оцененные параметры:
{chr(10).join([f'{k}: {v}' for k, v in match_result.estimated_parameters.items()])}
"""

        QMessageBox.information(self, "Сопоставление кривых", result_text)

    def on_export_report(self):
        """Экспорт отчета"""
        if self.well_data is None:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт отчета", "", "Текстовые файлы (*.txt)")

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("ОТЧЕТ АНАЛИЗА ДАННЫХ ГРП\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Скважина: Skin={self.well_data.skin:.3f}, "
                           f"N={self.well_data.fractures_count}, "
                           f"a/L={self.well_data.a_l_ratio:.3f}\n\n")

                    # Анализ режима течения
                    from helpers.grp_analysis import analyze_flow_regime
                    analysis = analyze_flow_regime(self.well_data)
                    f.write(f"Режим течения: {analysis.regime_type}\n")
                    f.write(f"Уверенность: {analysis.confidence:.2f}\n")
                    f.write(f"Характерное время: {analysis.characteristic_time or 'Не определено'}\n\n")

                    # Индекс продуктивности
                    from helpers.grp_analysis import compute_well_productivity_index
                    productivity = compute_well_productivity_index(self.well_data)
                    f.write("Индекс продуктивности:\n")
                    f.write(f"  Индекс продуктивности: {productivity['productivity_index']:.4f}\n")
                    f.write(f"  Эффективность ГРП: {productivity['fracture_efficiency']:.4f}\n")
                    f.write(f"  Средний дебит: {productivity['average_flow_rate']:.2f} м³/сут\n")
                    f.write(f"  Среднее давление: {productivity['average_pressure']:.2f} атм\n\n")

                QMessageBox.information(self, "Экспорт отчета", "Отчет успешно экспортирован")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка экспорта", f"Не удалось экспортировать отчет: {str(e)}")

    def _get_data(self):
        """Возвращает время и выбранный показатель (старый метод)"""
        if self.well_data is None:
            return None, None
        return self.well_data.time, self.well_data.pressure

    def _plot_data(self, values, times, title: str = ""):
        """Отрисовка графика (старый метод)"""
        if self.plot_widget is None:
            return
        self.plot_widget.clear()
        self.plot_widget.plot(values, times, pen='b')
        if title:
            self.plot_widget.setTitle(title)

    def on_plot(self):
        """Старый метод построения графиков"""
        if self.well_data is None:
            return
        time_data, pressure_data = self._get_data()
        if time_data is not None and pressure_data is not None:
            self._plot_data(pressure_data, time_data, "Давление vs Время")

    def on_derivative(self):
        """Старый метод вычисления производной"""
        if self.well_data is None:
            return
        self.plot_type_combo.setCurrentText("Производная давления")
        self.on_plot_timeseries()

    def on_interpolate(self):
        """Старый метод интерполяции"""
        if self.well_data is None:
            return
        self.plot_type_combo.setCurrentText("Давление vs Время")
        self.on_interpolate_data()

    def on_smooth(self):
        """Старый метод сглаживания"""
        if self.well_data is None:
            return
        self.plot_type_combo.setCurrentText("Давление vs Время")
        self.on_smooth_data()

    def setup_grp_analysis(self):
        """Настройка ГРП-анализа (старый метод)"""
        pass

    def on_grp_analysis(self):
        """Старый метод анализа ГРП"""
        pass

    def on_type_curves(self):
        """Старый метод эталонных кривых"""
        pass

    def on_ml_prediction(self):
        """Старый метод ML прогноза"""
        pass


def compute_dimensionless_parameters(time_series: WellTimeSeries, time_clean, pressure_clean, flow_rate_clean):
        """
        Вычисляет безразмерные параметры для анализа ГРП.

        X = (0.00864 * k * h * ∆p_i) / (μ * B * Q)
        Y = Q * B * t / (24 * φ * c_t * h * L² * ∆p_i)

        Использует типичные значения для нефти:
        k = 10 мД, μ = 1 сП, B = 1.2, φ = 0.15, c_t = 10^-5 1/атм
        """
        # Типичные значения для нефти
        k = 10e-15  # проницаемость, м² (10 мД)
        mu = 0.001  # вязкость, Па*с (1 сП)
        B = 1.2     # объемный коэффициент нефти
        phi = 0.15  # пористость
        ct = 1e-5   # общая сжимаемость, 1/атм

        h = time_series.thickness  # толщина пласта
        L = time_series.fracture_length  # длина трещины

        # Начальное изменение давления (используем среднее давление как приближение)
        delta_p_i = pressure_clean.mean() if len(pressure_clean) > 0 else 1.0

        # Защита от деления на ноль
        delta_p_i = max(delta_p_i, 1.0)

        # Безразмерный фильтрационный параметр X
        denominator = mu * B * flow_rate_clean
        denominator = np.where(denominator == 0, 1e-10, denominator)

        X = (0.00864 * k * h * delta_p_i) / denominator

        # Безразмерный ёмкостной параметр Y
        numerator = flow_rate_clean * B * time_clean
        denominator_y = 24 * phi * ct * h * L**2 * delta_p_i
        denominator_y = max(denominator_y, 1e-10)  # защита от нуля

        Y = numerator / denominator_y

        return X, Y


def set_logarithmic_axes(plot_widget):
        """Устанавливает логарифмические оси для графика."""
        try:
            plot_widget.setLogMode(x=True, y=True)
        except Exception:
            # Если не удается установить логарифмический режим
            pass


def invert_y_axis(plot_widget):
    """Инвертирует Y-ось графика."""
    try:
        # Получаем текущий диапазон Y
        y_range = plot_widget.getAxis('left').range
        if y_range:
            # Инвертируем диапазон
            plot_widget.setYRange(y_range[1], y_range[0])
    except Exception:
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())