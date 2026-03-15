# Техническое описание Solver (HydraFracApp)

## Содержание

1. [Общее описание](#общее-описание)
2. [Архитектура системы](#архитектура-системы)
3. [Основной класс ReservoirSolver](#основной-класс-reservoirsolver)
4. [Этапы оптимизации](#этапы-оптимизации)
   - [Этап 0: Подготовка входной кривой](#этап-0-подготовка-входной-кривой)
   - [Этап 1: Выбор Skin-фактора (Beam Search)](#этап-1-выбор-skin-фактора-beam-search)
   - [Этап 2: Выбор N (количество трещин)](#этап-2-выбор-n-количество-трещин)
   - [Этап 3: Байесовская оптимизация непрерывных параметров](#этап-3-байесовская-оптимизация-непрерывных-параметров)
5. [Функция невязки (Misfit)](#функция-невязки-misfit)
6. [Метрики сравнения кривых](#метрики-сравнения-кривых)
7. [Производные и их вычисление](#производные-и-их-вычисление)
8. [Интерполяция кривых](#интерполяция-кривых)
9. [Библиотека эталонных кривых](#библиотека-эталонных-кривых)
10. [Взаимодействие с UI и core модулями](#взаимодействие-с-ui-и-core-модулями)

---

## Общее описание

Solver — это модуль оптимизации в приложении HydraFracApp, предназначенный для решения **обратной задачи интерпретации данных гидродинамических исследований скважин (ГДИС)** после многостадийного гидроразрыва пласта (МГРП).

**Цель оптимизации** — определить следующие параметры пласта и трещины:
- **S (Skin)** — скин-фактор, характеризующий повреждение призабойной зоны
- **N** — количество трещин в системе
- **k** — проницаемость пласта, мД
- **L (xf)** — полудлина трещины, м

**Метод решения** — гибридный подход, сочетающий:
1. **Beam Search** (поиск по лучу) — для дискретных параметров (Skin, N)
2. **Bayesian Optimization** (байесовская оптимизация) — для непрерывных параметров (k, xf)

---

## Архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│                         HydraFracApp                            │
├─────────────────────────────────────────────────────────────────┤
│  UI Layer                                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ui/ui.py                                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Core Layer                                                      │
│  ┌────────────────────┐  ┌─────────────────────────────────┐   │
│  │ core/solver.py     │  │ core/reference_repo.py          │   │
│  │ (Solver class)    │  │ (ReferenceRepository class)     │   │
│  └────────────────────┘  └─────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  Solver Module                                                    │
│  ┌────────────────────┐  ┌─────────────────────────────────┐   │
│  │ solver/solver.py   │  │ solver/library.py               │   │
│  │ (ReservoirSolver) │  │ (build_skin_library)            │   │
│  └────────────────────┘  └─────────────────────────────────┘   │
│  ┌────────────────────┐  ┌─────────────────────────────────┐   │
│  │ solver/misfit.py   │  │ solver/metrics.py              │   │
│  │ (misfit function) │  │ (compute_metric)               │   │
│  └────────────────────┘  └─────────────────────────────────┘   │
│  ┌────────────────────┐  ┌─────────────────────────────────┐   │
│  │ solver/derivative.py│ │ solver/interpolation.py        │   │
│  │ (compute_derivative)│ │ (interpolate_input_curve)      │   │
│  └────────────────────┘  └─────────────────────────────────┘   │
│  ┌────────────────────┐  ┌─────────────────────────────────┐   │
│  │ solver/bayes_opt.py│  │ solver/beam_search.py           │   │
│  │ (bayesian_fit)    │  │ (select_top_k)                  │   │
│  └────────────────────┘  └─────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  Storage Layer                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ storage/db/reference_curves.db (SQLite)                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Основной класс ReservoirSolver

### [`solver/solver.py`](solver/solver.py) — класс `ReservoirSolver`

Класс `ReservoirSolver` является ядром модуля оптимизации. Он инкапсулирует всю логику сопоставления входных данных с эталонными кривыми.

#### Конструктор

```python
def __init__(self, skin_library, progress_callback=None):
```

**Параметры:**
- `skin_library` — словарь, организованный по значениям Skin-фактора: `{skin_value: [samples]}`
- `progress_callback` — функция обратного вызова для отображения прогресса оптимизации

**Атрибуты:**
```python
self.derivative_modes = ["linear", "loglog"]  # Режимы вычисления производной
self.metric_types = ["L2", "L1", "integral"]   # Типы метрик невязки
self._x_interp = None  # Кэш интерполированных X входной кривой
self._y_interp = None  # Кэш интерполированных Y входной кривой
```

---

## Этапы оптимизации

### Этап 0: Подготовка входной кривой

#### [`_prepare_input_curve(x_fact, y_fact, target_grid=None)`](solver/solver.py:32)

```python
def _prepare_input_curve(self, x_fact, y_fact, target_grid=None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Однократная подготовка входной кривой.
    
    Интерполирует входную кривую на стандартную сетку (логарифмическую).
    Результат сохраняется для повторного использования.
    
    Args:
        x_fact: X координаты входной кривой (фактические данные)
        y_fact: Y координаты входной кривой (фактические данные)
        target_grid: Целевая сетка (если None, создается логарифмическая 200 точек)
        
    Returns:
        x_grid, y_interp: Интерполированная кривая
    """
```

**Алгоритм:**

1. **Проверка кэша:** Если входные данные не изменились, используется кэшированный результат
2. **Создание логарифмической сетки:**
   ```python
   x_min = max(min(x_fact), 1e-10)  # Избегаем нуля
   x_max = max(x_fact)
   x_grid = np.logspace(np.log10(x_min), np.log10(x_max), 200)
   ```
3. **Интерполяция:** Линейная интерполяция (`scipy.interpolate.interp1d`)
4. **Фильтрация NaN:** Удаляются точки с неопределенными значениями
5. **Сохранение в кэш:** Результат сохраняется для повторного использования

---

### Этап 1: Выбор Skin-фактора (Beam Search)

#### [`select_skin(beam=3)`](solver/solver.py:153)

```python
def select_skin(self, beam=3) -> Tuple[List[float], Dict[float, float]]:
    """
    Выбор лучших Skin-факторов методом Beam Search.
    
    Args:
        beam: Количество лучших кандидатов для отбора
        
    Returns:
        Tuple: (список top-k Skin значений, словарь {skin: ошибка})
    """
```

**Алгоритм:**

```
┌─────────────────────────────────────────────┐
│         Для каждого Skin в библиотеке:      │
│  ┌────────────────────────────────────────┐ │
│  │  Для каждой sample с этим Skin:       │ │
│  │    → ensemble_misfit(эталонная кривая)│ │
│  │    → Запомнить лучшую ошибку           │ │
│  └────────────────────────────────────────┘ │
│  → score[Skin] = min(все ошибки sample)     │
└─────────────────────────────────────────────┘
         ↓
Выбрать top-k лучших Skin (beam=3 по умолчанию)
```

---

### Этап 2: Выбор N (количество трещин)

#### [`select_N(skins)`](solver/solver.py:178)

```python
def select_N(self, skins: List[float]) -> Tuple[Tuple[float, int], Dict[Tuple[float, int], float]]:
    """
    Выбор оптимального N для выбранных Skin-кандидатов.
    
    Args:
        skins: Список Skin-кандидатов из этапа 1
        
    Returns:
        Tuple: ((best_skin, best_N), словарь ошибок)
    """
```

**Алгоритм:**

```
┌─────────────────────────────────────────────────────┐
│  Для каждого Skin из списка кандидатов:            │
│   ┌───────────────────────────────────────────────┐ │
│   │  Для каждой sample с этим Skin:              │ │
│   │    → Получить значение N                      │ │
│   │    → ensemble_misfit()                       │ │
│   │    → score[(skin, N)] = ошибка               │ │
│   └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
        ↓
Выбрать комбинацию (Skin, N) с минимальной ошибкой
```

---

### Этап 3: Байесовская оптимизация непрерывных параметров

#### [`optimize_continuous(sample, k_bounds, xf_bounds)`](solver/solver.py:203)

```python
def optimize_continuous(
    self, 
    sample: Dict, 
    k_bounds: Tuple[float, float] = (1e-5, 10), 
    xf_bounds: Tuple[float, float] = (1e-3, 100)
) -> Tuple[Dict[str, float], float]:
    """
    Байесовская оптимизация непрерывных параметров k и xf.
    
    Args:
        sample: Выбранная эталонная кривая из библиотеки
        k_bounds: Границы проницаемости (мин, макс) в мД
        xf_bounds: Границы полудлины трещины (мин, макс) в м
        
    Returns:
        Tuple: (params {'k': k_opt, 'xf': xf_opt}, best_score)
    """
```

**Целевая функция оптимизации:**

```python
def objective(params):
    k, xf = params

    # Модификация эталонной кривой:
    # 1. Масштабирование по Y с помощью k (проницаемость влияет на амплитуду)
    # 2. Нелинейное преобразование от xf (полудлина влияет на форму)
    y_mod = y_ref_norm * k * (1 + 0.1 * np.log10(xf + 1))

    # Вычисление невязки между входной и модифицированной эталонной кривой
    error = self.ensemble_misfit(x_ref_norm, y_mod)
    
    return error
```

**Используемый инструмент:** [Optuna](https://optuna.org/) с TPE (Tree-structured Parzen Estimator) семплером.

**Логарифмическая шкала:** Параметры оптимизируются в логарифмической шкале для охвата широкого диапазона значений.

---

## Функция невязки (Misfit)

### [`solver/misfit.py`](solver/misfit.py)

#### [`misfit(x1, y1, x2, y2, derivative_mode, metric_type, n_points)`](solver/misfit.py:10)

```python
def misfit(
    x1: np.ndarray, 
    y1: np.ndarray, 
    x2: np.ndarray, 
    y2: np.ndarray, 
    derivative_mode: str, 
    metric_type: str, 
    n_points: int
) -> float:
    """
    Вычисление невязки между двумя кривыми.
    
    Args:
        x1, y1: Координаты первой кривой
        x2, y2: Координаты второй кривой
        derivative_mode: 'linear' или 'loglog'
        metric_type: 'L2', 'L1' или 'integral'
        n_points: Количество точек на интерполяционной сетке
        
    Returns:
        Значение метрики невязки (float)
    """
```

#### [`ensemble_misfit(x_ref, y_ref)`](solver/solver.py:97) — основная функция

```python
def ensemble_misfit(self, x_ref: np.ndarray, y_ref: np.ndarray) -> float:
    """
    Расчет ансамблевой невязки.
    
    Вычисляет медиану ошибок по всем комбинациям:
    - 2 режима производной (linear, loglog)
    - 3 типа метрик (L2, L1, integral)
    
    Args:
        x_ref, y_ref: Координаты эталонной кривой
        
    Returns:
        Медианное значение ошибки
    """
```

**Критически важно: Нормализация**

Обе кривые (входная и эталонная) приводятся к диапазону [0, 1]:

```python
# В ensemble_misfit()
x_interp_norm = (x - min(x)) / (max(x) - min(x))
y_interp_norm = (y - min(y)) / (max(y) - min(y))

x_ref_norm = (x_ref - min(x_ref)) / (max(x_ref) - min(x_ref))
y_ref_norm = (y_ref - min(y_ref)) / (max(y_ref) - min(y_ref))
```

Это решает проблему несоответствия масштабов между фактическими и эталонными данными.

---

## Метрики сравнения кривых

### [`solver/metrics.py`](solver/metrics.py)

#### [`compute_metric(a1, a2, metric_type)`](solver/metrics.py:5)

```python
def compute_metric(a1: np.ndarray, a2: np.ndarray, metric_type: str) -> float:
    """
    Вычисление метрики различия между двумя массивами.
    
    Args:
        a1, a2: Массивы для сравнения
        metric_type: 'L2', 'L1' или 'integral'
        
    Returns:
        Значение метрики
    """
```

**L2 норма (евклидово расстояние):**
```python
return np.sum((a1 - a2) ** 2)
```
Наиболее чувствительна к большим отклонениям (квадратично).

**L1 норма (манхэттенское расстояние):**
```python
return np.sum(np.abs(a1 - a2))
```
Менее чувствительна к выбросам, более робастная.

**Интегральная метрика:**
```python
return np.abs(trapezoid(a1) - trapezoid(a2))
```
Сравнивает площадь под кривой.

---

## Производные и их вычисление

### [`solver/derivative.py`](solver/derivative.py)

#### [`compute_derivative(X, Y, mode="linear")`](solver/derivative.py:4)

```python
def compute_derivative(X: np.ndarray, Y: np.ndarray, mode: str = "linear") -> Tuple[np.ndarray, np.ndarray]:
    """
    Вычисление производной dy/dx.
    
    Args:
        X, Y: Координаты кривой
        mode: 'linear' - линейный масштаб
              'loglog' - двойной логарифмический масштаб
              
    Returns:
        X_filtered, alpha: Отфильтрованные X и производная
    """
```

**Линейный режим:**
```python
alpha = np.gradient(Y, X)  # dY/dX
```

**Логарифмический режим (для диагностики режимов течения):**
```python
X_log = np.log(X)
Y_log = np.log(Y)
alpha = np.gradient(Y_log, X_log)  # d(log Y)/d(log X)
```

**Физический смысл в log-log:** Производная характеризует режим фильтрации:
- **-1** — билинейный поток
- **0.5** — линейный поток  
- **1** — псевдорадиальный поток

---

## Интерполяция кривых

### [`solver/interpolation.py`](solver/interpolation.py)

#### [`interpolate_input_curve(x_fact, y_fact, x_ref)`](solver/interpolation.py:5)

```python
def interpolate_input_curve(
    x_fact: np.ndarray, 
    y_fact: np.ndarray, 
    x_ref: np.ndarray
) -> np.ndarray:
    """
    Интерполяция пользовательской кривой на сетку эталонной кривой.
    
    Args:
        x_fact, y_fact: Входная кривая
        x_ref: Целевая сетка X
        
    Returns:
        Интерполированные значения Y
    """
```

**Особенности:**
- Сортировка входных данных по X
- Линейная интерполяция (`scipy.interpolate.interp1d`)
- Заполнение NaN за границами
- Валидация минимум 10 точек пересечения

---

## Библиотека эталонных кривых

### [`solver/library.py`](solver/library.py)

#### [`build_skin_library(df)`](solver/library.py:1)

```python
def build_skin_library(df: pd.DataFrame) -> Dict:
    """
    Построение библиотеки эталонных кривых из DataFrame.
    
    Args:
        df: DataFrame с колонками Skin, h, N, W, L, a/L, X, Y
        
    Returns:
        Словарь: {skin_value: [samples]}
    """
```

**Структура sample:**
```python
{
    'dynamic': DataFrame(columns=['X', 'Y']),
    'h': float,      # эффективная толщина пласта
    'N': float,      # количество трещин
    'W': float,      # ширина трещины
    'L': float,      # полудлина трещины
    'a/L': float,    # отношение расстояния до границы к длине
}
```

### [`core/reference_repo.py`](core/reference_repo.py) — класс `ReferenceRepository`

```python
class ReferenceRepository:
    """
    Репозиторий для доступа к эталонным кривым из SQLite базы данных.
    """
    
    def get_skin_library(self) -> Dict:
        """Построение библиотеки, сгруппированной по Skin"""
        
    def get_available_skins(self) -> List[float]:
        """Список доступных значений Skin"""
        
    def get_reference_curve(self, curve_id: int) -> Tuple[np.ndarray, np.ndarray]:
        """Получить конкретную кривую по ID"""
```

---

## Взаимодействие с UI и core модулями

### [`core/solver.py`](core/solver.py) — класс `Solver`

Класс `Solver` является фасадом для UI и предоставляет упрощённый интерфейс.

#### [`solve_from_dimensionless(x_fact, y_fact, k_bounds, L_bounds, beam_width)`](core/solver.py:105)

```python
def solve_from_dimensionless(
    self,
    x_fact: np.ndarray,      # Безразмерный X из данных
    y_fact: np.ndarray,      # Безразмерный Y из данных
    k_bounds: Tuple[float, float] = (1e-5, 10),
    L_bounds: Tuple[float, float] = (1e-3, 100),
    beam_width: int = 3
) -> SolverResult:
    """
    Главный метод запуска оптимизации.
    
    Returns:
        SolverResult с оптимизированными параметрами
    """
```

#### [`SolverResult`](core/solver.py:19)

```python
@dataclass
class SolverResult:
    S_opt: float           # Оптимальный Skin-фактор
    k_opt: float           # Оптимальная проницаемость, мД
    L_opt: float           # Оптимальная полудлина трещины, м
    N_opt: float           # Оптимальное количество трещин
    error_value: float     # Значение функции невязки
    W_scale_factor: float = 1.0
```

---

## Конфигурация

### [`solver/config.py`](solver/config.py)

```python
DEFAULT_DERIVATIVE_MODES = ["linear", "loglog"]  # Режимы производной
DEFAULT_METRIC_TYPES = ["L2", "L1", "integral"]   # Метрики невязки
DEFAULT_N_POINTS = 200                            # Точек на сетке
SKIN_BEAM_WIDTH = 3                               # Beam width для Skin
N_BEAM_WIDTH = 3                                 # Beam width для N
BAYES_ITER = 40                                   # Итераций байесовской оптимизации
```

---

## Поток данных в приложении

```
┌──────────────────┐
│  User Input      │
│  (CSV/LAS/etc)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────────┐
│ RawDynamicData  │────▶│ ProcessingPipeline  │
└────────┬─────────┘     └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ DimensionlessData   │
                         │ (X, Y)              │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Solver.solve()      │
                         │                     │
                         │ 1. Prepare curve    │
                         │ 2. Select Skin      │
                         │ 3. Select N         │
                         │ 4. Optimize k, L    │ ← Модификация эталонной кривой
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ SolverResult        │
                         │ S, k, L, N, error   │
                         └─────────────────────┘
```

---

## Пример использования

```python
from core.solver import Solver
import numpy as np

# Создание экземпляра solver
solver = Solver(db_path="storage/db/reference_curves.db")

# Данные (предполагаются предварительно рассчитанные X, Y)
x_fact = np.array([...])  # Безразмерный параметр X
y_fact = np.array([...])  # Безразмерный параметр Y

# Запуск оптимизации
result = solver.solve_from_dimensionless(
    x_fact=x_fact,
    y_fact=y_fact,
    k_bounds=(1e-5, 10),      # границы проницаемости
    L_bounds=(1e-3, 100),    # границы полудлины
    beam_width=3
)

# Результат
print(f"Skin = {result.S_opt:.4f}")
print(f"k = {result.k_opt:.6f} мД")
print(f"L = {result.L_opt:.4f} м")
print(f"N = {result.N_opt:.0f}")
print(f"Error = {result.error_value:.6f}")
```

---

## Ограничения и рекомендации

### Текущие ограничения

1. **Логарифмическая сетка:** Предполагается достаточный диапазон данных
2. **Дискретные параметры:** Skin и N выбираются только из доступных в библиотеке значений
3. **Модификация кривой:** Упрощённая формула `y_mod = y_ref_norm * k * (1 + 0.1 * np.log10(xf + 1))`

### Рекомендации по улучшению

1. **Интерполяция библиотеки:** Добавить интерполяцию между соседними Skin-значениями
2. **Физически обоснованная модификация:** Использовать реальные формулы влияния k и xf на кривые
3. **Ансамбль моделей:** Рассматривать несколько конкурирующих гипотез
4. **Неопределенность:** Добавить оценку доверительных интервалов

---

## Ссылки

- [Optuna Documentation](https://optuna.org/)
- [NumPy Documentation](https://numpy.org/doc/)
- [SciPy Interpolation](https://docs.scipy.org/doc/scipy/reference/interpolate.html)
- [МГРП теория](docs/Объяснение решения обратной задачи МГРП.docx)
