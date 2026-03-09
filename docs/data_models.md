# Data Models Documentation

## Общие принципы

Архитектура данных разделена на **несколько независимых моделей**, которые управляются через центральный контейнер `AppState`.

```
RawDynamicData        → исходные пользовательские данные
ProcessingDynamicData → рабочие динамические данные
DimensionlessData     → безразмерные параметры (X,Y)
ReferenceCurve        → эталонная кривая из БД
SolverState           → текущее состояние оптимизации
AppState              → центральное состояние приложения
```

Ключевой принцип:

**Исходные данные никогда не изменяются.**

---

# 1. RawDynamicData

```python
@dataclass
class RawDynamicData
```

Хранит **исходные динамические данные пользователя**, загруженные из файла.

Источник данных:

```
CSV
LAS
```

### Поля

| поле                  | тип        | описание             |
| --------------------- | ---------- | -------------------- |
| t                     | np.ndarray | время                |
| P                     | np.ndarray | давление             |
| Q                     | np.ndarray | суммарный дебит      |
| is_Q_in_dynamic_input | bool       | был ли дебит в файле |

### Назначение

Это **оригинальный датасет пользователя**.

Используется как:

```
источник данных
точка восстановления (reset)
```

### Ограничения

Запрещено изменять:

```
t
P
Q
```

Эти данные считаются **фактическими измерениями**.

---

# 2. ProcessingDynamicData

```python
@dataclass
class ProcessingDynamicData
```

Хранит **рабочие динамические данные**, используемые алгоритмом.

Создаётся из:

```
RawDynamicData
```

но может изменяться в процессе обработки.

### Поля

| поле | описание            |
| ---- | ------------------- |
| t    | время               |
| P    | давление            |
| Q    | нормированный дебит |

Дополнительные поля:

| поле           | описание                     |
| -------------- | ---------------------------- |
| P_interpolated | давление после интерполяции  |
| t_extended     | время после экстраполяции    |
| P_extended     | давление после экстраполяции |
| Q_extended     | дебит после экстраполяции    |

### Назначение

Используется в этапах:

```
preprocessing
dimensionless calculations
solver
```

### Разрешённые изменения

Можно изменять:

```
P_interpolated
t_extended
P_extended
Q_extended
```

---

# 3. DimensionlessData

```python
@dataclass
class DimensionlessData
```

Хранит **безразмерные параметры интерпретации**.

### Поля

| поле | описание                             |
| ---- | ------------------------------------ |
| X    | безразмерный фильтрационный параметр |
| Y    | безразмерный ёмкостной параметр      |

### Источник данных

Вычисляется из:

```
ProcessingDynamicData
StaticParams
```

### Использование

Используется для:

```
сравнения с эталонными кривыми
оптимизации параметров
```

---

# 4. ReferenceCurve

```python
@dataclass
class ReferenceCurve
```

Модель **эталонной кривой из базы данных**.

Источник:

```
SQLite reference.db
```

### Поля

| поле          | описание                    |
| ------------- | --------------------------- |
| dynamic_data  | динамические данные эталона |
| dimensionless | безразмерные параметры      |
| static_params | параметры модели            |

Используется для:

```
сравнения с пользовательскими данными
```

---

# 5. SolverState

```python
@dataclass
class SolverState
```

Хранит **текущее состояние оптимизационного алгоритма**.

### Поля

| поле         | описание              |
| ------------ | --------------------- |
| k_current    | текущая проницаемость |
| L_current    | текущая длина трещины |
| skin_current | текущий skin-фактор   |
| residual     | значение невязки      |

Используется внутри solver.

---

# 6. AppState

```python
@dataclass
class AppState
```

Главный контейнер состояния приложения.

Через него взаимодействуют:

```
UI
processing
solver
storage
```

### Поля

| поле                    | описание                     |
| ----------------------- | ---------------------------- |
| raw_dynamic_data        | исходные данные пользователя |
| processing_dynamic_data | рабочие динамические данные  |
| dimensionless           | рассчитанные X,Y             |
| static_params           | статические параметры пласта |
| optimize_thresholds     | границы оптимизации          |
| reference_curve         | текущая эталонная кривая     |
| solver_state            | состояние оптимизации        |

---

# Поток данных

Полный pipeline системы:

```
CSV / LAS
   ↓
RawDynamicData
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

# Что можно изменять

Разрешено изменять:

```
ProcessingDynamicData
DimensionlessData
SolverState
```

---

# Что менять нельзя

Нельзя изменять структуру:

```
RawDynamicData
ReferenceCurve
AppState
```

Это **основные архитектурные модели системы**.

---

# Когда можно добавлять новые поля

| модель                | допустимо |
| --------------------- | --------- |
| ProcessingDynamicData | да        |
| DimensionlessData     | да        |
| SolverState           | да        |

Добавление в:

```
RawDynamicData
ReferenceCurve
AppState
```

требует изменения архитектуры.

---

# Архитектурная схема

```
RawDynamicData
       │
       ▼
ProcessingDynamicData
       │
       ▼
DimensionlessData
       │
       ▼
SolverState
```

---

## Ключевой принцип архитектуры

```
RawDynamicData — immutable
ProcessingDynamicData — mutable
```

---
