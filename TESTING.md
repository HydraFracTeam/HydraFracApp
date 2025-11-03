# Руководство по тестированию

## Быстрый старт

### Установка зависимостей
```bash
pip install -r requirements.txt
```

### Запуск всех быстрых тестов (< 5 минут)
```bash
pytest tests/test_comprehensive_performance.py -v -m "not longrun"
```

### Автоматический запуск с отчетом
```bash
python run_comprehensive_tests.py
```

## Основные группы тестов

### 1. Время отклика GUI < 500ms
```bash
pytest tests/test_comprehensive_performance.py::TestGUIResponseTime -v
```
Покрывает 12 кнопок (кроме загрузки файлов).

### 2. Failure Rate < 1%
```bash
pytest tests/test_comprehensive_performance.py::TestFailureRate -v -m load
```
Проверяет стабильность при многократных операциях (1000+ итераций).

### 3. Потребление памяти (линейный рост)
```bash
pytest tests/test_comprehensive_performance.py::TestMemoryConsumption -v -m memory
```
Проверяет линейность роста памяти (R² > 0.8).

### 4. Загрузка данных < 5 сек/100K строк
```bash
pytest tests/test_comprehensive_performance.py::TestDataLoadingPerformance -v
```

### 5. Точность ML > 95%
```bash
pytest tests/test_comprehensive_performance.py::TestMLAccuracy -v -m unit
```
Тестирует интерполяцию, фильтрацию и обнаружение выбросов.

### 6. Стабильность (деградация < 15%)
```bash
pytest tests/test_comprehensive_performance.py::TestLongTermStability -v -m longrun -s
```
⚠️ **Внимание:** Занимает 10-20 минут!

## Маркеры pytest

| Маркер | Описание | Пример |
|--------|----------|-------|
| `performance` | Тесты производительности | `-m performance` |
| `memory` | Тесты памяти | `-m memory` |
| `load` | Нагрузочные тесты | `-m load` |
| `unit` | Юнит-тесты (ML) | `-m unit` |
| `longrun` | Долгие тесты (> 5 мин) | `-m longrun` |
| `not slow` | Исключить медленные | `-m "not slow"` |

## Настройка окружения

### Windows PowerShell
```powershell
$env:QT_QPA_PLATFORM="offscreen"
pytest tests/test_comprehensive_performance.py -v
```

### Windows CMD
```cmd
set QT_QPA_PLATFORM=offscreen
pytest tests/test_comprehensive_performance.py -v
```

### Linux / Mac
```bash
export QT_QPA_PLATFORM=offscreen
pytest tests/test_comprehensive_performance.py -v
```

## Структура тестов

### Основные файлы
- `tests/test_comprehensive_performance.py` - Основные тесты производительности (23 теста)
- `tests/test_dimensionless_interpolation_comprehensive.py` - Тесты интерполяции безразмерных кривых
- `tests/test_gui_load.py` - Нагрузочные тесты GUI
- `tests/test_ml_methods.py` - Тесты ML-методов
- `tests/test_gui_with_dialogs.py` - Тесты с реальными диалогами

### Два подхода к тестированию GUI

#### 1. Быстрый подход (test_mode)
- Файл: `tests/test_comprehensive_performance.py`
- Диалоги не показываются (`test_mode=True`)
- Время выполнения: 5-8 минут
- Критерий: < 500ms

#### 2. Реалистичный подход (с диалогами)
- Файл: `tests/test_gui_with_dialogs.py`
- Диалоги показываются и автоматически закрываются
- Время выполнения: 10-15 минут
- Критерий: < 1000ms

## Критерии качества

| Метрика | Критерий | Файл теста |
|---------|----------|------------|
| Время отклика GUI | < 500ms | `TestGUIResponseTime` |
| Failure rate | < 1% | `TestFailureRate` |
| Рост памяти | Линейный (R² > 0.8) | `TestMemoryConsumption` |
| Загрузка данных | < 5 сек/100K | `TestDataLoadingPerformance` |
| Точность ML | > 95% | `TestMLAccuracy` |
| Деградация | < 15% | `TestLongTermStability` |

## Тестирование ML-функций

### Обзор
Тесты проверяют физическую адекватность результатов ML-функций для анализа данных ГРП.

### Запуск
```bash
pytest tests/test_ml_methods.py -v
```

### Создание тестовых данных
```bash
python create_test_data.py
```

### Проверяемые аспекты

#### Интерполяция
- Сохранение диапазона значений
- Корреляция с базовым сигналом
- Заполнение пропусков
- Сохранение тренда

#### Фильтрация
- Улучшение корреляции
- Сохранение амплитуды
- Отсутствие артефактов
- Физические ограничения

#### Обнаружение выбросов
- Чувствительность
- Специфичность
- Разумная доля выбросов (< 20%)

## Тестирование интерполяции безразмерных кривых

### Запуск
```bash
pytest tests/test_dimensionless_interpolation_comprehensive.py -v
```

### Покрытие
- Тесты на объёмных синтетических данных
- Тесты на реальных данных
- Тесты взаимодействия между модулями
- Тесты идемпотентности

### Нагрузочные тесты GUI
- 1000 кликов по кнопке "Построить график"
- 100 кликов по интерполяции
- Проверка использования памяти

## Отладка

### Детальный вывод
```bash
pytest tests/test_comprehensive_performance.py -vv -s
```

### Только проваленные тесты
```bash
pytest --lf tests/test_comprehensive_performance.py
```

### С покрытием кода
```bash
pytest tests/test_comprehensive_performance.py --cov=. --cov-report=html
```

### Проблемы и решения

**GUI тесты не запускаются:**
```bash
export QT_QPA_PLATFORM=offscreen  # Linux/Mac
$env:QT_QPA_PLATFORM="offscreen"  # Windows PowerShell
```

**Тесты зависают:**
- Запустите с флагом `-s` для вывода прогресса
- Проверьте, что нет блокирующих диалогов

**Память растет нелинейно:**
- Проверьте логи утечек памяти
- Уменьшите количество итераций в тестах

## CI/CD интеграция

### GitHub Actions пример
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: |
          export QT_QPA_PLATFORM=offscreen
          pytest tests/test_comprehensive_performance.py -v -m "not longrun"
```

## Стек технологий

- **pytest 8.3.3** - фреймворк тестирования
- **PySide6 / QTest** - тестирование GUI
- **unittest.mock** - мокирование
- **tracemalloc** - профилирование памяти
- **numpy, pandas** - обработка данных
- **scikit-learn** - ML алгоритмы

## Дополнительные ресурсы

- `DIMENSIONLESS_METHODS.md` - Документация по безразмерным методам
- `INTERPOLATION_METHODS.md` - Документация по методам интерполяции
- `REQUIREMENTS_CHECK.md` - Проверка выполнения требований

