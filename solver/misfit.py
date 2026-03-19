import numpy as np
from scipy.interpolate import interp1d
from .derivative import compute_derivative
from .metrics import compute_metric
import logging

logger = logging.getLogger(__name__)


def find_best_scale(x_ref, x_fact):
    """
    Находит коэффициент масштабирования для приведения диапазона референсной кривой к фактической.
    
    Использует отношение медиан для устойчивости к выбросам.
    
    Args:
        x_ref (np.ndarray): X координаты референсной кривой
        x_fact (np.ndarray): X координаты фактической кривой
        
    Returns:
        float: Коэффициент масштабирования
    """
    if np.median(x_ref) == 0:
        return 1.0
    return np.median(x_fact) / np.median(x_ref)


def get_scale_factors(x_ref, y_ref, x_fact, y_fact):
    """
    Возвращает коэффициенты масштабирования для X и Y.
    
    Args:
        x_ref, y_ref: Координаты референсной кривой
        x_fact, y_fact: Координаты фактической кривой
        
    Returns:
        Tuple[float, float]: (scale_x, scale_y)
    """
    scale_x = find_best_scale(x_ref, x_fact)
    scale_y = find_best_scale(y_ref, y_fact)
    return scale_x, scale_y


def scale_to_match(x_ref, y_ref, x_fact, y_fact):
    """
    Масштабирует референсную кривую (X, Y) к диапазону фактической кривой
    с помощью аффинного преобразования.
    
    Args:
        x_ref, y_ref: Координаты референсной кривой
        x_fact, y_fact: Координаты фактической кривой
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: Масштабированные x_ref, y_ref
    """
    # Масштабирование по X
    scale_x = find_best_scale(x_ref, x_fact)
    x_ref_scaled = x_ref * scale_x
    
    # Масштабирование по Y  
    scale_y = find_best_scale(y_ref, y_fact)
    y_ref_scaled = y_ref * scale_y
    
    return x_ref_scaled, y_ref_scaled


def misfit(x1, y1, x2, y2, derivative_mode, metric_type, n_points, scale_ref=True):
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
        scale_ref (bool): Масштабировать ли референсную кривую к диапазону первой кривой
        
    Returns:
        float: Значение метрики невязки
    """

    # Масштабируем референсную кривую (x2, y2) к диапазону первой кривой (x1, y1)
    if scale_ref:
        x2, y2 = scale_to_match(x2, y2, x1, y1)

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