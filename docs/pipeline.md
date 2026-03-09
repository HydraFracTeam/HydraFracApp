---

# Application Workflow

Документ описывает поток данных и этапы работы приложения интерпретации ГДИС.

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
ProcessingDynamicData Creation
   ↓
Preprocessing
   ↓
Dimensionless Calculation
   ↓
Solver
   ↓
Results Visualization
```

---

# 1. Загрузка динамических данных

Источник:

```
CSV
LAS
```

Процесс:

```
UI
 ↓
csv_loader / las_loader
 ↓
RawDynamicData
```

Валидация выполняется через:

```
schemas.raw_dynamic_input.RawDynamicDataInput
```

Результат сохраняется в:

```
AppState.raw_dynamic_data
```

Содержимое:

```
t
P
Q
is_Q_in_dynamic_input
```

После загрузки UI разблокирует ввод статичных параметров.

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
P0 (пластовое давление)
```

Если дебит отсутствует в файле:

```
Q_constant
```

Валидация выполняется через:

```
schemas.static_params.StaticParams
```

Результат сохраняется в:

```
AppState.static_params
```

Если дебит был константным:

```
RawDynamicData.Q = Q_constant
```

---

# 3. Ввод границ оптимизации

Пользователь задаёт диапазоны:

```
L_min
L_max
k_min
k_max
```

Валидация:

```
schemas.optimize_thresholds.OptimizeThresholds
```

Результат:

```
AppState.optimize_thresholds
```

---

# 4. Создание рабочего набора динамических данных

На основе исходных данных создаётся рабочая модель:

```
ProcessingDynamicData
```

Создание:

```
ProcessingDynamicData(
    t = RawDynamicData.t
    P = RawDynamicData.P
    Q = normalize_Q_by_n(Q_total, N)
    dp = calculate_dP(RawDynamicData.P, StaticParams.P0)
)
```

Сохраняется в:

```
AppState.processing_dynamic_data
```

---

# 5. Preprocessing

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

Результат сохраняется в:

```
ProcessingDynamicData
```

Поля:

```
dP
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
ProcessingDynamicData
StaticParams
```

Результат:

```
DimensionlessData
```

Сохраняется в:

```
AppState.dimensionless
```

Поля:

```
X
Y
```

---

# 7. Работа solver

Модуль:

```
core/solver.py
```

Использует:

```
DimensionlessData
ReferenceCurve
OptimizeThresholds
```

Алгоритм:

```
1. перебор skin
2. масштабирование по W
3. выбор эталонной кривой
4. оптимизация k и L
5. вычисление невязки
```

Метрика:

```
L1 или L2 между XY кривыми
```

Результат сохраняется в:

```
AppState.solver_state
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

Сбрасывает состояние:

```
AppState = AppState()
```

и интерфейс возвращается в исходное состояние.

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
ProcessingDynamicData
   ↓
DimensionlessData
   ↓
Solver
   ↓
SolverState
```

---

# Ключевой принцип архитектуры

Исходные данные **никогда не изменяются**.

```
RawDynamicData → immutable
```

Рабочие изменения происходят только в:

```
ProcessingDynamicData
DimensionlessData
SolverState
```
