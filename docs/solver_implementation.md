# Реализация Solver модуля (HydraFracApp)

## Содержание

1. [Обзор архитектуры](#обзор-архитектуры)
2. [Компоненты модуля](#компоненты-модуля)
   - [solver/solver.py — основной класс](#solversolverpy--основной-класс-reservoirsolver)
   - [solver/library.py — построение библиотеки кривых](#solverlibrarypy--построение-библиотеки-эталонных-кривых)
   - [solver/interpolation.py — интерполяция кривых](#solverinterpolationpy--интерполяция-кривых)
   - [solver/misfit.py — функция невязки](#solvermisfitpy--функция-невязки)
   - [solver/derivative.py — вычисление производных](#solverderivativepy--вычисление-производных)
   - [solver/metrics.py — метрики сравнения](#solvermetricspy--метрики-сравнения-кривых)
   - [solver/beam_search.py — выбор топ-k кандидатов](#solverbeam_searchpy--выбор-топ-k-кандидатов)
   - [solver/bayes_opt.py — байесовская оптимизация](#solverbayes_optpy--байесовская-оптимизация)
3. [Алгоритм работы](#алгоритм-работы)
4. [Типы данных](#типы-данных)

---

## Обзор архитектуры

Модуль **solver** реализует гибридный алгоритм решения обратной задачи ГДИС после МГРП. Архитектура построена по принципу конвейера:

```
Входные данные (X, Y)
        ↓
[Этап 0] Интерполяция на логарифмическую сетку
        ↓
[Этап 1] Beam Search → выбор Skin-фактора (top-k)
        ↓
[Этап 2] Перебор N → выбор количества трещин
        ↓
[Этап 3] Bayesian Optimization → оптимизация k и xf
        ↓
Результат: {skin, N, k, xf, misfit}
```

**Ключевые принципы:**
- **Без нормализации** на этапе сравнения кривых — сохраняется абсолютный масштаб параметров
- **Кэширование** интерполированной входной кривой для повторного использования
- **Два режима невязки:** `misfit_shape` (с нормировкой) для выбора формы, `misfit_aligned` (без нормировки) для оптимизации k

---

## Компоненты модуля

### solver/solver.py — основной класс ReservoirSolver

**Назначение:** главный orchestrator-класс, координирующий все этапы оптимизации.

**Основные методы:**

```python
class ReservoirSolver:
    def __init__(self, skin_library, progress_callback=None)
    
    def _prepare_input_curve(self, x_fact, y_fact, target_grid=None)
    
    def ensemble_misfit(self, x_ref, y_ref) -> float
    
    def select_skin(self, beam=3, N_fixed=None) -> Tuple[List[float], Dict]
    
    def select_N(self, skins, N_fixed=None) -> Tuple[Tuple, Dict]
    
    def optimize_continuous(self, sample, k_bounds, xf_bounds) -> Tuple[Dict, float]
    
    def solve(self, x_fact, y_fact, k_bounds, xf_bounds, N_fixed=None) -> Dict
```

**Параметры конструктора:**
- `skin_library` — словарь эталонных кривых, сгруппированный по Skin: `{skin_value: [samples]}`
- `progress_callback` — callback для отображения прогресса оптимизации

**Кэширование:**
- `_x_interp`, `_y_interp` — интерполированная входная кривая
- `_x_fact_orig`, `_y_fact_orig` — оригинальные входные данные
- При повторном вызове с теми же `x_fact` используется кэш

---

### solver/library.py — построение библиотеки эталонных кривых

**Назначение:** преобразование DataFrame с эталонными кривыми в структурированный словарь для быстрого поиска.

```python
def build_skin_library(df) -> Dict:
    """
    Построение библиотеки эталонных кривых из DataFrame.
    
    Args:
        df: DataFrame с колонками Skin, h, N, W, L, a/L, X, Y
        
    Returns:
        Dict: {skin_value: [samples]}
            где sample содержит:
                - 'dynamic': DataFrame с X, Y
                - 'h': эффективная толщина пласта
                - 'N': количество трещин
                - 'W': ширина трещины
                - 'L': полудлина трещины
                - 'a/L': отношение расстояния до границы к длине
    """
```

**Пример структуры:**
```python
skin_library = {
    -6.0: [
        {'dynamic': DataFrame(X, Y), 'h': 10, 'N': 1, 'W': 0.005, 'L': 50, 'a/L': 0.5},
        {'dynamic': DataFrame(X, Y), 'h': 10, 'N': 2, 'W': 0.005, 'L': 50, 'a/L': 0.5},
        ...
    ],
    -5.0: [...],
    ...
}
```

---

### solver/interpolation.py — интерполяция кривых

**Назначение:** приведение кривых к общей сетке для корректного сравнения.

```python
def interpolate_input_curve(x_fact, y_fact, x_ref) -> np.ndarray:
    """
    Интерполяция пользовательской кривой на сетку эталонной кривой.
    
    Args:
        x_fact: X координаты входной кривой
        y_fact: Y координаты входной кривой
        x_ref:  Целевая сетка X
        
    Returns:
        np.ndarray: Интерполированные значения Y
    """
```

**Особенности:**
- Использует `scipy.interpolate.interp1d` с `bounds_error=False` и `fill_value=np.nan`
- Автоматическая сортировка входных данных
- Проверка минимального количества точек (≥10)

```python
def interpolate_to_grid(x, y, grid) -> Tuple[np.ndarray, np.ndarray]:
    """
    Интерполяция кривой на заданную сетку.
    
    Returns:
        (grid, y_interp): Отфильтрованная сетка и интерполированные значения
    """
```

---

### solver/misfit.py — функция невязки

**Назначение:** вычисление различия между двумя кривыми через производные.

**Две реализации:**

#### 1. `misfit_shape()` — сравнение формы (с нормировкой)

```python
def misfit_shape(x1, y1, x2, y2,
                 derivative_mode="linear",
                 metric_type="integral",
                 n_points=200) -> float:
    """
    Невязка ФОРМЫ двух кривых через производную dY/dX.
    
    Используется для выбора Skin, N, a/L, L — когда масштаб Y (параметр k) ещё не известен.
    
    Нормировка по медиане:
      - Убирает влияние вертикального масштаба (k)
      - Сохраняет только форму кривой
      - Медиана робастна к выбросам на краях
    """
```

**Почему `derivative_mode="linear"`:**
- X и Y уже безразмерные параметры
- loglog-производная — двойная трансформация без выигрыша
- Линейная производная сохраняет информацию о переходных режимах

#### 2. `misfit_aligned()` — сравнение значений (без нормировки)

```python
def misfit_aligned(x1, y1, x2, y2,
                   derivative_mode="linear",
                   metric_type="integral",
                   n_points=200) -> float:
    """
    Невязка АЛЛАЙНЕД двух кривых БЕЗ нормировки.
    
    Используется для подбора k и xf — когда форма уже согласована.
    
    БЕЗ нормировки — сохраняется абсолютный масштаб k:
      - Маленький k → маленький Y → большая невязка
      - Большой k → большой Y → меньшая невязка
    """
```

**Общий алгоритм:**
1. Найти пересечение диапазонов X: `[xmin, xmax]`
2. Создать логарифмическую сетку на этом интервале
3. Интерполировать обе кривые на общую сетку
4. Применить нормировку (для `misfit_shape`)
5. Вычислить производные `dY/dX`
6. Рассчитать метрику расстояния

---

### solver/derivative.py — вычисление производных

**Назначение:** численное дифференцирование кривых.

```python
def compute_derivative(X, Y, mode="linear") -> Tuple[np.ndarray, np.ndarray]:
    """
    Вычисление производной dy/dx.
    
    Args:
        X: X координаты кривой
        Y: Y координаты кривой
        mode: 'linear' — линейный масштаб, 'loglog' — двойной логарифмический
        
    Returns:
        Tuple[X_filtered, alpha]: Отфильтрованные X и производная alpha
    """
```

**Режимы:**
- `mode="linear"`: `alpha = dY/dX` напрямую
- `mode="loglog"`: `alpha = d(log Y)/d(log X)` — логарифмическая производная

**Предобработка:**
- Фильтрация точек с `X > 0` и `Y > 0`

---

### solver/metrics.py — метрики сравнения кривых

**Назначение:** количественная оценка различия между массивами производных.

```python
def compute_metric(a1, a2, metric_type, X=None) -> float:
    """
    Метрика расстояния между двумя массивами производных.
    
    Args:
        a1, a2: массивы производных одинаковой длины
        metric_type: "L2", "L1", "integral"
        X: координаты для интегрирования (обязателен для "integral")
    """
```

**Доступные метрики:**

| Тип | Формула | Описание |
|-----|---------|----------|
| `L2` | Σ(a₁ - a₂)² | Квадратичная ошибка |
| `L1` | Σ|a₁ - a₂| | Линейная ошибка |
| `integral` | ∫|a₁ - a₂| dX | Площадь между кривыми |

**Важно (integral):**
```python
# ПРАВИЛЬНО: trapezoid(|a1 - a2|, X) — площадь между кривыми
# НЕВЕРНО: |trapezoid(a1) - trapezoid(a2)| — может быть нулём
#          при полном расхождении с разными знаками
```

---

### solver/beam_search.py — выбор топ-k кандидатов

**Назначение:** отбор лучших значений из словаря ошибок.

```python
def select_top_k(scores: Dict, k: int) -> List:
    """
    Выбор top-k лучших элементов из словаря по значениям.
    
    Args:
        scores: Словарь {ключ: значение_ошибки}
        k: Количество лучших элементов для возврата
        
    Returns:
        List: Список из k лучших ключей (отсортированных по возрастанию ошибки)
    """
```

**Используется на этапе 1 для выбора лучших Skin-факторов.**

---

### solver/bayes_opt.py — байесовская оптимизация

**Назначение:** оптимизация непрерывных параметров с использованием библиотеки Optuna.

```python
def bayesian_fit(objective, bounds, n_trials=50, progress_callback=None):
    """
    Bayesian optimization using Optuna.
    
    Args:
        objective: Функция для минимизации
        bounds: Словарь границ {name: (low, high)}
        n_trials: Количество итераций (по умолчанию 50)
        progress_callback: Callback для отображения прогресса
        
    Returns:
        Tuple[Dict, float]: (best_params, best_value)
    """
```

**Особенности:**
- Использует **TPE (Tree-structured Parzen Estimator)** — метод Optuna
- `log=True` для всех параметров — равномерное покрытие логарифмической шкалы
- In-memory storage (без сохранения в БД)

**Пример использования:**
```python
bounds = {
    "k": (1e-5, 10),    # проницаемость, мД
    "xf": (1e-3, 100)   # полудлина трещины, м
}

params, score = bayesian_fit(objective, bounds, n_trials=50)
```

---

## Алгоритм работы

### Этап 0: Подготовка входной кривой

```python
def _prepare_input_curve(self, x_fact, y_fact, target_grid=None):
    """
    1. Если target_grid не передан — создаётся логарифмическая сетка (200 точек)
    2. Интерполирует входную кривую на сетку
    3. Фильтрует NaN-значения
    4. Сохраняет результат в кэш
    
    Returns:
        (x_grid, y_interp): Интерполированная кривая
    """
```

### Этап 1: Выбор Skin-фактора (Beam Search)

```python
def select_skin(self, beam=3, N_fixed=None):
    """
    Алгоритм:
    1. Если задан N_fixed — фильтрация по количеству трещин
    2. Для каждого Skin находит медианные значения (h, W, L, a/L)
    3. Выбирает sample, ближайший к медиане
    4. Вычисляет misfit_shape для каждого Skin
    5. Возвращает top-k лучших Skin-значений
    
    Returns:
        (top_skins, scores): Список лучших Skin и словарь всех ошибок
    """
```

### Этап 2: Выбор N (количество трещин)

```python
def select_N(self, skins, N_fixed=None):
    """
    Алгоритм:
    1. Если N_fixed задан — используется напрямую (поиск ближайшего в библиотеке)
    2. Иначе — полный перебор всех N для каждого Skin
    3. Вычисляет misfit_shape для каждой комбинации (Skin, N)
    4. Возвращает лучшую комбинацию
    
    Returns:
        ((best_skin, best_N), scores): Лучшая пара и словарь ошибок
    """
```

### Этап 3: Байесовская оптимизация

```python
def optimize_continuous(self, sample, k_bounds, xf_bounds):
    """
    Алгоритм:
    1. Из sample извлекается референсная кривая (X_ref, Y_ref)
    2. Определяется objective-функция:
       
       def objective(params):
           k, xf = params
           # Модификация амплитуды кривой
           Y_mod = Y_ref * k * (1 + 0.1 * log10(xf + 1))
           # Сравнение БЕЗ нормализации
           error = self.ensemble_misfit(X_ref, Y_mod)
           return error
       
    3. Запускается bayesian_fit с границами k и xf
    4. Возвращаются оптимальные параметры
    
    Формула модификации:
      Y_mod = Y_ref × k × (1 + 0.1 × log₁₀(xf + 1))
    
    Важно: нормализация НЕ используется — сохраняется абсолютный масштаб k
    """
```

---

## Типы данных

### Входные данные

```python
# Входные данные (фактическая кривая ГДИС)
x_fact: np.ndarray  # время безразмерное
y_fact: np.ndarray  # давление/дебит безразмерные
```

### Библиотека кривых

```python
skin_library = Dict[float, List[Dict]]:
{
    skin_value: [
        {
            'dynamic': pd.DataFrame({'X': [...], 'Y': [...]}),
            'h': float,      # эффективная толщина пласта, м
            'N': int,        # количество трещин
            'W': float,      # ширина трещины, м
            'L': float,      # полудлина трещины, м
            'a/L': float     # отношение расстояния до границы к длине
        },
        ...
    ],
    ...
}
```

### Результат оптимизации

```python
result = {
    'skin': float,      # оптимальный Skin-фактор
    'N': int,           # оптимальное количество трещин
    'params': {
        'k': float,     # проницаемость, мД
        'xf': float     # полудлина трещины, м
    },
    'misfit': float     # значение функции невязки
}
```

---

## Зависимости

- **numpy** — численные вычисления
- **scipy** — интерполяция (`interp1d`), интегрирование (`trapezoid`)
- **optuna** — байесовская оптимизация
- **pandas** — работа с DataFrame

---

## Пример использования

```python
from solver.solver import ReservoirSolver
from solver.library import build_skin_library

# Загрузка библиотеки кривых
df_reference = pd.read_csv('reference_curves.csv')
skin_library = build_skin_library(df_reference)

# Создание решателя
solver = ReservoirSolver(skin_library)

# Запуск оптимизации
result = solver.solve(
    x_fact=np.array([...]),  # входные данные
    y_fact=np.array([...]),
    k_bounds=(1e-5, 10),     # границы проницаемости
    xf_bounds=(1e-3, 100),   # границы полудлины
    N_fixed=None             # или фиксированное N
)

print(f"Skin: {result['skin']}")
print(f"N: {result['N']}")
print(f"k: {result['params']['k']} мД")
print(f"xf: {result['params']['xf']} м")
print(f"Misfit: {result['misfit']}")
```
