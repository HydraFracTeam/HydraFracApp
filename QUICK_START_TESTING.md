# 🚀 Быстрый старт: Тесты и визуализация

## Шаг 1: Запуск тестов

```bash
python run_tests_with_logging.py
```

Выберите:
- `1` или Enter - быстрые тесты (рекомендуется для начала)
- `all` - все тесты (займёт больше времени)

## Шаг 2: Генерация визуализаций

```bash
python generate_visualizations.py
```

Если логов нет, скрипт предложит создать демонстрационные данные.

## Шаг 3: Просмотр результатов

Откройте папку `test_results/` и просмотрите созданные PNG файлы:
- `error_vs_volume_*.png` - ошибка vs объём данных
- `error_vs_quality_*.png` - ошибка vs качество данных  
- `error_heatmap_*.png` - тепловые карты

## Альтернативный способ (через pytest)

```bash
# 1. Запуск тестов
pytest tests/test_load_with_error_logging.py -v -m load

# 2. Генерация визуализаций
python generate_visualizations.py
```

## Проверка состояния

```bash
python check_tests_status.py
```

## Работа с обратными данными

Для сравнения с обратными трендами (рост ошибки от объёма):

```bash
# 1. Генерация обратных данных
python generate_reverse_error_data.py

# 2. Просмотр сохранённых данных
python view_saved_data.py --all

# 3. Генерация визуализаций для обратных данных
python generate_visualizations.py --source reverse

# Или для обоих наборов данных
python generate_visualizations.py --source both
```

---
📖 Подробная документация: `README_TESTING.md`

