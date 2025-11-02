# Руководство по комплексному тестированию

## Обзор

Этот документ описывает комплексную систему тестирования приложения, покрывающую все ключевые метрики качества.

## Метрики качества и критерии

### 1. ✅ Время отклика GUI (< 500ms)

**Критерий:** Все кнопки GUI (кроме загрузки файлов) должны отвечать менее чем за 500ms

**Покрытие:**
- ✅ Построить график
- ✅ Интерполяция (до 5000ms для ML методов)
- ✅ ML фильтрация
- ✅ Обнаружить выбросы
- ✅ Экспорт данных
- ✅ Анализ режима течения
- ✅ Индекс продуктивности
- ✅ Переходы режимов
- ✅ Билинейное/линейное/псевдорадиальное течение
- ✅ Сопоставить с данными

**Файл тестов:** `tests/test_comprehensive_performance.py::TestGUIResponseTime`

**Запуск:**
```bash
pytest tests/test_comprehensive_performance.py::TestGUIResponseTime -v -m performance
```

### 2. ✅ Failure Rate (< 1%)

**Критерий:** Частота отказов при многократном выполнении операций должна быть менее 1%

**Покрытие:**
- ✅ 1000 итераций построения графиков
- ✅ 100 итераций интерполяции
- ✅ Комбинированные тесты всех операций

**Файл тестов:** `tests/test_comprehensive_performance.py::TestFailureRate`

**Запуск:**
```bash
pytest tests/test_comprehensive_performance.py::TestFailureRate -v -m load
```

### 3. ✅ Потребление памяти (линейный рост)

**Критерий:** Рост памяти должен быть линейным (R² > 0.8), не квадратичным

**Покрытие:**
- ✅ Анализ тренда роста памяти (10, 20, 50, 100, 200 итераций)
- ✅ Проверка на утечки памяти (< 100MB на 100 операций)
- ✅ Линейная регрессия vs квадратичная

**Файл тестов:** `tests/test_comprehensive_performance.py::TestMemoryConsumption`

**Запуск:**
```bash
pytest tests/test_comprehensive_performance.py::TestMemoryConsumption -v -m memory
```

### 4. ✅ Время загрузки данных (< 5 сек/100K строк)

**Критерий:** Загрузка 100,000 строк данных должна занимать менее 5 секунд

**Покрытие:**
- ✅ Прямой тест загрузки 100K строк
- ✅ Множественные файлы по 50K строк
- ✅ Проверка линейной масштабируемости

**Файл тестов:** `tests/test_comprehensive_performance.py::TestDataLoadingPerformance`

**Запуск:**
```bash
pytest tests/test_comprehensive_performance.py::TestDataLoadingPerformance -v -m performance
```

### 5. ✅ Точность ML-функций (> 95%)

**Критерий:** ML-методы должны обеспечивать точность > 95%

**Покрытие:**
- ✅ Интерполяция (Random Forest)
- ✅ Фильтрация (Savitzky-Golay)
- ✅ Обнаружение выбросов (IQR)
- ✅ Метрики: accuracy, precision, recall, F1-score

**Файл тестов:** `tests/test_comprehensive_performance.py::TestMLAccuracy`

**Запуск:**
```bash
pytest tests/test_comprehensive_performance.py::TestMLAccuracy -v -m unit
```

### 6. ✅ Стабильность долгой работы (деградация < 15%)

**Критерий:** Деградация производительности за длительный период < 15%

**Покрытие:**
- ✅ 1000 операций с измерением деградации
- ✅ Стабильность использования памяти
- ✅ Проверка линейности роста ресурсов

**Файл тестов:** `tests/test_comprehensive_performance.py::TestLongTermStability`

**Запуск:**
```bash
pytest tests/test_comprehensive_performance.py::TestLongTermStability -v -m longrun
```

⚠️ **Внимание:** Long-running тесты могут занимать 10-20 минут!

## Быстрый старт

### Установка зависимостей

```bash
pip install -r requirements.txt
pip install pytest-cov memory-profiler
```

### Запуск всех тестов (автоматический)

```bash
python run_comprehensive_tests.py
```

Этот скрипт:
1. Запускает все группы тестов последовательно
2. Спрашивает, запускать ли long-running тесты
3. Генерирует подробный отчет
4. Сохраняет результаты в `test_report.txt`

### Запуск отдельных групп тестов

#### Быстрые тесты (unit + performance)
```bash
pytest tests/test_comprehensive_performance.py -v -m "performance and not longrun"
```

#### Тесты памяти
```bash
pytest tests/test_comprehensive_performance.py -v -m memory
```

#### Нагрузочные тесты
```bash
pytest tests/test_comprehensive_performance.py -v -m load
```

#### Долгие тесты стабильности
```bash
pytest tests/test_comprehensive_performance.py -v -m longrun
```

#### Все тесты точности ML
```bash
pytest tests/test_comprehensive_performance.py -v -m unit
```

### Запуск с покрытием кода

```bash
pytest tests/test_comprehensive_performance.py --cov=. --cov-report=html
```

Отчет будет сохранен в `htmlcov/index.html`

## Структура тестов

```
tests/test_comprehensive_performance.py
├── TestGUIResponseTime          # Время отклика кнопок < 500ms
│   ├── test_plot_button_response_time
│   ├── test_interpolation_button_response_time
│   ├── test_ml_filter_button_response_time
│   ├── test_outlier_detection_button_response_time
│   ├── test_export_button_response_time
│   ├── test_flow_regime_analysis_button_response_time
│   ├── test_productivity_button_response_time
│   ├── test_transitions_button_response_time
│   ├── test_type_curve_buttons_response_time
│   └── test_match_curves_button_response_time
│
├── TestFailureRate              # Failure rate < 1%
│   ├── test_plot_button_failure_rate (1000 итераций)
│   ├── test_interpolation_failure_rate (100 итераций)
│   └── test_all_buttons_combined_failure_rate (200 итераций)
│
├── TestMemoryConsumption        # Линейный рост памяти
│   ├── test_memory_growth_is_linear
│   └── test_memory_leak_detection
│
├── TestDataLoadingPerformance   # Загрузка данных < 5 сек/100K
│   ├── test_large_dataset_loading_time
│   └── test_multiple_large_datasets_loading
│
├── TestMLAccuracy               # Точность ML > 95%
│   ├── test_interpolation_accuracy_above_95_percent
│   ├── test_filtering_accuracy_above_95_percent
│   └── test_outlier_detection_accuracy_above_95_percent
│
└── TestLongTermStability        # Деградация < 15%
    ├── test_long_running_performance_degradation (1000+ операций)
    └── test_memory_stability_long_run
```

## Интерпретация результатов

### Успешный прогон

```
📊 Построить график: среднее=245.32ms, макс=487.21ms
✅ PASSED

📊 Failure rate (построение графика): 0.00% (0/1000)
✅ PASSED

📊 Анализ роста памяти:
   Линейная модель: R²=0.9543
   Квадратичная модель: R²=0.9587
   Коэффициент роста: 0.0234 МБ/итерация
✅ PASSED

📊 Загрузка 100K строк: 3.45 сек
✅ PASSED

📊 Точность интерполяции: 97.34%
✅ PASSED

📊 Деградация производительности: 8.23%
✅ PASSED
```

### Проблемные результаты

```
❌ FAILED: test_plot_button_response_time
AssertionError: Среднее время отклика 687.45ms превышает 500ms

❌ FAILED: test_interpolation_failure_rate
AssertionError: Failure rate 2.34% превышает 1%

❌ FAILED: test_memory_growth_is_linear
AssertionError: Рост памяти сильно нелинейный (улучшение=0.15)
```

## Непрерывная интеграция (CI/CD)

### GitHub Actions пример

```yaml
name: Comprehensive Tests

on: [push, pull_request]

jobs:
  fast-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest-cov
      - name: Run fast tests
        run: |
          pytest tests/test_comprehensive_performance.py -v -m "not longrun and not slow"
  
  nightly-stability:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest-cov
      - name: Run long-running tests
        run: |
          pytest tests/test_comprehensive_performance.py -v -m longrun
```

## Troubleshooting

### Тесты GUI не запускаются

**Проблема:** `QApplication` не инициализируется

**Решение:**
```bash
export QT_QPA_PLATFORM=offscreen  # Linux/Mac
set QT_QPA_PLATFORM=offscreen     # Windows CMD
$env:QT_QPA_PLATFORM="offscreen"  # Windows PowerShell
```

### Тесты памяти показывают нелинейный рост

**Возможные причины:**
1. Утечка памяти в коде
2. Кэширование данных
3. Незакрытые ресурсы

**Отладка:**
```bash
python -m memory_profiler your_script.py
```

### Долгие тесты зависают

**Решение:**
- Запускайте с флагом `-s` для вывода прогресса
- Используйте меньше итераций для отладки
- Проверьте логи приложения

## Дополнительные инструменты

### Профилирование производительности

```bash
python -m cProfile -o profile.stats main.py
python -m pstats profile.stats
```

### Визуализация использования памяти

```bash
mprof run python your_script.py
mprof plot
```

### Анализ покрытия кода

```bash
pytest --cov=. --cov-report=term-missing --cov-report=html
```

## Поддержка и вопросы

При возникновении проблем:
1. Проверьте логи в `test_report.txt`
2. Запустите тесты с флагом `-vv` для детального вывода
3. Используйте `--lf` для запуска только проваленных тестов

## Лицензия и авторство

Разработано в рамках проекта анализа гидравлического разрыва пласта.

