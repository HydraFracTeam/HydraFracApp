# Таблица тестов

Полное описание существующих тестов проекта с указанием их назначения, сложности и команд запуска.

| Тест | Файл | Запуск | Что тестирует | Тяжесть |
|------|------|---------|---------------|---------|
| `test_get_well_params_defaults` | `test_main_functions.py` | `pytest tests/test_main_functions.py::TestMainFunctions::test_get_well_params_defaults` | Создание параметров скважины с значениями по умолчанию | Легкий |
| `test_get_well_params_custom` | `test_main_functions.py` | `pytest tests/test_main_functions.py::TestMainFunctions::test_get_well_params_custom` | Создание параметров скважины с кастомными значениями | Легкий |
| `test_get_quality_label` | `test_main_functions.py` | `pytest tests/test_main_functions.py::TestMainFunctions::test_get_quality_label` | Определение качества интерполяции по RMSE | Легкий |
| `test_create_no_interpolation_report` | `test_main_functions.py` | `pytest tests/test_main_functions.py::TestMainFunctions::test_create_no_interpolation_report` | Создание отчета о том, что интерполяция не требуется | Легкий |
| `test_show_info_test_mode` | `test_main_functions.py` | `pytest tests/test_main_functions.py::TestMainFunctions::test_show_info_test_mode` | Отключение сообщений в test_mode | Легкий |
| `test_show_warning_test_mode` | `test_main_functions.py` | `pytest tests/test_main_functions.py::TestMainFunctions::test_show_warning_test_mode` | Отключение предупреждений в test_mode | Легкий |
| `test_show_error_test_mode` | `test_main_functions.py` | `pytest tests/test_main_functions.py::TestMainFunctions::test_show_error_test_mode` | Отключение ошибок в test_mode | Легкий |
| `test_application_startup` | `test_main_functions.py` | `pytest tests/test_main_functions.py::TestMainIntegration::test_application_startup` | Запуск приложения и проверка инициализации | Легкий |
| `test_constants_defined` | `test_main_functions.py` | `pytest tests/test_main_functions.py::TestMainIntegration::test_constants_defined` | Проверка определения всех констант из config.py | Легкий |
| `test_1000_clicks_plot_button_stability` | `test_gui_load.py` | `pytest tests/test_gui_load.py::TestGUILoadPlotButton::test_1000_clicks_plot_button_stability` | Стабильность при 1000 кликах по кнопке построения графика | Тяжелый |
| `test_rapid_plot_clicks_no_hang` | `test_gui_load.py` | `pytest tests/test_gui_load.py::TestGUILoadPlotButton::test_rapid_plot_clicks_no_hang` | Отсутствие зависания при быстрых кликах | Средний |
| `test_plot_button_memory_usage` | `test_gui_load.py` | `pytest tests/test_gui_load.py::TestGUILoadPlotButton::test_plot_button_memory_usage` | Использование памяти при многократных кликах | Средний |
| `test_100_clicks_interpolation_no_hang` | `test_gui_load.py` | `pytest tests/test_gui_load.py::TestGUILoadInterpolation::test_100_clicks_interpolation_no_hang` | Стабильность при 100 кликах по интерполяции | Тяжелый |
| `test_interpolation_idempotency` | `test_gui_load.py` | `pytest tests/test_gui_load.py::TestGUILoadInterpolation::test_interpolation_idempotency` | Идемпотентность интерполяции | Средний |
| `test_interpolation_on_already_interpolated_data` | `test_gui_load.py` | `pytest tests/test_gui_load.py::TestGUILoadInterpolation::test_interpolation_on_already_interpolated_data` | Интерполяция уже интерполированных данных | Средний |
| `test_plot_creation_performance` | `test_gui_load.py` | `pytest tests/test_gui_load.py::TestGUIPerformance::test_plot_creation_performance` | Производительность создания графика | Средний |
| `test_interpolation_performance` | `test_gui_load.py` | `pytest tests/test_gui_load.py::TestGUIPerformance::test_interpolation_performance` | Производительность интерполяции | Средний |
| `test_application_initialization` | `test_gui_integration.py` | `pytest tests/test_gui_integration.py::TestGUIIntegration::test_application_initialization` | Инициализация приложения | Легкий |
| `test_plot_type_combo_population` | `test_gui_integration.py` | `pytest tests/test_gui_integration.py::TestGUIIntegration::test_plot_type_combo_population` | Заполнение combo box типами графиков | Легкий |
| `test_well_data_loading` | `test_gui_integration.py` | `pytest tests/test_gui_integration.py::TestGUIIntegration::test_well_data_loading` | Загрузка данных скважины | Легкий |
| `test_file_loading_dialog` | `test_gui_integration.py` | `pytest tests/test_gui_integration.py::TestGUIIntegration::test_file_loading_dialog` | Диалог загрузки файла | Легкий |
| `test_plot_widget_initialization` | `test_gui_integration.py` | `pytest tests/test_gui_integration.py::TestGUIIntegration::test_plot_widget_initialization` | Инициализация виджета графика | Легкий |
| `test_button_connections` | `test_gui_integration.py` | `pytest tests/test_gui_integration.py::TestGUIIntegration::test_button_connections` | Подключение кнопок к обработчикам | Легкий |
| `test_well_selection_combo` | `test_gui_integration.py` | `pytest tests/test_gui_integration.py::TestGUIIntegration::test_well_selection_combo` | Combo box выбора скважины | Легкий |
| `test_plot_creation_with_data` | `test_gui_integration.py` | `pytest tests/test_gui_integration.py::TestGUIFunctional::test_plot_creation_with_data` | Создание графика с данными | Средний |
| `test_dimensionless_parameters_plot` | `test_gui_integration.py` | `pytest tests/test_gui_integration.py::TestGUIFunctional::test_dimensionless_parameters_plot` | Построение графика безразмерных параметров | Средний |
| `test_logarithmic_plot_with_inversion` | `test_gui_integration.py` | `pytest tests/test_gui_integration.py::TestGUIFunctional::test_logarithmic_plot_with_inversion` | Логарифмический график с инверсией | Средний |
| `test_plot_without_data` | `test_gui_integration.py` | `pytest tests/test_gui_integration.py::TestGUIErrorHandling::test_plot_without_data` | Построение графика без данных | Легкий |
| `test_plot_with_invalid_data` | `test_gui_integration.py` | `pytest tests/test_gui_integration.py::TestGUIErrorHandling::test_plot_with_invalid_data` | Построение графика с некорректными данными | Легкий |
| `test_plot_button_response_time` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestGUIResponseTime::test_plot_button_response_time` | Время отклика кнопки 'Построить график' < 500ms | Средний |
| `test_interpolation_button_response_time` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestGUIResponseTime::test_interpolation_button_response_time` | Время отклика кнопки 'Интерполяция' < 500ms | Средний |
| `test_ml_filter_button_response_time` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestGUIResponseTime::test_ml_filter_button_response_time` | Время отклика кнопки 'ML фильтрация' < 500ms | Средний |
| `test_outlier_detection_button_response_time` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestGUIResponseTime::test_outlier_detection_button_response_time` | Время отклика кнопки 'Обнаружить выбросы' < 500ms | Средний |
| `test_export_button_response_time` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestGUIResponseTime::test_export_button_response_time` | Время отклика кнопки 'Экспорт данных' < 500ms | Средний |
| `test_flow_regime_analysis_button_response_time` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestGUIResponseTime::test_flow_regime_analysis_button_response_time` | Время отклика кнопки 'Анализ режима течения' < 500ms | Средний |
| `test_productivity_button_response_time` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestGUIResponseTime::test_productivity_button_response_time` | Время отклика кнопки 'Индекс продуктивности' < 500ms | Средний |
| `test_transitions_button_response_time` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestGUIResponseTime::test_transitions_button_response_time` | Время отклика кнопки 'Переходы режимов' < 500ms | Средний |
| `test_type_curve_buttons_response_time` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestGUIResponseTime::test_type_curve_buttons_response_time` | Время отклика кнопок эталонных кривых < 500ms | Средний |
| `test_match_curves_button_response_time` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestGUIResponseTime::test_match_curves_button_response_time` | Время отклика кнопки 'Сопоставить с данными' < 500ms | Средний |
| `test_plot_button_failure_rate` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestFailureRate::test_plot_button_failure_rate` | Failure rate при построении графика < 1% (1000 попыток) | Тяжелый |
| `test_interpolation_failure_rate` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestFailureRate::test_interpolation_failure_rate` | Failure rate при интерполяции < 1% (100 попыток) | Тяжелый |
| `test_all_buttons_combined_failure_rate` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestFailureRate::test_all_buttons_combined_failure_rate` | Общий failure rate для всех операций < 1% | Тяжелый |
| `test_memory_growth_is_linear` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestMemoryConsumption::test_memory_growth_is_linear` | Линейный рост памяти при многократных операциях (R² > 0.8) | Тяжелый |
| `test_memory_leak_detection` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestMemoryConsumption::test_memory_leak_detection` | Отсутствие утечек памяти при повторных операциях | Тяжелый |
| `test_large_dataset_loading_time` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestDataLoadingPerformance::test_large_dataset_loading_time` | Время загрузки 100K строк < 5 секунд | Тяжелый |
| `test_multiple_large_datasets_loading` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestDataLoadingPerformance::test_multiple_large_datasets_loading` | Загрузка нескольких больших файлов | Тяжелый |
| `test_interpolation_accuracy_above_95_percent` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestMLAccuracy::test_interpolation_accuracy_above_95_percent` | Точность интерполяции > 95% | Средний |
| `test_filtering_accuracy_above_95_percent` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestMLAccuracy::test_filtering_accuracy_above_95_percent` | Точность фильтрации > 95% | Средний |
| `test_outlier_detection_accuracy_above_95_percent` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestMLAccuracy::test_outlier_detection_accuracy_above_95_percent` | Точность обнаружения выбросов > 95% | Средний |
| `test_long_running_performance_degradation` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestLongTermStability::test_long_running_performance_degradation -m longrun` | Деградация производительности при длительной работе < 15% | Очень тяжелый |
| `test_memory_stability_long_run` | `test_comprehensive_performance.py` | `pytest tests/test_comprehensive_performance.py::TestLongTermStability::test_memory_stability_long_run -m longrun` | Стабильность использования памяти при длительной работе | Очень тяжелый |
| `test_plot_button_with_dialog_auto_close` | `test_gui_with_dialogs.py` | `pytest tests/test_gui_with_dialogs.py::TestGUIWithRealDialogs::test_plot_button_with_dialog_auto_close` | Кнопка 'Построить график' с автозакрытием диалогов | Средний |
| `test_interpolation_with_dialog_auto_close` | `test_gui_with_dialogs.py` | `pytest tests/test_gui_with_dialogs.py::TestGUIWithRealDialogs::test_interpolation_with_dialog_auto_close` | Интерполяция с автозакрытием диалогов | Средний |
| `test_flow_regime_with_dialog_auto_close` | `test_gui_with_dialogs.py` | `pytest tests/test_gui_with_dialogs.py::TestGUIWithRealDialogs::test_flow_regime_with_dialog_auto_close` | Анализ режима течения с автозакрытием диалогов | Средний |
| `test_dialog_closing_mechanism` | `test_gui_with_dialogs.py` | `pytest tests/test_gui_with_dialogs.py::TestDialogClosingMechanism::test_dialog_closing_mechanism` | Механизм автоматического закрытия диалогов | Легкий |
| `test_load_with_dialogs` | `test_gui_with_dialogs.py` | `pytest tests/test_gui_with_dialogs.py::TestLoadWithDialogs::test_load_with_dialogs` | Нагрузочные тесты с реальными диалогами | Тяжелый |
| `test_well_data_schemas` | `test_well_analysis.py` | `pytest tests/test_well_analysis.py::TestWellDataSchemas::test_well_data_schemas` | Тесты для схем данных (Pydantic) | Легкий |
| `test_parse_well_data` | `test_well_analysis.py` | `pytest tests/test_well_analysis.py::TestParseWellData::test_parse_well_data` | Парсинг данных скважины из CSV/Parquet | Средний |
| `test_grp_analysis` | `test_well_analysis.py` | `pytest tests/test_well_analysis.py::TestGRPAnalysis::test_grp_analysis` | Анализ режимов течения и индекса продуктивности | Средний |
| `test_ml_methods` | `test_well_analysis.py` | `pytest tests/test_well_analysis.py::TestMLMethods::test_ml_methods` | ML-методы интерполяции и фильтрации | Средний |
| `test_full_analysis_pipeline` | `test_well_analysis.py` | `pytest tests/test_well_analysis.py::TestIntegration::test_full_analysis_pipeline` | Полный пайплайн анализа от загрузки до экспорта | Средний |
| `test_physical_adequacy` | `test_physical_adequacy.py` | `pytest tests/test_physical_adequacy.py::TestPhysicalAdequacy::test_physical_adequacy` | Физическая адекватность результатов анализа ГРП | Средний |
| `test_synthetic_large_dataset` | `test_dimensionless_interpolation_comprehensive.py` | `pytest tests/test_dimensionless_interpolation_comprehensive.py::TestSyntheticLargeDataset::test_synthetic_large_dataset` | Тесты на объёмных синтетических данных | Тяжелый |
| `test_real_data_files` | `test_dimensionless_interpolation_comprehensive.py` | `pytest tests/test_dimensionless_interpolation_comprehensive.py::TestRealDataFiles::test_real_data_files` | Тесты на реальных файлах test.csv и test_bad.csv | Средний |
| `test_module_integration` | `test_dimensionless_interpolation_comprehensive.py` | `pytest tests/test_dimensionless_interpolation_comprehensive.py::TestModuleIntegration::test_module_integration` | Взаимодействие между модулями на точность | Средний |
| `test_idempotency` | `test_dimensionless_interpolation_comprehensive.py` | `pytest tests/test_dimensionless_interpolation_comprehensive.py::TestIdempotency::test_idempotency` | Идемпотентность интерполяции безразмерных кривых | Средний |
| `test_ml_interpolation` | `test_ml_methods.py` | `pytest tests/test_ml_methods.py::TestMLInterpolation::test_ml_interpolation` | ML-интерполяция различными методами | Средний |
| `test_ml_filtering` | `test_ml_methods.py` | `pytest tests/test_ml_methods.py::TestMLFiltering::test_ml_filtering` | ML-фильтрация данных | Средний |
| `test_outlier_detection` | `test_ml_methods.py` | `pytest tests/test_ml_methods.py::TestOutlierDetection::test_outlier_detection` | Обнаружение выбросов ML-методами | Средний |
| `test_complex_data_cleaning` | `test_ml_methods.py` | `pytest tests/test_ml_methods.py::TestComplexDataCleaning::test_complex_data_cleaning` | Комплексная очистка данных | Средний |
| `test_compute_transmissivity` | `test_helpers_and_physics.py` | `pytest tests/test_helpers_and_physics.py::test_compute_transmissivity_scalar_vector` | Вычисление трансмиссивности | Легкий |
| `test_compute_pore_volume` | `test_helpers_and_physics.py` | `pytest tests/test_helpers_and_physics.py::test_compute_pore_volume_basic` | Вычисление порового объема | Легкий |
| `test_compute_darcy_flux` | `test_helpers_and_physics.py` | `pytest tests/test_helpers_and_physics.py::test_compute_darcy_flux_sign_and_scale` | Вычисление потока по Дарси | Легкий |
| `test_compute_diffusivity` | `test_helpers_and_physics.py` | `pytest tests/test_helpers_and_physics.py::test_compute_diffusivity_monotonic` | Вычисление диффузивности | Легкий |
| `test_derivative` | `test_helpers_and_physics.py` | `pytest tests/test_helpers_and_physics.py::test_derivative_linear_should_be_constant` | Вычисление производных | Легкий |
| `test_interpolate_series` | `test_helpers_and_physics.py` | `pytest tests/test_helpers_and_physics.py::test_interpolate_linear_gaps` | Интерполяция временных рядов | Легкий |
| `test_smooth_series` | `test_helpers_and_physics.py` | `pytest tests/test_helpers_and_physics.py::test_smooth_series_window_1_no_change` | Сглаживание временных рядов | Легкий |
| `test_parse_csv_params` | `test_helpers_and_physics.py` | `pytest tests/test_helpers_and_physics.py::test_parse_csv_params_ok` | Парсинг параметров из CSV | Легкий |

## Легенда тяжести тестов

- **Легкий**: Быстрый запуск (< 1 секунды), простая функциональность
- **Средний**: Умеренное время выполнения (1-10 секунд), более сложная логика
- **Тяжелый**: Долгое выполнение (10 секунд - 5 минут), нагрузочные тесты, большие объемы данных
- **Очень тяжелый**: Очень долгое выполнение (> 5 минут), длительные тесты стабильности (маркер `longrun`)

## Группы тестов

### Быстрые тесты (< 5 минут)
```bash
pytest tests/ -v -m "not longrun"
```

### Все тесты включая длительные
```bash
pytest tests/ -v
```

### Только тесты производительности
```bash
pytest tests/test_comprehensive_performance.py -v
```

### Только юнит-тесты
```bash
pytest tests/test_main_functions.py tests/test_helpers_and_physics.py -v
```

### Только интеграционные тесты
```bash
pytest tests/test_gui_integration.py tests/test_well_analysis.py -v
```

