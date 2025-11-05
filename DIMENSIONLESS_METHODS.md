# Безразмерные методы для МГРП

## Обзор

Реализован полный пайплайн для работы с безразмерными кривыми МГРП, включающий конвертацию, интерполяцию и экстраполяцию в пространстве безразмерных параметров.

## Безразмерные параметры

### Фильтрационный параметр X
```
X = (0.00864 * k * h * Δp_i) / (μ * B * Q)
```
где:
- `k` - проницаемость, мД
- `h` - толщина пласта, м
- `Δp_i` - начальное падение давления, атм
- `μ` - вязкость, мПа·с
- `B` - объемный коэффициент
- `Q` - дебит, м³/сут

### Ёмкостной параметр Y
```
Y = (Q * B * t) / (24 * φ * c_t * h * L² * Δp_i)
```
где:
- `t` - время, ч
- `φ` - пористость
- `c_t` - общая сжимаемость, 1/атм
- `L` - длина трещины, м

## Основные классы

### DimensionlessConverter
Конвертер между физическими и безразмерными параметрами.

```python
from helpers.dimensionless_analysis import convert_to_dimensionless_curves

# Конвертация в безразмерные параметры
dimensionless_data = convert_to_dimensionless_curves(
    time, pressure, flow_rate, well_params
)
```

### DimensionlessInterpolator
Интерполяция в пространстве безразмерных кривых.

```python
from helpers.dimensionless_analysis import interpolate_dimensionless_curves

# Интерполяция
interpolated_pressure, interpolated_flow = interpolate_dimensionless_curves(
    time, pressure, flow_rate, well_params, 
    target_times, target_params, method='rbf'
)
```

### PhysicsConstrainedDimensionlessInterpolator
Физически ограниченная интерполяция с учетом ограничений МГРП.

```python
# Ограничения
constraints = {
    'max_skin': 50.0,
    'min_skin': -10.0,
    'max_n_fractures': 100,
    'min_n_fractures': 1,
    'max_a_l_ratio': 1.0,
    'min_a_l_ratio': 0.01
}
```

### DimensionlessExtrapolator
Экстраполяция безразмерных кривых в будущее.

```python
from helpers.dimensionless_analysis import extrapolate_dimensionless_curves

# Экстраполяция
extrapolated_pressure, extrapolated_flow = extrapolate_dimensionless_curves(
    time, pressure, flow_rate, well_params,
    future_times, extrapolation_params, method='physics_constrained'
)
```

## Методы интерполяции

### 1. RBF (Радиальные базисные функции)
- **Применение**: Сложные нелинейные зависимости
- **Преимущества**: Гибкость, хорошая точность
- **Недостатки**: Может быть нестабильной

### 2. Linear (Линейная)
- **Применение**: Простые линейные зависимости
- **Преимущества**: Быстрота, стабильность
- **Недостатки**: Ограниченная точность

### 3. Physics Constrained (Физически ограниченная)
- **Применение**: МГРП данные с физическими ограничениями
- **Преимущества**: Соответствие физическим законам
- **Недостатки**: Может быть консервативной

## Методы экстраполяции

### 1. Physics Constrained
- Экспоненциальное затухание
- Физические ограничения
- Учет режимов течения

### 2. RBF
- Радиальные базисные функции
- Адаптивность
- Хорошая точность

## Эталонные кривые

### Создание библиотеки
```python
from helpers.dimensionless_analysis import create_dimensionless_type_curves

type_curves = create_dimensionless_type_curves(
    skin_range=(-5, 20),
    n_fractures_range=(1, 50),
    a_l_range=(0.01, 0.5),
    n_points=100
)
```

### Типы режимов течения
1. **Билинейное течение** - ранняя стадия
2. **Линейное течение** - средняя стадия
3. **Псевдорадиальное течение** - поздняя стадия

## Визуализация

### Matplotlib графики
```python
from helpers.dimensionless_plotting import plot_dimensionless_analysis

# Анализ безразмерных кривых
fig = plot_dimensionless_analysis(time, pressure, flow_rate, well_params, 'pressure')
```

### PyQtGraph графики
```python
from helpers.dimensionless_plotting import PyQtGraphDimensionlessPlotter

plotter = PyQtGraphDimensionlessPlotter()
plotter.create_dimensionless_plot(plot_widget, dimensionless_data, 'pressure')
```

## Физические ограничения

### Параметры ГРП
- **Skin**: -10 ≤ skin ≤ 50
- **N (количество трещин)**: 1 ≤ N ≤ 100
- **a/L (отношение)**: 0.01 ≤ a/L ≤ 1.0

### Динамические ограничения
- **Градиент давления**: ≤ 100 МПа/час
- **Дебит**: 0 ≤ Q ≤ 1000 м³/сут

## Примеры использования

### Базовый анализ
```python
# Параметры скважины
well_params = {
    'k': 1.0, 'h': 10.0, 'mu': 1.0, 'B': 1.0,
    'phi': 0.1, 'c_t': 1e-4, 'L': 100.0,
    'skin': 2.0, 'N': 5, 'a_L': 0.1
}

# Конвертация
dimensionless_data = convert_to_dimensionless_curves(
    time, pressure, flow_rate, well_params
)

# Визуализация
fig = plot_dimensionless_analysis(time, pressure, flow_rate, well_params)
```

### Интерполяция
```python
# Целевые временные точки
target_times = np.linspace(time.min(), time.max(), 100)

# Интерполяция
interpolated_pressure, interpolated_flow = interpolate_dimensionless_curves(
    time, pressure, flow_rate, well_params,
    target_times, well_params, 'rbf'
)
```

### Экстраполяция
```python
# Будущие временные точки
future_times = np.linspace(time.max(), time.max() * 2, 50)

# Экстраполяция
extrapolated_pressure, extrapolated_flow = extrapolate_dimensionless_curves(
    time, pressure, flow_rate, well_params,
    future_times, well_params, 'physics_constrained'
)
```

## Интеграция в интерфейс

### Новые методы в главном приложении
- `on_dimensionless_analysis()` - анализ безразмерных кривых
- `on_dimensionless_interpolation()` - интерполяция
- `on_dimensionless_extrapolation()` - экстраполяция
- `on_create_type_curves()` - создание эталонных кривых
- `on_plot_dimensionless_pyqtgraph()` - PyQtGraph визуализация

## Тестирование

### Запуск тестов
```bash
python test_dimensionless_methods.py
```

### Тестируемые функции
1. Конвертация в безразмерные параметры
2. Интерполяция различными методами
3. Экстраполяция с физическими ограничениями
4. Создание библиотеки эталонных кривых
5. Физические ограничения

## Производительность

| Метод | Скорость | Точность | Физическая адекватность |
|-------|----------|----------|------------------------|
| RBF | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Linear | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Physics Constrained | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## Рекомендации

### Для анализа МГРП:
1. **Начальный анализ**: `plot_dimensionless_analysis()`
2. **Интерполяция**: `interpolate_dimensionless_curves()` с методом 'rbf'
3. **Экстраполяция**: `extrapolate_dimensionless_curves()` с методом 'physics_constrained'
4. **Сравнение с эталонами**: `create_dimensionless_type_curves()`

### Для производственных данных:
- Используйте физически ограниченные методы
- Проверяйте соответствие физическим законам
- Сравнивайте с эталонными кривыми

## Заключение

Реализованный пайплайн обеспечивает:
- ✅ Адекватную физически интерполяцию
- ✅ Экстраполяцию безразмерных кривых
- ✅ Работу с важными параметрами МГРП (Skin, N, a/L)
- ✅ Подходящий формат графиков для безразмерных кривых
- ✅ Физические ограничения и валидацию

Система готова для анализа реальных данных МГРП и может быть легко интегрирована в существующий интерфейс.
