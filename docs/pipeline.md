---

# Application Workflow

Документ описывает полный поток данных и действий в приложении интерпретации ГДИС.

---

# Общая архитектура

Pipeline работы приложения:

```
User Input
   ↓
Dynamic Data Loading
   ↓
Static Parameters Input
   ↓
Optimization Bounds Input
   ↓
UserDataset Creation
   ↓
Preprocessing
   ↓
Dimensionless Transformation
   ↓
Solver
   ↓
Results Visualization
```

---

# 1. Загрузка динамических данных

Источник:

```
CSV файл
LAS файл
```

Процесс:

```
UI → csv_loader / las_loader → RawDynamicData
```

Проверки выполняются через:

```
schemas.raw_dynamic_input.RawDynamicDataInput
```

Результат:

```
AppState.raw_dynamic
```

Содержит:

```
t
P
Q
is_Q_in_dynamic_input
```

После успешной загрузки:

```
UI → разблокирует ввод статичных параметров
```

---

# 2. Ввод статичных параметров

Пользователь вводит:

```
W
h
mu
phi
B
ct
N
```

Если в динамических данных **нет дебита**, пользователь вводит:

```
Q_constant
```

Валидация выполняется через:

```
schemas.static_params.StaticParams
```

После успешной проверки:

```
AppState.static_params
```

Если дебит не был в файле:

```
Q = Q_constant / N
```

и заполняется массив:

```
RawDynamicData.Q
```

После этого UI разблокирует следующий этап.

---

# 3. Ввод границ оптимизации

Пользователь задаёт диапазоны:

```
L_min
L_max
k_min
k_max
```

Проверка выполняется через:

```
schemas.optimize_thresholds.OptimizeThresholds
```

Результат:

```
AppState.optimize_thresholds
```

---

# 4. Создание рабочего датасета

После ввода всех данных создаётся основной контейнер:

```
UserDataset
```

Он содержит:

```
ProcessedDynamicData
StaticParams
OptimizeThresholds
DimensionlessData (пока None)
```

Создание ProcessedDynamicData:

```
ProcessedDynamicData(
    t = RawDynamicData.t
    P = RawDynamicData.P
    Q = RawDynamicData.Q
)
```

Сохраняется:

```
AppState.fact_data
```

После этого пользователь может запускать расчёт.

---

# 5. Preprocessing

Перед интерпретацией выполняется обработка данных.

Модуль:

```
processing/preprocessing.py
```

Операции:

```
1. интерполяция пропусков давления
2. сглаживание давления
3. экстраполяция временного ряда
```

Изменяется:

```
ProcessedDynamicData
```

Добавляются:

```
P_interpolated
t_extended
P_extended
Q_extended
```

---

# 6. Расчёт безразмерных параметров

Модуль:

```
core/dimensionless.py
```

Использует:

```
ProcessedDynamicData
StaticParams
```

Результат:

```
DimensionlessData
```

Содержит:

```
X
Y
```

Сохраняется в:

```
UserDataset.dimensionless
```

---

# 7. Работа solver

Модуль:

```
core/solver.py
```

Использует:

```
UserDataset
ReferenceCurves
```

Алгоритм:

```
1. перебор skin
2. масштабирование по W
3. интерполяция эталонных кривых
4. оптимизация k и L
5. вычисление ошибки
```

Метрика ошибки:

```
L1 или L2 между XY кривыми
```

Результат:

```
SolverResult
```

---

# 8. Вывод результатов

В UI отображаются:

```
skin
k
L
```

Заполняются элементы:

```
skin_result_spinbox
frac_length_result_spinbox
permeability_result_spinbox
```

---

# 9. Reset состояния

Кнопка:

```
reset_data_button
```

Выполняет:

```
AppState = AppState()
```

и UI возвращается к начальному состоянию.

---

# AppState

Центральный контейнер состояния приложения.

Хранит:

```
raw_dynamic
static_params
optimize_thresholds
fact_data (UserDataset)
solver_state
solver_result
```

---

# Полный поток данных

```
CSV/LAS
   ↓
RawDynamicData
   ↓
StaticParams
   ↓
OptimizeThresholds
   ↓
ProcessedDynamicData
   ↓
DimensionlessData
   ↓
Solver
   ↓
Results
```

---

# Ключевой принцип архитектуры

Исходные данные **никогда не изменяются**.

```
RawDynamicData → immutable
```

Все изменения происходят в:

```
ProcessedDynamicData
DimensionlessData
```

