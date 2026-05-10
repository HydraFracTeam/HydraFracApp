# Архитектура HydraFracApp — полный обзор

> Дата последнего обновления: май 2026

---

## 1. Общая структура проекта

```
main.py  ← точка входа
   │
   └── session.py  ← сессия (главный контроллер)
          │
          ├── core/          ← данные и физика
          ├── processing/    ← предобработка динамических данных
          ├── solver/        ← подбор параметров трещины
          ├── ui/            ← PySide6 + pyqtgraph
          ├── helpers/       ← утилиты-однострочники
          ├── schemas/       ← Pydantic-валидация
          ├── sessions/      ← сохранение/загрузка .fflow
          ├── config.py      ← глобальные настройки
          └── storage/db/    ← SQLite с эталонными кривыми
```

---

## 2. Модели данных (`core/models.py`)

Все модели — `dataclass`'ы без встроенной валидации (валидация вынесена в `schemas/`).

### 2.1. `RawDynamicData`

Сырые данные пользователя. **Никогда не изменяются** после загрузки.

```python
@dataclass
class RawDynamicData:
    t: np.ndarray                    # время
    P: np.ndarray                    # давление
    Q: np.ndarray                    # дебит
    is_Q_in_dynamic_input: bool      # был ли дебит в исходном файле
```

### 2.2. `ProcessingDynamicData`

Рабочая версия данных — то, с чем проводятся операции preprocessing.

```python
@dataclass
class ProcessingDynamicData:
    t: np.ndarray
    P: np.ndarray
    Q: np.ndarray
    dP: Optional[np.ndarray]         # депрессия P0 - P
    burde: Optional[np.ndarray]      # производная Бурде
    is_Q_normalized: bool            # нормирован ли дебит на N

    # Маски интерполяции
    P_interpolated_mask: Optional[np.ndarray]
    is_P_interpolated: bool

    Q_interpolated_mask: Optional[np.ndarray]
    is_Q_interpolated: bool

    # Маски экстраполяции
    t_extrapolated_mask: Optional[np.ndarray]
    is_t_extrapolated: bool

    P_extrapolated_mask: Optional[np.ndarray]
    is_P_extrapolated: bool

    Q_extrapolated_mask: Optional[np.ndarray]
    is_Q_extrapolated: bool
```

### 2.3. `DimensionlessData`

Безразмерные параметры X и Y.

```python
@dataclass
class DimensionlessData:
    X: np.ndarray   # фильтрационный параметр
    Y: np.ndarray   # ёмкостной параметр
```

Формулы:

```
X = 0.00864 * k * h * |ΔP| / (μ * B * Q)
Y = Q * B * t / (24 * φ * ct * h * |ΔP| * L²)
```

### 2.4. `SolverState`

Текущее состояние решения.

```python
@dataclass
class SolverState:
    k_current: float    # текущая проницаемость (мД)
    L_current: float    # текущая полудлина трещины (м)
    skin_current: float # текущий Skin-фактор
    residual: float     # невязка
```

### 2.5. Референсные кривые (результат солвера)

```python
ReferenceCurves
   ├── main: Optional[MainRefCurve]
   │         ├── dimensionless: DimensionlessData
   │         └── static_params: RefStaticParams (Skin, h, N, W, L, aL)
   └── neighbours: Optional[List[NeighbourRefCurve]]
                     ├── dimensionless
                     └── skin_offset: int  (-2, -1, +1, +2)
```

### 2.6. `ProcessingOperationResult`

Возвращается каждой операцией preprocessing.

```python
@dataclass(slots=True)
class ProcessingOperationResult:
    data: ProcessingDynamicData
    operation: str
    details: List[str]       # человекочитаемые логи
```

---

## 3. `AppState` (`core/app_state.py`) — центральное состояние

Единственный контейнер состояния всей сессии. Хранит всё, без бизнес-логики.

```python
@dataclass
class AppState:
    raw_dynamic_data: Optional[RawDynamicData]
    processing_dynamic_data: Optional[ProcessingDynamicData]
    dimensionless: Optional[DimensionlessData]
    static_params: Optional[StaticParams]
    optimize_thresholds: Optional[OptimizeThresholds]
    solver_state: Optional[SolverState]
    reference_curves: Optional[ReferenceCurves]
```

---

## 4. Pipeline данных (основной поток)

```
Загрузка (CSV/LAS/clipboard)
    │
    ▼
RawDynamicData  ←── autosplit (КСД/КВД)
    │
    ├──→ raw_to_processing()
    │       └── проверка len(P) == len(Q)
    ▼
ProcessingDynamicData  ←── preprocessing (interp, extrap, smooth, outliers)
    │                         через copy_processing_data + rollback
    │
    └──→ rebuild_processing_dynamic()
    │       └── normalize_Q_by_n(), calculate_dP(), calculate_burde()
    │
    ▼
ProcessingDynamicData (полный: dP, burde, Q нормирован)
    │
    └──→ recalculate_dimensionless()
    │       └── calculate_x(), calculate_y()
    ▼
DimensionlessData (X, Y)  ←── использует solver_state.k_current, solver_state.L_current
    │
    └──→ Solver.solve_from_dimensionless()
    ▼
SolverResult → reference_curves → CompareDialog
```

---

## 5. Preprocessing pipeline

### 5.1. Механизм rollback

`_apply_preprocessing()` в `session.py`:

1. **Копия** `ProcessingDynamicData` через `copy_processing_data()` (легковесная, только `.copy()` для ndarray)
2. **Применение** цепочки actions (interpolate → extrapolate → smooth → outliers)
3. **При ошибке**: логирование + QMessageBox, **оригинал не тронут**
4. **При успехе**: сохранение → `recalculate_processing_dynamic_data()` → `recalculate_dimensionless()` → `refresh_ui()`

### 5.2. Доступные операции

| Кнопка | Actions | Что делает |
|---|---|---|
| Интерполяция | `extend_masks → interpolate_pressure → interpolate_debit` | Pchip для P, step-fill для Q |
| Экстраполяция | `extrapolate_time → extend_masks → extrapolate_pressure → extrapolate_debit` | Время + log-регрессия для P, const для Q |
| Сглаживание | `smooth_pressure` | Savitzky–Golay (auto window) |
| Выбросы | `remove_pressure_outliers` | MAD + median (window=7, threshold=7) |
| Сброс | `raw_to_processing(raw)` | Полный откат к исходным |

### 5.3. `copy_processing_data` (`helpers/copy_processing_data.py`)

Лёгковесная альтернатива `deepcopy`. Не копирует Python-метаданные — только ndarray через `.copy()`.

```python
def copy_processing_data(src: ProcessingDynamicData) -> ProcessingDynamicData:
    return ProcessingDynamicData(
        t=src.t.copy(),
        P=src.P.copy(),
        Q=src.Q.copy(),
        dP=src.dP.copy() if src.dP is not None else None,
        # ... остальные поля аналогично
    )
```

Производительность: ~10-30x быстрее `deepcopy`.

---

## 6. Solver — ступенчатый подбор параметров

### 6.1. Физика

Безразмерные параметры:

```
X = 0.00864 * k * h * |ΔP| / (μ * B * Q)
Y = Q * B * t / (24 * φ * ct * h * |ΔP| * L²)
```

Сравнение кривых идёт по **производной dY/dX** в **linear**-режиме (не loglog — для безразмерных кривых это двойная трансформация без выигрыша).

### 6.2. Алгоритм (5 шагов)

```
Шаг 0: Фильтрация библиотеки по W + N
Шаг 1: select_skin   — Beam search по форме кривой (dY/dX) с h-взвешиванием
Шаг 2: select_N      — если N не фиксирован пользователем
Шаг 3: select_aL     — перебор a/L при фиксированных Skin, N
Шаг 4: select_L      — перебор L + blend между соседними значениями
Шаг 5: recover_k     — аналитически: k_real = k_ref * median(X_fact) / median(X_ref)
```

### 6.3. Выравнивание кривых (`align_fact_to_ref`)

Перед каждым сравнением кривые выравниваются по X:

1. **Якорный сдвиг** по первой точке X (совмещение начал):
   ```
   shift_x = x_ref[0] / x_fact[0]
   x_anchored = x_fact * shift_x
   ```
2. Y не трогается — только X.

### 6.4. Misfit

| Функция | Нормировка | Использование |
|---|---|---|
| `misfit_shape` | По медиане Y | Выбор формы кривой (Skin, N, a/L, L) |
| `misfit_aligned` | Без нормировки | Восстановление k (важен абсолютный масштаб) |

**Метрики**: integral (по умолчанию), L1, L2.

### 6.5. Восстановление k (шаг 5)

Аналитически, без подбора:

```
k_real = k_ref * median(X_fact) / median(X_ref)
```

Где `k_ref = 5.0` — проницаемость, при которой считались эталонные кривые.

### 6.6. Blend кривых (шаг 4)

Если две соседние L дают сравнимые ошибки, между ними строится интерполяция:

```python
alpha = _choose_alpha(F1, F2)
x_blend = (1-alpha) * x1 + alpha * x2
```

Правила выбора alpha:
- Ошибки различаются < 30% → берём лучшую
- 30-40% → линейная интерполяция
- > 40% → середина (0.5)

### 6.7. Слои solver'a

| Файл | Класс / функции | Назначение |
|---|---|---|
| `solver_wrapper.py` | `Solver`, `SolverResult` | Обёртка, вызываемая из UI |
| `solver_new.py` | `ReservoirSolver` | Ступенчатый алгоритм (основной) |
| `solver_worker.py` | `SolverWorker` | QThread-обёртка для асинхронного запуска |
| `misfit.py` | `misfit_shape`, `misfit_aligned` | Функции невязки |
| `derivative.py` | `compute_derivative` | Производная dY/dX |
| `metrics.py` | `compute_metric` | L1, L2, integral |
| `interpolation.py` | — | Интерполяция кривых |
| `beam_search.py` | `select_top_k` | Отбор top-k кандидатов |
| `library.py` | — | Построение библиотеки из БД |
| `solver.py` | — | Устаревшая версия (solver v1) |

---

## 7. База эталонных кривых (SQLite)

**Файл**: `storage/db/reference_curves.db`

**Таблицы**:

```sql
dynamics: curve_id | elemIdx | X | Y
statics:  curve_id | Skin | h | N | W | L | aL
```

**Доступ** через `ReferenceRepository` (`core/reference_repo.py`):

| Метод | Назначение |
|---|---|
| `get_skin_library()` | Загрузка всей библиотеки |
| `find_best_curve(skin, L, N, W)` | Поиск лучшей кривой |
| `find_neighbor_curves(skin, L, N, W)` | Соседи по Skin |

**Константы библиотеки** (`config.py`):

```python
REF_k   = 5      # проницаемость (мД)
REF_phi = 0.2    # пористость
REF_mu  = 1      # вязкость (сП)
REF_B   = 1      # объёмный коэффициент
REF_ct  = 4e-5   # сжимаемость (1/атм)
REF_P0  = 300    # пластовое давление (атм)
```

---

## 8. UI слой

### 8.1. `main.py` — MDI контейнер

- `QMainWindow` с `QTabWidget`
- Каждая вкладка = `SessionWidget`
- Кнопка "+" для новой сессии
- Закрытие вкладок (кроме последней)

### 8.2. `session.py` — контроллер сессии

- Все сигналы/слоты UI
- Включение/выключение контролов по этапам:
  ```
  load → static → thresholds → calculate
  ```
- Управление видимостью доков (через чекбоксы)
- Асинхронный запуск солвера через `QThread` + `SolverWorker`

### 8.3. Управление контролами

```python
_load_controls:       кнопки загрузки данных
_static_controls:     spinbox'ы статических параметров
_threshold_controls:  spinbox'ы границ оптимизации
_calculation_controls: результаты солвера
```

Методы `enable_*()` / `disable_*()` управляют доступностью на каждом этапе.

### 8.4. Модули UI (`ui/`)

| Файл | Назначение |
|---|---|
| `ui.py` | Сгенерирован из `main_ui.ui` (Qt Designer) |
| `ui_setup.py` | Сборка DockArea |
| `plot_pressure.py` | График давления P(t) |
| `plot_debit.py` | График дебита Q(t) |
| `plot_xy.py` | Безразмерные кривые X(Y) |
| `plot_burde.py` | Производная Бурде |
| `plot_autosplit_line.py` | Линия разделения КСД/КВД |
| `data_table.py` | Табличное представление данных |
| `compare_dialog.py` | Диалог сравнения результатов |
| `downsampling.py` | LTTB-даунсемплинг для графиков |
| `report_service.py` | Сервис логов в текстовое поле |
| `paste_dialog_data.py` | Диалог вставки из буфера |
| `autosplit_dialog.py` | Диалог выбора режима КСД/КВД |
| `fill_state_to_ui.py` | Заполнение UI при загрузке сессии |
| `export_processing_to_csv.py` | Экспорт таблицы в CSV |
| `clear_plot.py` | Очистка графиков |
| `solution_view.py` | Просмотр решения |

---

## 9. Сериализация (`.fflow`)

### 9.1. Формат файла

```
.fflow = zstd(tar(parquet + json))
```

### 9.2. Структура внутри

```
tmpdir/
├── raw.parquet          (t, P, Q)
├── processing.parquet   (t, P, Q, маски)
├── meta.json            (флаги, static_params, thresholds, solver_state)
└── data.tar.zst         (архив, сжатый zstd level 10)
```

### 9.3. `sessions/save_state.py`

Использует: `pandas`, `pyarrow`, `zstandard`.

```python
# RAW → raw.parquet
df = pd.DataFrame({"t": raw.t, "P": raw.P, "Q": raw.Q})
pq.write_table(pa.Table.from_pandas(df), tmp / "raw.parquet")

# PROCESSING → processing.parquet
# META → meta.json
# TAR → zstd → .fflow
```

### 9.4. `sessions/load_state.py`

Обратный процесс: распаковка → загрузка parquet → восстановление `AppState` → `fill_state_to_ui()`.

---

## 10. Вспомогательные модули

### `helpers/`

| Файл | Функция | Назначение |
|---|---|---|
| `calculate_dP.py` | `calculate_dP(P, P0)` | Депрессия `dP = P0 - P` |
| `calculate_burde.py` | `calculate_burde(t, dP)` | Производная Бурде |
| `calculate_k_value.py` | `calculate_k_value(k_min, k_max)` | Начальное k: `sqrt(k_min * k_max)` |
| `calculate_L_value.py` | `calculate_L_value(L_min, L_max)` | Начальное L: `sqrt(L_min * L_max)` |
| `normalize_Q_by_n.py` | `normalize_Q_by_n(Q, N)` | Нормировка дебита: `Q / N` |
| `copy_processing_data.py` | `copy_processing_data(src)` | Лёгковесное копирование `ProcessingDynamicData` |

### `schemas/` (Pydantic)

| Схема | Поля | Назначение |
|---|---|---|
| `StaticParams` | W, h, mu, phi, B, ct, N, P0, Q_constant | Валидация статических параметров |
| `OptimizeThresholds` | L_min, L_max, k_min, k_max | Валидация границ оптимизации |
| `RawDynamicDataInput` | t, P, Q | Валидация загруженных динамических данных |

### `processing/loaders/`

| Файл | Формат | Что читает |
|---|---|---|
| `csv_loader.py` | `.csv` | t, P, Q (Q опционально) |
| `las_loader.py` | `.las` | t, P, Q из LAS-формата |

### `autosplitter` (`processing/`)

Автоматическое разделение КСД/КВД по пороговому времени:

```
t ≤ 50000     → КСД (кривая стабилизации давления)
t > 50000.01  → КВД (кривая восстановления давления)
```

Возможные режимы:
- `ksd` — только КСД
- `kvd` — только КВД
- `both` — оба режима (с предупреждением)
- `ignore` — отключить

---

## 11. Дополнительные файлы

| Файл | Назначение |
|---|---|
| `config.py` | Глобальные настройки (путь к БД, константы библиотеки) |
| `ARCHITECTURE.md` | Краткое описание архитектуры (корневой) |
| `README.md` | Общее описание проекта |

---

## 12. Ключевые архитектурные решения

1. **Однонаправленный поток данных**: Raw → Processing → Dimensionless → Solver. Никаких циклических зависимостей.

2. **Rollback при preprocessing**: копия → операции → при ошибке оригинал нетронут.

3. **Сравнение по форме dY/dX** (не по абсолютным значениям) — позволяет подбирать параметры без знания k на ранних шагах.

4. **k восстанавливается аналитически** из соотношения медиан X, а не подбором.

5. **Blend кривых** при интерполяции L между дискретными значениями библиотеки.

6. **Beam search** — не полный перебор, а top-k на каждом шаге (ускорение).

7. **Легковесное копирование** — только `.copy()` для ndarray, без `deepcopy` (10-30x быстрее).

8. **Сохранение в .fflow** — Parquet + zstd, компактно и быстро.

9. **Async solver** — через QThread, UI не блокируется.

10. **DockArea** — гибкое расположение графиков, скрытие/показ через чекбоксы.

11. **Единственный источник истины** — весь стейт в `AppState`, никаких дублирующих полей.

12. **Backward compatibility** — старые preprocessing-функции (возвращающие `ProcessingDynamicData`) поддерживаются наряду с новыми (возвращающими `ProcessingOperationResult`).

---

## 13. Потенциальные проблемы / TODO

- `_draw_autosplit_line()` рисует на `self.ui.p_graphic`, а основные графики — на `self.ui.plot_pressure` (разные виджеты)
- `ProcessingDynamicData.dP` и `burde` не сохраняются в `.fflow` — пересчитываются при загрузке
- Нет прогресс-бара для солвера — только сообщение "Солвер запущен, идет расчет..."
- `reset_all_data()` не останавливает работающий solver thread
- Нет unit-тестов для solver'a (см. `pytest.ini`)
