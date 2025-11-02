# Быстрый старт тестирования - Шпаргалка

## 🚀 Установка

```bash
pip install -r requirements.txt
```

## ⚡ Быстрые команды

### Запуск всех тестов (автоматический)
```bash
python run_comprehensive_tests.py
```

### Только быстрые тесты (< 5 минут)
```bash
pytest tests/test_comprehensive_performance.py -v -m "not longrun and not slow"
```

## 📊 Тесты по требованиям

### 1️⃣ Время отклика GUI < 500ms
```bash
pytest tests/test_comprehensive_performance.py::TestGUIResponseTime -v
```

### 2️⃣ Failure Rate < 1%
```bash
pytest tests/test_comprehensive_performance.py::TestFailureRate -v -m load
```

### 3️⃣ Потребление памяти (линейный рост)
```bash
pytest tests/test_comprehensive_performance.py::TestMemoryConsumption -v -m memory
```

### 4️⃣ Загрузка данных < 5 сек/100K строк
```bash
pytest tests/test_comprehensive_performance.py::TestDataLoadingPerformance -v
```

### 5️⃣ Точность ML > 95%
```bash
pytest tests/test_comprehensive_performance.py::TestMLAccuracy -v -m unit
```

### 6️⃣ Стабильность (деградация < 15%)
```bash
pytest tests/test_comprehensive_performance.py::TestLongTermStability -v -m longrun -s
```
⚠️ **Занимает 10-20 минут!**

## 🏷️ Маркеры

| Команда | Описание |
|---------|----------|
| `-m performance` | Тесты производительности |
| `-m memory` | Тесты памяти |
| `-m load` | Нагрузочные тесты |
| `-m unit` | Юнит-тесты (ML точность) |
| `-m longrun` | Долгие тесты (> 5 мин) |
| `-m "not slow"` | Исключить медленные |

## 📈 С покрытием кода

```bash
pytest tests/test_comprehensive_performance.py --cov=. --cov-report=html
```

Отчет: `htmlcov/index.html`

## 🐛 Отладка

### Только проваленные тесты
```bash
pytest --lf
```

### Детальный вывод
```bash
pytest -vv
```

### С выводом print
```bash
pytest -s
```

### Остановка на первой ошибке
```bash
pytest -x
```

## 🔧 Настройка окружения

### Linux/Mac
```bash
export QT_QPA_PLATFORM=offscreen
pytest tests/test_comprehensive_performance.py -v
```

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

## 📁 Структура тестов

```
tests/test_comprehensive_performance.py
├── TestGUIResponseTime         → Время отклика
├── TestFailureRate            → Частота отказов
├── TestMemoryConsumption      → Память
├── TestDataLoadingPerformance → Загрузка данных
├── TestMLAccuracy             → Точность ML
└── TestLongTermStability      → Долгая стабильность
```

## 📄 Документация

- `TESTING_STACK_REPORT.md` - Подробное описание стека
- `COMPREHENSIVE_TESTING_GUIDE.md` - Полное руководство
- `TEST_SUMMARY_AND_RESULTS.md` - Итоговый отчет
- `TESTING_QUICK_START.md` - Эта шпаргалка

## ✅ Целевые метрики

| Метрика | Критерий | Тест |
|---------|----------|------|
| Время отклика | < 500ms | ✅ |
| Failure rate | < 1% | ✅ |
| Рост памяти | Линейный | ✅ |
| Загрузка | < 5 сек/100K | ✅ |
| Точность ML | > 95% | ✅ |
| Деградация | < 15% | ✅ |

## 🆘 Помощь

### Проблема: GUI тесты не запускаются

**Решение:** Установите `QT_QPA_PLATFORM=offscreen`

### Проблема: Тесты зависают

**Решение:** Запустите с флагом `-s` для вывода прогресса

### Проблема: Памяти не хватает

**Решение:** Уменьшите количество итераций в долгих тестах

---

**Быстрая проверка всех метрик:**
```bash
python run_comprehensive_tests.py
```

Выберите `N` когда спросит про long-running тесты (они долгие!)

