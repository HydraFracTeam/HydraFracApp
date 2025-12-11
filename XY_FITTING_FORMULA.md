# Подгонка X-Y: формулы

**Функция:** `fit_xy_curve_coefficients()` в `helpers/dimensionless_analysis.py`

## Формулы подгонки

### X (координата)

$$X_{\text{fitted}} = a \cdot X_{\text{calc}}$$

где коэффициент $a$ находится методом МНК:

$$a = \frac{X_{\text{data}}^T \cdot X_{\text{calc}}}{X_{\text{calc}}^T \cdot X_{\text{calc}}}$$

Если `fit_only_y = True`, то $a = 1$ (X без изменений).

### Y (координата)

Квадратичная регрессия:

$$Y_{\text{fitted}} = a_y \cdot Y_{\text{calc}} + b + c \cdot Y_{\text{calc}}^2$$

**Вычисление коэффициентов:**

1. Нормализация: $Y_{\text{norm}} = Y_{\text{calc}} / \text{median}(Y_{\text{calc}})$
2. МНК: решаем систему $A \cdot \theta = Y_{\text{data}}$, где
   - $A = [Y_{\text{norm}}, \mathbf{1}, Y_{\text{norm}}^2]$ (матрица $n \times 3$)
   - $\theta = [a_n, b, c_n]$ (коэффициенты)
3. Обратное преобразование:
   - $a_y = a_n / \text{median}(Y_{\text{calc}})$
   - $c = c_n / \text{median}(Y_{\text{calc}})^2$

## Ограничения

- Квадратичный коэффициент: $-0.2 \leq c \leq 0.2$
- Fallback: если RMSE ухудшился, используется линейная подгонка ($c = 0$)

## Метрики

- `rmse_before` / `rmse` — ошибка до/после подгонки
- `accuracy` — точность: $(1 - \text{rmse}/y_{\text{range}}) \cdot 100\%$
- `r2` — коэффициент детерминации
- `c_clipped`, `fallback_used` — флаги ограничений

## Особенности

- Интерполяция Y на сетку X для выравнивания массивов
- Нормализация на медиану для числовой устойчивости
- Фильтрация NaN/Inf перед подгонкой
