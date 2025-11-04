import sys
import pandas as pd
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (QLabel, QTableView, QApplication, QMainWindow, QFileDialog, QMessageBox, 
                               QComboBox, QSpinBox, QPushButton, QWidget, QVBoxLayout, 
                               QHBoxLayout, QTabWidget, QTextEdit, QGroupBox, QGridLayout,
                               QCheckBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem

from ui import Ui_mainWindow

from helpers.parse_well_data import parse_well_data
from helpers.ml_methods import (apply_ml_interpolation, apply_ml_filter, 
                               detect_outliers)
from helpers.dimensionless_analysis import convert_to_dimensionless_curves
from helpers.dimensionless_plotting import plot_dimensionless_grouped
from helpers.dimensionless_interpolating import DimensionlessCurveInterpolator                                                                                         
from schemas.well_data import WellTimeSeries



class MyApp(QMainWindow, Ui_mainWindow):
    def __init__(self, test_mode=False):
        super().__init__()
        self.setupUi(self)
        
        self.test_mode = test_mode  # Флаг для отключения сообщений в тестах
        self.resize(1400, 900)
        # Переименуем существующую кнопку и подключим обработчик
        try:
            self.load_template_button.setText("Загрузить основной файл")
        except Exception:
            pass
        self.load_template_button.clicked.connect(self.load_template)
        self.well_data_list = []  # Список WellTimeSeries объектов
        self.current_well_index = 0  # Индекс текущей скважины
        self.validation_well_data_list = []  # Данные для проверки качества интерполяции
        
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
    
    def show_info(self, title, message):
        """Показывает информационное сообщение (только если не test_mode)"""
        if not self.test_mode:
            QMessageBox.information(self, title, message)
    
    def show_warning(self, title, message):
        """Показывает предупреждение (только если не test_mode)"""
        if not self.test_mode:
            QMessageBox.warning(self, title, message)
    
    def show_error(self, title, message):
        """Показывает сообщение об ошибке (только если не test_mode)"""
        if not self.test_mode:
            QMessageBox.critical(self, title, message)
    
    def _get_well_params(self, well: WellTimeSeries, 
                        default_k: float = 1.0, 
                        default_mu: float = 1.0, 
                        default_B: float = 1.0,
                        default_phi: float = 0.1, 
                        default_c_t: float = 1e-4) -> dict:
        """Создает словарь параметров скважины для безразмерного анализа"""
        return {
            'k': default_k,
            'h': well.thickness,
            'mu': default_mu,
            'B': default_B,
            'phi': default_phi,
            'c_t': default_c_t,
            'L': well.fracture_length,
            'skin': well.skin,
            'N': well.fractures_count,
            'a_L': well.a_l_ratio
        }

    def setup_professional_interface(self):
        """Создает профессиональный интерфейс с вкладками для анализа ГРП"""
        # Основной контейнер с вкладками
        self.tab_widget = QTabWidget(self.centralwidget)
        self.tab_widget.setGeometry(350, 20, 1150, 900)
        
        # Вкладка 1: Временные ряды
        self.timeseries_tab = self.setup_timeseries_tab()  # ← присваиваем возвращённый QWidget
        self.tab_widget.addTab(self.timeseries_tab, "Безразмерные кривые")  # можно переименовать вкладку
        
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
        """Вкладка для безразмерных графиков в стиле Kappa Sapphire."""
        tab = QWidget()
        
        # ОСНОВНОЙ ЛАЙАУТ С РАЗДЕЛЕНИЕМ ПО ГОРИЗОНТАЛИ
        main_layout = QHBoxLayout(tab)
        main_layout.setContentsMargins(5, 5, 5, 5)  # минимальные отступы

        # --- ЛЕВАЯ ПАНЕЛЬ: управление ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_panel.setMaximumWidth(300)  # фиксированная ширина

        # --- Загрузка файлов ---
        load_group = QGroupBox("Загрузка данных")
        load_layout = QGridLayout(load_group)
        self.load_validation_button = QPushButton("Загрузить файл для проверки")
        load_layout.addWidget(self.load_validation_button, 0, 0)
        left_layout.addWidget(load_group)

        # --- Кнопки анализа СВЕРХУ ---
        buttons_group = QGroupBox("Управление")
        buttons_layout = QGridLayout(buttons_group)
        self.plot_btn = QPushButton("Построить график")
        self.interp_btn = QPushButton("Интерполяция")
        self.ml_filter_btn = QPushButton("ML фильтрация")
        self.outlier_btn = QPushButton("Обнаружить выбросы")
        self.export_btn = QPushButton("Экспорт данных")

        buttons_layout.addWidget(self.plot_btn, 0, 0)
        buttons_layout.addWidget(self.interp_btn, 0, 1)
        buttons_layout.addWidget(self.ml_filter_btn, 1, 0)
        buttons_layout.addWidget(self.outlier_btn, 1, 1)
        buttons_layout.addWidget(self.export_btn, 2, 0)
        left_layout.addWidget(buttons_group)

        # --- Выбор скважины ---
        well_group = QGroupBox("Выбор скважины")
        well_layout = QVBoxLayout(well_group)
        self.well_combo_dim = QComboBox()
        well_layout.addWidget(self.well_combo_dim)
        left_layout.addWidget(well_group)

        # --- Панель чекбоксов ---
        controls_group = QGroupBox("Отображение (группы)")
        controls_layout = QVBoxLayout(controls_group)

        # Реальные параметры
        self.grp_real = QGroupBox("Реальные параметры")
        real_lay = QVBoxLayout(self.grp_real)
        self.cb_real_p = QCheckBox("P(t)")
        self.cb_real_q = QCheckBox("Q(t)")
        self.cb_real_t = QCheckBox("t (ось)")
        real_lay.addWidget(self.cb_real_p)
        real_lay.addWidget(self.cb_real_q)
        real_lay.addWidget(self.cb_real_t)
        controls_layout.addWidget(self.grp_real)

        # Безразмерные (log-log)
        self.grp_dim = QGroupBox("Безразмерные (log-log)")
        dim_lay = QVBoxLayout(self.grp_dim)
        self.cb_dim_pD = QCheckBox("pD(Y)")
        self.cb_dim_dpD = QCheckBox("dpD/dlogY")
        self.cb_dim_tD = QCheckBox("tD (≈Y)")
        self.cb_dim_CD = QCheckBox("CD (ёмкость)")
        dim_lay.addWidget(self.cb_dim_pD)
        dim_lay.addWidget(self.cb_dim_dpD)
        dim_lay.addWidget(self.cb_dim_tD)
        dim_lay.addWidget(self.cb_dim_CD)
        controls_layout.addWidget(self.grp_dim)

        # Спец-пространства и типовые кривые
        self.grp_special = QGroupBox("Спец-пространства/типовые")
        sp_lay = QVBoxLayout(self.grp_special)
        self.cb_gfunc = QCheckBox("G-функция (Nolte)")
        self.cb_mbt = QCheckBox("Время материального баланса")
        self.cb_type_gry = QCheckBox("Билинейный режим")
        self.cb_type_cinco = QCheckBox("Линейный режим течения")
        self.cb_type_valko = QCheckBox("Псевдорадиальный режим")
        sp_lay.addWidget(self.cb_gfunc)
        sp_lay.addWidget(self.cb_mbt)
        sp_lay.addWidget(self.cb_type_gry)
        sp_lay.addWidget(self.cb_type_cinco)
        sp_lay.addWidget(self.cb_type_valko)
        controls_layout.addWidget(self.grp_special)

        # По умолчанию включим pD(Y)
        self.cb_dim_pD.setChecked(True)
        left_layout.addWidget(controls_group)

        # --- Отчёт ПОД ЧЕКБОКСАМИ ---
        report_group = QGroupBox("Отчёт")
        report_layout = QVBoxLayout(report_group)
        self.text_report = QTextEdit()
        self.text_report.setReadOnly(True)
        self.text_report.setPlaceholderText("Здесь появится отчёт...")
        report_layout.addWidget(self.text_report)
        left_layout.addWidget(report_group)

        # Растягиваем отчёт вниз
        left_layout.addStretch()

        # --- ПРАВАЯ ПАНЕЛЬ: график ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # График занимает всё доступное пространство
        self.dimensionless_plot = pg.PlotWidget()
        self.dimensionless_plot.showGrid(x=True, y=True)
        

        self.dimensionless_plot.setLabel('bottom', 'X  безразмерный фильтрационный параметр')  # ← СНИЗУ X
        self.dimensionless_plot.setLabel('left', '•	Y  безразмерный ёмкостной параметр')  # ← СЛЕВА Y
        self.dimensionless_plot.setTitle("Безразмерные кривые МГРП")
        
        right_layout.addWidget(self.dimensionless_plot)

        # --- Собираем основной интерфейс ---
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, stretch=1)  # график растягивается

        tab.setLayout(main_layout)
        return tab

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
        self.grp_results_text.setMaximumHeight(300)
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
    
    def setup_data_tab(self):
        """Вкладка для просмотра загруженных данных (только чтение)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Таблица для отображения данных
        self.data_table = QTableView()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(self.data_table.SelectionBehavior.SelectRows)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.data_table)

        # Текстовое поле для информации (например, имя файла или статистика)
        self.data_info_label = QLabel("Здесь появится информация о загруженных данных")
        self.data_info_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.data_info_label)

        tab.setLayout(layout)
        return tab
    
    def setup_event_handlers(self):
        """Настройка обработчиков событий"""
        # Временные ряды
        self.plot_btn.clicked.connect(self.on_plot_dimensionless_selected)
        self.interp_btn.clicked.connect(self.on_interpolate_data)
        self.ml_filter_btn.clicked.connect(self.on_ml_filter)
        self.outlier_btn.clicked.connect(self.on_detect_outliers)
        self.export_btn.clicked.connect(self.on_export_data)
        self.load_validation_button.clicked.connect(self.load_validation_file)
        
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

        self.data_tab = self.setup_data_tab()
        self.tab_widget.addTab(self.data_tab, "Загруженные данные")

    def load_template(self):
        """Загрузка CSV файла с данными разведки месторождений"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Загрузить файл данных", "./", 
                                                 "Data Files (*.csv *.parquet);;CSV Files (*.csv);;Parquet Files (*.parquet);;All Files (*)")
        if not file_path:
            return

        # Парсим данные скважины
        try:
            well_data_list, error_msg = parse_well_data(file_path)
            if error_msg is not None:
                self.show_warning("Ошибка загрузки", error_msg)
                return
        except Exception as e:
            self.show_warning("Ошибка загрузки", f"Неожиданная ошибка при загрузке файла: {str(e)}")
            return

        self.well_data_list = well_data_list
        self.current_well_index = 0
        
        # Обновляем список выбора скважин
        self.update_well_selection()
        
        # Обновляем отображение параметров ГРП
        self.update_grp_parameters()
        
        # Обновляем вкладку с загруженными данными
        self.update_data_tab()
        
        # Обновляем старые поля для совместимости
        current_well = self.current_well_data
        if current_well:
            self.update_interface_parameters()
        
        # Показываем информацию о загруженных данных
        total_points = sum(len(well.time) for well in well_data_list)
        self.show_info("Данные загружены", 
                      f"Загружено {len(well_data_list)} групп данных\n"
                      f"Всего измерений: {total_points}\n"
                      f"Текущая скважина: {self.well_combo_dim.currentText()}")
        
        # Запускаем диагностику асинхронно
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self.run_data_diagnostics(file_path))
        
        # ФИКС: Автоматически строим безразмерный график
        self.on_plot_dimensionless_selected()
        
        # Обновляем комбо в новой вкладке
        self.well_combo_dim.clear()
        for i, well in enumerate(self.well_data_list):
            self.well_combo_dim.addItem(f"Скважина {i+1} (Skin={well.skin:.2f})")

    def load_validation_file(self):
        """Загрузка файла для проверки качества интерполяции."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Загрузить файл для проверки", "./", 
                                                 "Data Files (*.csv *.parquet);;CSV Files (*.csv);;Parquet Files (*.parquet);;All Files (*)")
        if not file_path:
            return

        try:
            well_data_list, error_msg = parse_well_data(file_path)
            if error_msg is not None:
                self.show_warning("Ошибка загрузки", error_msg)
                return
        except Exception as e:
            self.show_warning("Ошибка загрузки", f"Неожиданная ошибка при загрузке файла: {str(e)}")
            return

        self.validation_well_data_list = well_data_list
        self.show_info("Файл для проверки", 
                      f"Загружено {len(well_data_list)} групп данных для проверки\n"
                      f"Всего измерений: {sum(len(w.time) for w in well_data_list)}")
    
    def run_data_diagnostics(self, file_path):
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
                if self.well_data_list and len(self.well_data_list) > 0:
                    well = self.well_data_list[0]
                    # Конвертируем в безразмерные параметры
                    from helpers.dimensionless_analysis import convert_to_dimensionless_curves
                    well_params = self._get_well_params(well)
                    dim_data = convert_to_dimensionless_curves(
                        well.time, well.pressure, well.flow_rate, well_params
                    )
                    
                    # Создаем DataFrame в нужном формате
                    df_diag = pd.DataFrame({
                        'X': dim_data.X,
                        'Y': dim_data.Y,
                        'P': dim_data.pressure,
                        'Q': dim_data.flow_rate,
                        't': well.time
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
    
    def update_interface_parameters(self):
        self.thickness_doubleSpinBox.setValue(self.current_well_data.thickness)
        self.skin_doubleSpinBox.setValue(self.current_well_data.skin)
        self.width_doubleSpinBox.setValue(self.current_well_data.fracture_width)
        self.n_spinBox.setValue(self.current_well_data.fractures_count)
        self.aL_doubleSpinBox.setValue(self.current_well_data.a_l_ratio)
    def update_data_tab(self):
        """Обновляет таблицу на вкладке 'Загруженные данные'"""
        if not self.well_data_list:
            self.data_info_label.setText("Нет загруженных данных")
            self.data_table.setModel(None)
            return

        # Преобразуем данные текущей скважины в DataFrame
        current_well = self.current_well_data
        df = pd.DataFrame({
            "time": current_well.time,
            "pressure": current_well.pressure,
            "rate": current_well.flow_rate
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
        self.data_info_label.setText(f"Отображены данные скважины {self.current_well_index + 1} — {len(df)} строк")

        
    def update_well_selection(self):
        """Обновляет список выбора скважин"""
        self.well_combo_dim.clear()
        
        for i, well_data in enumerate(self.well_data_list):
            well_name = f"Скважина {i+1} (Skin={well_data.skin:.3f}, N={well_data.fractures_count})"
            self.well_combo_dim.addItem(well_name)
        
        if self.well_data_list:
            self.well_combo_dim.setCurrentIndex(self.current_well_index)
    
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
    
    def on_interpolate_data(self):
        """Интерполяция данных безразмерных кривых"""
        if self.well_data is None:
            return
        
        # Проверяем, есть ли пропуски в данных
        has_nan = (self.well_data.pressure.isna().any() or 
                   self.well_data.flow_rate.isna().any())
        
        if not has_nan:
            # Данные уже полные, интерполяция не требуется
            report = "=" * 60 + "\n"
            report += "ИНТЕРПОЛЯЦИЯ НЕ ТРЕБУЕТСЯ\n"
            report += "=" * 60 + "\n\n"
            report += "Данные не содержат пропущенных значений (NaN).\n"
            report += f"Точек данных по давлению: {len(self.well_data.pressure)}\n"
            report += f"Точек данных по дебиту: {len(self.well_data.flow_rate)}\n"
            report += "\nВсе данные присутствуют, интерполяция не нужна.\n"
            report += "=" * 60 + "\n"
            
            if hasattr(self, 'results_text'):
                self.results_text.setPlainText(report)
            
            self.show_info("Интерполяция", 
                          "Данные уже полные, интерполяция не требуется")
            return
        
        try:
            # Подсчитываем количество пропусков
            n_nan_pressure = self.well_data.pressure.isna().sum()
            n_nan_flow = self.well_data.flow_rate.isna().sum()
            
            # Используем интерполяцию безразмерных кривых вместо простой математики
            well_params = self._get_well_params(self.well_data)
            
            # Конвертируем в безразмерные параметры
            from helpers.dimensionless_analysis import convert_to_dimensionless_curves
            dim_data = convert_to_dimensionless_curves(
                self.well_data.time, self.well_data.pressure, self.well_data.flow_rate, well_params
            )
            
            # Используем интерполятор безразмерных кривых для восстановления пропусков
            from helpers.dimensionless_interpolating import DimensionlessCurveInterpolator
            
            # Для интерполяции используем текущие параметры
            param_grid = np.array([[self.well_data.skin, self.well_data.fractures_count, self.well_data.a_l_ratio]])
            Y_grid = dim_data.Y
            P_curves = np.asarray([dim_data.pressure / (dim_data.delta_p_i if dim_data.delta_p_i != 0 else 1.0)])
            
            interp = DimensionlessCurveInterpolator(methods=('rbf', 'gp'))
            interp.fit(param_grid, Y_grid, P_curves)
            
            # Предсказываем для тех же параметров (восстанавливаем пропуски)
            pred_series = interp.predict(
                skin=self.well_data.skin,
                N=self.well_data.fractures_count,
                a_L=self.well_data.a_l_ratio
            )
            
            # Восстанавливаем физические величины из безразмерных
            pressure_values = pred_series.values if hasattr(pred_series, 'values') else np.asarray(pred_series)
            self.well_data.pressure = pd.Series(pressure_values * dim_data.delta_p_i, index=self.well_data.time)
            
            # Получаем информацию о результатах интерполяции
            interp_info = interp.get_interpolation_info()
            
            # Сохраняем информацию для отображения в резюме графика
            self.last_interpolation_info = interp_info
            
            # Формируем отчёт для вывода
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
            
            report = "=" * 60 + "\n"
            report += "РЕЗУЛЬТАТЫ ИНТЕРПОЛЯЦИИ БЕЗРАЗМЕРНЫХ КРИВЫХ\n"
            report += "=" * 60 + "\n\n"
            
            # Что было интерполировано
            report += "Интерполировано:\n"
            if interpolated_items:
                report += "  ✓ Безразмерная кривая pD(Y)\n"
                for item in interpolated_items:
                    report += f"  ✓ {item}\n"
            report += "\n"
            
            # Исходные данные
            report += "Исходные данные:\n"
            report += f"  Всего точек: {len(self.well_data.time)}\n"
            total_possible = len(self.well_data.time) * 2  # давление + дебит
            total_nan = n_nan_pressure + n_nan_flow
            coverage = (1 - total_nan / total_possible) * 100 if total_possible > 0 else 0
            report += f"  Полнота данных: {coverage:.1f}%\n"
            report += f"  Заполнено пропусков:\n"
            if n_nan_pressure > 0:
                report += f"    - Давление: {n_nan_pressure} точек ({n_nan_pressure/len(self.well_data.time)*100:.1f}%)\n"
            if n_nan_flow > 0:
                report += f"    - Дебит: {n_nan_flow} точек ({n_nan_flow/len(self.well_data.time)*100:.1f}%)\n"
            report += "\n"
            
            # Параметры скважины (не интерполировались)
            report += "Параметры скважины (использованы для интерполяции):\n"
            report += f"  Skin: {self.well_data.skin:.4f}\n"
            report += f"  N (кол-во трещин): {self.well_data.fractures_count}\n"
            report += f"  a/L: {self.well_data.a_l_ratio:.4f}\n"
            report += f"  L (длина трещины): {self.well_data.fracture_length:.2f} м\n"
            report += f"  h (толщина пласта): {self.well_data.thickness:.2f} м\n"
            report += "\n"
            
            # Параметры интерполяции
            report += "Параметры метода:\n"
            report += f"  Обучающих примеров: {interp_info['n_samples']}\n"
            report += f"  Точек на безразмерной кривой: {interp_info['n_points']}\n\n"
            
            # Сравнение методов
            report += "СРАВНЕНИЕ МЕТОДОВ ИНТЕРПОЛЯЦИИ\n"
            report += "-" * 60 + "\n"
            report += f"{'Метод':<42} {'RMSE':<12} {'Статус'}\n"
            report += "-" * 60 + "\n"
            
            # Сортируем методы по RMSE
            sorted_methods = sorted(interp_info['rmse_scores'].items(), key=lambda x: x[1])
            
            for i, (method, rmse) in enumerate(sorted_methods, 1):
                method_display = method_names.get(method, method)
                marker = "✓ ВЫБРАН" if method == interp_info['best_method'] else f"#{i}"
                report += f"{method_display:<42} {rmse:<12.3f} {marker}\n"
            
            report += "-" * 60 + "\n\n"
            
            # Итоговая информация
            best_rmse = interp_info['rmse_scores'].get(interp_info['best_method'], 0)
            report += "ИТОГОВЫЙ РЕЗУЛЬТАТ:\n"
            report += f"  Метод: {method_names.get(interp_info['best_method'], interp_info['best_method'])}\n"
            report += f"  RMSE: {best_rmse:.3f}\n"
            report += f"  Качество: {'Отлично' if best_rmse < 0.01 else 'Хорошо' if best_rmse < 0.1 else 'Удовлетворительно'}\n"
            report += "\n" + "=" * 60 + "\n"
            
            # Выводим в текстовое поле результатов
            if hasattr(self, 'results_text'):
                self.results_text.setPlainText(report)
            
            self.on_plot_dimensionless_selected()
            best_rmse = interp_info['rmse_scores'].get(interp_info['best_method'], 0)
            self.show_info("Интерполяция", 
                          f"Данные интерполированы методом безразмерных кривых\n\n"
                          f"Выбранный метод: {method_names.get(interp_info['best_method'], interp_info['best_method'])}\n"
                          f"RMSE: {best_rmse:.3f}\n"
                          f"Качество: {'Отлично' if best_rmse < 0.01 else 'Хорошо' if best_rmse < 0.1 else 'Удовлетворительно'}")
        except Exception as e:
            self.show_warning("Ошибка", f"Ошибка интерполяции: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    def on_plot_dimensionless_selected(self):
        """Обработка нажатия на кнопку 'Построить график'."""
        self.dimensionless_plot.clear()
        self.text_report.clear()

        current_well = self.current_well_data
        if current_well is None:
            self.text_report.setText("❌ Нет данных для построения.")
            return

        try:
            # Параметры скважины
            well_params = self._get_well_params(current_well)
            
            # 1️⃣ Конвертация в безразмерные параметры
            dim_data = convert_to_dimensionless_curves(
                current_well.time, current_well.pressure, current_well.flow_rate, well_params
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
            
            # 3️⃣ Подготовка данных для валидации
            validation_data = None
            if self.validation_well_data_list:
                try:
                    ref_well = self.validation_well_data_list[0]
                    ref_params = self._get_well_params(ref_well)
                    ref_dim = convert_to_dimensionless_curves(
                        ref_well.time, ref_well.pressure, ref_well.flow_rate, ref_params
                    )
                    validation_data = {'ref_dim': ref_dim}
                except Exception as e:
                    self.text_report.append(f"⚠️ Ошибка подготовки данных валидации: {e}")
            
            # 4️⃣ Используем новую функцию для отображения сгруппированных графиков
            plot_dimensionless_grouped(
                plot_widget=self.dimensionless_plot,
                dim_data=dim_data,
                current_well_time=current_well.time,
                current_well_pressure=current_well.pressure,
                current_well_flow_rate=current_well.flow_rate,
                checked_groups=checked_groups,
                validation_data=validation_data
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
                quality = 'отлично' if best_rmse < 0.01 else 'хорошо' if best_rmse < 0.1 else 'удовл.'
                self.text_report.append(
                    f"📊 Интерполяция: {method_names.get(interp_info['best_method'], interp_info['best_method'])}, "
                    f"RMSE={best_rmse:.3f} ({quality})"
                )
            
        except Exception as e:
            self.text_report.setText(f"❌ Ошибка построения графика: {str(e)}")
            import traceback
            print(traceback.format_exc())        

    def on_ml_filter(self):
        """ML-фильтрация данных"""
        if self.well_data is None:
            return
            
        try:
            filtered = apply_ml_filter(self.well_data.pressure, 'savitzky_golay', window_length=5, polyorder=2)
            self.well_data.pressure = filtered
            self.on_plot_dimensionless_selected()
            self.show_info("ML фильтрация", "Данные отфильтрованы с помощью ML")
        except Exception as e:
            self.show_warning("Ошибка", f"Ошибка ML фильтрации: {str(e)}")
            
    def on_detect_outliers(self):
        """Обнаружение выбросов"""
        if self.well_data is None:
            return

        try:
            outliers = detect_outliers(self.well_data.pressure, 'iqr', threshold=1.5)
            outlier_count = outliers.sum()
            
            self.show_info("Обнаружение выбросов", f"Найдено {outlier_count} выбросов")
            
            # Обновляем график
            self.on_plot_dimensionless_selected()
        except Exception as e:
            self.show_warning("Ошибка", f"Ошибка обнаружения выбросов: {str(e)}")
    
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
                self.show_info("Экспорт", "Данные успешно экспортированы")
            except Exception as e:
                self.show_warning("Ошибка экспорта", f"Не удалось экспортировать данные: {str(e)}")
    
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
        self.show_info("Анализ режима течения", result_text)

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

        self.show_info("Индекс продуктивности", result_text)

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

        self.show_info("Переходы режимов", result_text)

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

        self.show_info("Сопоставление кривых", result_text)

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

                self.show_info("Экспорт отчета", "Отчет успешно экспортирован")
            except Exception as e:
                self.show_warning("Ошибка экспорта", f"Не удалось экспортировать отчет: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())
