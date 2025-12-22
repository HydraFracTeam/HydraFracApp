# Инструкция по запуску тестов и просмотру визуализаций

## Быстрый старт

### 1. Запуск тестов с логированием

```bash
# Запуск всех тестов с логированием
python run_tests_with_logging.py all

# Или запуск только быстрых тестов
python run_tests_with_logging.py 1

# Или через pytest напрямую
pytest tests/test_load_with_error_logging.py -v -m load
```

### 2. Генерация визуализаций

После запуска тестов сгенерируйте визуализации:

```bash
python generate_visualizations.py
```

Если логов ещё нет, скрипт предложит создать демонстрационные данные.

### 3. Просмотр результатов

Визуализации сохраняются в директории `test_results/`:
- `error_vs_volume_*.png` - зависимость ошибки от объёма данных
- `error_vs_quality_*.png` - зависимость ошибки от качества данных
- `error_heatmap_*.png` - тепловые карты ошибок по методам и подсистемам

## Детальная инструкция

### Структура тестов

1. **test_error_logging_and_visualization.py** - быстрые тесты системы логирования
2. **test_load_with_error_logging.py** - нагрузочные тесты с логированием
3. **test_gui_load.py** - базовые нагрузочные тесты GUI
4. **test_comprehensive_performance.py** - комплексные тесты производительности

### Запуск отдельных тестов

```bash
# Тесты логирования (быстрые)
pytest tests/test_error_logging_and_visualization.py -v

# Нагрузочные тесты GUI
pytest tests/test_gui_load.py -v -m slow

# Тесты с логированием ошибок
pytest tests/test_load_with_error_logging.py -v -m load

# Комплексные тесты производительности
pytest tests/test_comprehensive_performance.py -v -m performance
```

### Проверка состояния

Проверьте состояние тестов и системы логирования:

```bash
python check_tests_status.py
```

### Просмотр статистики ошибок

```python
from helpers.math_error_logger import get_logger

logger = get_logger()
stats = logger.get_error_statistics()
print(stats)

# Загрузить все ошибки в DataFrame
df = logger.load_errors()
print(df.head())
```

## Структура логов

Логи сохраняются в:
- `logs/math_errors.jsonl` - JSONL файл с записями об ошибках
- `logs/math_errors.log` - текстовый лог

Каждая запись содержит:
- `timestamp` - время ошибки
- `subsystem` - подсистема (interpolation, gui, filtering и т.д.)
- `method` - метод (linear, rbf, gp и т.д.)
- `error_type` - тип ошибки (rmse, mae, mape, exception и т.д.)
- `error_value` - значение ошибки
- `data_volume` - объём данных (количество точек)
- `data_quality` - качество данных (0-1)
- `metadata` - дополнительные метаданные

## Типы визуализаций

### 1. Зависимость ошибки от объёма данных

Показывает, как ошибка изменяется с ростом объёма данных:
- Общий график по всем подсистемам
- Разбивка по подсистемам
- Разбивка по методам
- Боксплоты по диапазонам объёма

### 2. Зависимость ошибки от качества данных

Показывает, как ошибка зависит от качества входных данных:
- Общий график
- Разбивка по подсистемам и методам
- Боксплоты по диапазонам качества

### 3. Тепловые карты

Матрицы ошибок: подсистема × метод
- Позволяют быстро найти проблемные комбинации
- Средние значения ошибок по каждой комбинации

## Примеры использования

### Полный цикл тестирования

```bash
# 1. Запуск тестов
python run_tests_with_logging.py all

# 2. Генерация визуализаций
python generate_visualizations.py

# 3. Проверка результатов
python check_tests_status.py
```

### Анализ конкретной подсистемы

```python
from helpers.math_error_logger import get_logger
from helpers.error_visualization import ErrorVisualizer

logger = get_logger()
df = logger.load_errors()

# Фильтруем по подсистеме
interpolation_errors = df[df['subsystem'] == 'interpolation']
print(interpolation_errors.describe())

# Генерируем визуализации только для интерполяции
visualizer = ErrorVisualizer()
visualizer.plot_error_vs_volume(df=interpolation_errors, error_type='rmse')
```

## Устранение проблем

### Нет логов после тестов

Убедитесь, что:
1. Тесты действительно выполнялись (проверьте вывод pytest)
2. Директория `logs/` существует и доступна для записи
3. Нет ошибок импорта модуля `math_error_logger`

### Визуализации не генерируются

1. Проверьте наличие данных: `python -c "from helpers.math_error_logger import get_logger; print(len(get_logger().load_errors()))"`
2. Убедитесь, что установлены все зависимости: `pip install matplotlib seaborn`
3. Проверьте права на запись в `test_results/`

### Тесты падают с ошибками импорта

Убедитесь, что все зависимости установлены:
```bash
pip install -r requirements.txt
```

## Дополнительные возможности

### Настройка логирования

В коде можно настроить директорию для логов:

```python
from helpers.math_error_logger import MathErrorLogger

logger = MathErrorLogger(log_dir="custom_logs", log_file="custom_errors.jsonl")
```

### Кастомные визуализации

```python
from helpers.error_visualization import ErrorVisualizer

visualizer = ErrorVisualizer(output_dir="my_results")
visualizer.plot_error_vs_volume(error_type="rmse", save_path="my_plot.png")
```

