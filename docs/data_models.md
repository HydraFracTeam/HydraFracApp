# Data Models Documentation

## Общие принципы

Модели разделены на **два уровня данных**:

```
RawDynamicData        → исходные пользовательские данные
ProcessedDynamicData  → рабочие данные алгоритма
DimensionlessData     → безразмерные параметры
UserDataset           → объединённый контейнер данных задачи
```

Главный принцип:

**RawDynamicData никогда не изменяется алгоритмами.**

Все модификации выполняются в `ProcessedDynamicData`.

---

# 1. RawDynamicData

```python
@dataclass
class RawDynamicData
```

Хранит **исходные динамические данные пользователя**.

Источник:

```
CSV / LAS файл
```

Содержимое:

| поле                  | тип        | описание                      |
| --------------------- | ---------- | ----------------------------- |
| t                     | np.ndarray | время (часы)                  |
| P                     | np.ndarray | давление                      |
| Q                     | np.ndarray | дебит                         |
| is_Q_in_dynamic_input | bool       | был ли дебит в исходном файле |

### Важные правила

1️⃣ Эти данные **нельзя изменять алгоритмами обработки**.
2️⃣ Используются только как источник для `ProcessedDynamicData`.
3️⃣ Могут использоваться для **reset состояния приложения**.

---

# 2. ProcessedDynamicData

```python
@dataclass
class ProcessedDynamicData
```

Хранит **рабочие данные**, которые могут изменяться.

Создаётся на основе `RawDynamicData`.

Содержимое:

| поле | тип        | описание |
| ---- | ---------- | -------- |
| t    | np.ndarray | время    |
| P    | np.ndarray | давление |
| Q    | np.ndarray | дебит    |

Дополнительные поля:

| поле           | описание                     |
| -------------- | ---------------------------- |
| P_interpolated | давление после интерполяции  |
| t_extended     | время после экстраполяции    |
| P_extended     | давление после экстраполяции |
| Q_extended     | дебит после экстраполяции    |

### Разрешённые изменения

Можно изменять:

```
P_interpolated
t_extended
P_extended
Q_extended
```

Нельзя изменять:

```
t
P
Q
```

Эти значения считаются **базовыми измерениями**.

---

# 3. DimensionlessData

```python
@dataclass
class DimensionlessData
```

Хранит **безразмерные параметры**, используемые в интерпретации.

| поле | описание                             |
| ---- | ------------------------------------ |
| X    | безразмерный фильтрационный параметр |
| Y    | безразмерный ёмкостной параметр      |

Эти данные вычисляются из:

```
ProcessedDynamicData
StaticParams
```

---

# 4. SolverState

```python
@dataclass
class SolverState
```

Хранит **текущее состояние оптимизационного алгоритма**.

| поле         | описание              |
| ------------ | --------------------- |
| k_current    | текущая проницаемость |
| L_current    | текущая длина трещины |
| skin_current | текущий skin фактор   |
| residual     | значение невязки      |

Используется внутри solver.

---

# 5. UserDataset

```python
@dataclass
class UserDataset
```

Главный контейнер данных пользователя.

Объединяет:

```
ProcessedDynamicData
DimensionlessData
StaticParams
OptimizeThresholds
```

| поле                | описание                     |
| ------------------- | ---------------------------- |
| dynamic_data        | рабочие динамические данные  |
| dimensionless       | безразмерные параметры       |
| static_params       | статические параметры пласта |
| optimize_thresholds | границы оптимизации          |

---

# 6. ReferenceCurve

```python
@dataclass
class ReferenceCurve
```

Описывает **эталонную кривую из базы данных**.

Источник:

```
SQLite reference database
```

| поле          | описание                      |
| ------------- | ----------------------------- |
| dynamic_data  | эталонные динамические данные |
| dimensionless | эталонные X,Y                 |
| static_params | параметры модели              |

Используется для сравнения с пользовательскими данными.

---

# Поток данных в системе

Полный pipeline:

```
CSV / LAS
   ↓
RawDynamicData
   ↓
ProcessedDynamicData
   ↓
DimensionlessData
   ↓
Solver
```

---

# Что можно изменять

Разрешено менять:

```
ProcessedDynamicData
DimensionlessData
SolverState
```

---

# Что менять нельзя

Нельзя изменять структуру:

```
RawDynamicData
UserDataset
ReferenceCurve
```

Эти структуры являются **основой архитектуры данных**.

---

# Когда добавлять новые поля

Добавлять новые поля можно:

| модель               | допустимо |
| -------------------- | --------- |
| ProcessedDynamicData | да        |
| DimensionlessData    | да        |
| SolverState          | да        |

Добавлять в:

```
RawDynamicData
UserDataset
```

нужно **очень осторожно**, так как это влияет на весь pipeline.

---

# Краткая схема архитектуры

```
RawDynamicData
       │
       ▼
ProcessedDynamicData
       │
       ▼
DimensionlessData
       │
       ▼
SolverState
       │
       ▼
SolverResult
```


