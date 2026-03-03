Ниже — **единая, целостная архитектурная инструкция**, объединяющая весь предыдущий промпт.
Это базовый документ, от которого можно отталкиваться при генерации проекта и дальнейшей модификации.

Документ предназначен для передачи LLM (Qwen) или использования как внутренней архитектурной спецификации.

---

# АРХИТЕКТУРНАЯ ИНСТРУКЦИЯ

## MVP-прототип локального приложения интерпретации ГДИС (МГРП)

---

# 1. Назначение проекта

Разработать skeleton локального desktop-приложения на Python 3.11 для интерпретации КСД методом сопоставления с библиотекой эталонных безразмерных кривых (X–Y).

Это **MVP-прототип**.
Основная цель — проверить корректность архитектуры и работоспособность solver-а.

Физическая модель реализуется частично (через TODO).

---

# 2. Технологический стек

Обязательно использовать:

* Python 3.11
* pandas==2.3.3
* numpy==2.3.3
* scipy>=1.9.0
* PySide6==6.10.0
* PyQtGraph==0.13.7
* sqlite3

---

# 3. Архитектурная модель

Архитектура: **модульная (modular architecture)**.

Принципиальные правила:

1. Математика полностью отделена от GUI.
2. Solver не импортирует PySide6.
3. Solver работает только с numpy.
4. pandas используется только в processing.
5. SQLite используется только в data-модуле.
6. GUI не содержит формул.
7. Оптимизация выполняется в отдельном потоке (QThread).
8. Логирование выполняется через logging + отображается в UI-консоли.
9. Никаких глобальных переменных.
10. Никакого монолитного файла.

---

# 4. Структура проекта

```text
project/
│
├── core/                     # вычислительное ядро
│   ├── models.py
│   ├── dimensionless.py
│   ├── objective.py
│   ├── w_scaling.py
│   └── solver.py
│
├── processing/               # предобработка P(t)
│   └── preprocessing.py
│
├── data/                     # работа с SQLite
│   └── reference_repository.py
│
├── ui/
│   ├── main_window.py
│   ├── controller.py
│   ├── plot_manager.py
│   ├── threads.py
│   └── generated/            # файлы из Qt Designer
│
├── config.py
└── main.py
```

---

# 5. Точка входа

## main.py

Единственная точка запуска приложения.

Должен:

* создать QApplication
* создать MainWindow
* запустить event loop

Никакой бизнес-логики.

---

# 6. CORE — вычислительное ядро

Зависит только от numpy и scipy.

НЕ импортирует:

* PySide6
* pandas
* sqlite3

---

## 6.1 models.py

Создать dataclass:

```python
StaticParams
DynamicParams
SolverResult
```

---

## 6.2 dimensionless.py

Реализовать:

* compute_x(...)
* compute_y(...)
* normalize_flow_by_n(...)

Работают только с numpy.ndarray.

---

## 6.3 w_scaling.py

```python
scale_reference_by_w(Y_std, W_ref, W_user)
```

Масштабирует Y эталона.

---

## 6.4 objective.py

Реализовать:

* l1_error(x, y1, y2)
* l2_error(x, y1, y2)

---

## 6.5 solver.py

Skeleton solver-а должен включать:

* внешний перебор S
* интерполяцию эталона по S
* масштабирование по W
* внутреннюю оптимизацию k и L (scipy.optimize.minimize)
* возврат SolverResult

Без полной физики. Только структура + TODO.

---

# 7. PROCESSING

## preprocessing.py

Использует pandas.

Функции:

* interpolate_nan(df)
* smooth_pressure(df)
* to_numpy_arrays(df)

Возвращает numpy.

---

# 8. DATA — SQLite

Эталонные данные хранятся в двух таблицах:

---

## Таблица static

```sql
static (
    curve_id INTEGER PRIMARY KEY,
    Skin REAL,
    h REAL,
    N REAL,
    W REAL,
    L REAL,
    aL REAL,
    Q REAL
)
```

---

## Таблица dynamic

```sql
dynamic (
    id INTEGER PRIMARY KEY,
    curve_id INTEGER,
    elemIdx INTEGER,
    t REAL,
    dP REAL,
    X REAL,
    Y REAL
)
```

---

## reference_repository.py

Создать класс:

```python
class ReferenceRepository:
```

Методы:

```python
get_available_skins() -> list[float]

get_curves_by_skin(skin: float) -> list[int]

get_reference_curve(curve_id: int) -> tuple[np.ndarray, np.ndarray]

get_static_metadata(curve_id: int) -> dict
```

Требования:

* не использовать pandas
* возвращать numpy
* не содержать solver-логики

---

# 9. UI

GUI создается частично через Qt Designer.

## 9.1 Qt Designer

* создается базовая форма
* placeholder QWidget для графика
* placeholder для лог-консоли

Файл `.ui` конвертируется в `.py` и сохраняется в `ui/generated/`.

---

## 9.2 main_window.py

Наследуется от QMainWindow.

Должен:

* вызвать setupUi
* программно создать PyQtGraph PlotWidget
* добавить его в layout
* создать log_console (QPlainTextEdit)
* создать Controller

---

## 9.3 Встроенная лог-консоль

Внизу окна.

Тип:

* QTextEdit или QPlainTextEdit
* readOnly=True

Имя:

```
log_console
```

Метод:

```python
append_log(message: str)
```

Запрещено использовать print().

---

# 10. Логирование

Использовать стандартный модуль logging.

SolverThread должен отправлять сообщения через Qt-сигнал:

```python
progress_signal(str)
```

Controller должен передавать их в log_console.

Пример сообщений:

```
[INFO] Starting solver...
[INFO] Testing Skin=0.5
[INFO] Current error=0.0213
[INFO] Best result updated
[INFO] Solver finished in 2.34 sec
```

---

# 11. Потоки

## threads.py

Создать:

```python
class SolverThread(QThread):
```

Сигналы:

```python
progress_signal(str)
result_signal(SolverResult)
error_signal(str)
```

SolverThread:

* вызывает solver.run()
* отправляет лог-сообщения
* возвращает результат

---

# 12. Controller

controller.py:

Отвечает за:

* обработку кнопки "Рассчитать"
* запуск preprocessing
* запуск SolverThread
* обновление графиков
* логирование

---

# 13. PlotManager

plot_manager.py:

Отвечает за:

* очистку графика
* отрисовку X–Y
* обновление данных

---

# 14. Поток выполнения

```
Button Click
    ↓
Controller
    ↓
SolverThread.start()
    ↓
progress_signal → append_log()
    ↓
result_signal → update_plot()
```

---

# 15. Требования к Skeleton

1. GUI запускается.
2. Отображается лог-консоль.
3. При нажатии "Рассчитать" появляется лог.
4. SolverThread выполняет mock-вычисление.
5. База SQLite подключается.
6. Архитектура строго разделена.

---

# 16. Запрещено

* смешивать solver и GUI
* использовать pandas внутри core
* использовать глобальные переменные
* писать всё в одном файле
* реализовывать сложную физику в MVP

---

# 17. Цель генерации

Qwen должен:

* создать skeleton всех файлов
* сделать проект запускаемым
* обеспечить работу потока
* обеспечить работу лог-консоли
* добавить TODO в местах будущей физики

---

# Конец архитектурной инструкции

