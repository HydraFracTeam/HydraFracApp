import numpy as np
from scipy.interpolate import interp1d
from .derivative import compute_derivative
from .metrics import compute_metric
import logging

logger = logging.getLogger(__name__)


def misfit_shape(x1, y1, x2, y2,
                 derivative_mode="linear",
                 metric_type="integral",
                 n_points=200):
    """
    Невязка ФОРМЫ двух кривых через производную dY/dX.

    Используется для сравнения кривых когда масштаб Y неизвестен
    (выбор Skin, N, a/L, L). k ещё не подобран на этом этапе.

    Почему mode="linear", а не "loglog":
      X и Y — уже безразмерные параметры. loglog-производная
      d(logY)/d(logX) уместна для P(t) в абсолютных единицах
      (убирает масштаб размерности). Для безразмерных X-Y это
      двойная трансформация без выигрыша, которая дополнительно
      сжимает пологие участки и растягивает крутые, теряя
      информацию о переходных режимах.

    Нормировка по медиане:
      Убирает влияние вертикального масштаба (k) при сравнении форм.
      Медиана робастна к единичным выбросам на краях кривой
      (в отличие от max, который нестабилен на реальных данных).

    Args:
        x1, y1  : фактическая кривая (или кэшированная сетка)
        x2, y2  : референсная кривая
        derivative_mode : "linear" (рекомендуется) или "loglog"
        metric_type     : "integral", "L2", "L1"
        n_points        : точек на общей лог-сетке

    Returns:
        float: значение невязки (меньше = лучше совпадение формы)
    """
    # Пересечение диапазонов X
    xmin = max(np.min(x1), np.min(x2))
    xmax = min(np.max(x1), np.max(x2))

    if xmin <= 0 or xmax <= xmin:
        return np.inf

    # Логарифмическая сетка — равномерное покрытие всех декад
    x_grid = np.logspace(np.log10(xmin), np.log10(xmax), n_points)

    f1 = interp1d(x1, y1, bounds_error=False, fill_value=np.nan)
    f2 = interp1d(x2, y2, bounds_error=False, fill_value=np.nan)

    y1i = f1(x_grid)
    y2i = f2(x_grid)

    mask = (~np.isnan(y1i)) & (~np.isnan(y2i)) & (y1i > 0) & (y2i > 0)

    if mask.sum() < 20:
        return np.inf

    xg  = x_grid[mask]
    y1g = y1i[mask]
    y2g = y2i[mask]

    # Нормировка по медиане — убираем масштаб Y, сохраняем форму
    med1 = np.median(y1g)
    med2 = np.median(y2g)
    if med1 <= 0 or med2 <= 0:
        return np.inf
    y1g = y1g / med1
    y2g = y2g / med2

    # Производная и метрика
    X1, alpha1 = compute_derivative(xg, y1g, derivative_mode)
    _,  alpha2 = compute_derivative(xg, y2g, derivative_mode)

    return compute_metric(alpha1, alpha2, metric_type, X=X1)


def misfit(x1, y1, x2, y2, derivative_mode, metric_type, n_points, scale_ref=True):
    """
    Обёртка для совместимости - вызывает misfit_shape.
    """
    return misfit_shape(x1, y1, x2, y2,
                       derivative_mode=derivative_mode,
                       metric_type=metric_type,
                       n_points=n_points)


def misfit_aligned(x1, y1, x2, y2,
                   derivative_mode="linear",
                   metric_type="integral",
                   n_points=200):
    """
    Невязка АЛЛАЙНЕД двух кривых БЕЗ нормировки.
    
    Используется для подбора k и xf, когда форма уже согласована
    (Skin, N, a/L выбраны), и нужно сравнить абсолютные значения Y.
    
    БЕЗ нормировки — сохраняется абсолютный масштаб k:
      - Маленький k -> маленький Y -> большая невязка
      - Большой k -> большой Y -> меньшая невязка
    
    Это позволяет оптимизатору "видеть" правильный k.

    Args:
        x1, y1  : фактическая кривая
        x2, y2  : референсная кривая  
        derivative_mode : "linear" (рекомендуется) или "loglog"
        metric_type     : "integral", "L2", "L1"
        n_points        : точек на общей лог-сетке

    Returns:
        float: значение невязки (меньше = лучше совпадение)
    """
    # Пересечение диапазонов X
    xmin = max(np.min(x1), np.min(x2))
    xmax = min(np.max(x1), np.max(x2))

    if xmin <= 0 or xmax <= xmin:
        return np.inf

    # Логарифмическая сетка — равномерное покрытие всех декад
    x_grid = np.logspace(np.log10(xmin), np.log10(xmax), n_points)

    f1 = interp1d(x1, y1, bounds_error=False, fill_value=np.nan)
    f2 = interp1d(x2, y2, bounds_error=False, fill_value=np.nan)

    y1i = f1(x_grid)
    y2i = f2(x_grid)

    mask = (~np.isnan(y1i)) & (~np.isnan(y2i)) & (y1i > 0) & (y2i > 0)

    if mask.sum() < 20:
        return np.inf

    xg  = x_grid[mask]
    y1g = y1i[mask]
    y2g = y2i[mask]

    # БЕЗ нормировки! Используем сырые значения Y
    # Это позволяет оптимизатору "видеть" абсолютный масштаб k

    # Производная и метрика
    X1, alpha1 = compute_derivative(xg, y1g, derivative_mode)
    _,  alpha2 = compute_derivative(xg, y2g, derivative_mode)

    return compute_metric(alpha1, alpha2, metric_type, X=X1)
