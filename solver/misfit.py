import numpy as np
from scipy.interpolate import interp1d
from .derivative import compute_derivative
from .metrics import compute_metric
import logging

logger = logging.getLogger(__name__)


def misfit(x1, y1, x2, y2, derivative_mode, metric_type, n_points):
    """
    Вычисление невязки между двумя кривыми.
    
    Args:
        x1 (np.ndarray): X координаты первой кривой
        y1 (np.ndarray): Y координаты первой кривой
        x2 (np.ndarray): X координаты второй кривой
        y2 (np.ndarray): Y координаты второй кривой
        derivative_mode (str): 'linear' или 'loglog'
        metric_type (str): 'L2', 'L1' или 'integral'
        n_points (int): Количество точек на интерполяционной сетке
        
    Returns:
        float: Значение метрики невязки
    """

    xmin = max(np.min(x1), np.min(x2))
    xmax = min(np.max(x1), np.max(x2))

    if xmax <= xmin:
        logger.debug(f"    [misfit] Диапазоны не пересекаются: x1=[{np.min(x1):.4f}, {np.max(x1):.4f}], x2=[{np.min(x2):.4f}, {np.max(x2):.4f}]")
        return np.inf

    x_grid = np.linspace(xmin, xmax, n_points)

    f1 = interp1d(x1, y1, bounds_error=False, fill_value=np.nan)
    f2 = interp1d(x2, y2, bounds_error=False, fill_value=np.nan)

    y1i = f1(x_grid)
    y2i = f2(x_grid)

    # Применяем одинаковую маску к обеим кривым для вычисления производных
    mask = (~np.isnan(y1i)) & (~np.isnan(y2i))

    if np.sum(mask) < 30:
        logger.debug(f"    [misfit] Слишком мало точек после интерполяции: {np.sum(mask)} (нужно ≥30)")
        return np.inf

    xg = x_grid[mask]
    y1g = y1i[mask]
    y2g = y2i[mask]

    # Дополнительно фильтруем для производной - одинаковая маска для обоих
    # Используем xg > 0 и y > 0
    deriv_mask = (xg > 0) & (y1g > 0) & (y2g > 0)
    
    if np.sum(deriv_mask) < 10:
        logger.debug(f"    [misfit] Слишком мало точек для производной: {np.sum(deriv_mask)}")
        return np.inf
        
    xg = xg[deriv_mask]
    y1g = y1g[deriv_mask]
    y2g = y2g[deriv_mask]

    X1, alpha1 = compute_derivative(xg, y1g, derivative_mode)
    X2, alpha2 = compute_derivative(xg, y2g, derivative_mode)

    return compute_metric(alpha1, alpha2, metric_type)