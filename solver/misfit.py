# solver/misfit.py
import numpy as np
from scipy.interpolate import interp1d
from .derivative import compute_derivative
from .metrics import compute_metric


def misfit_shape(x1, y1, x2, y2,
                 derivative_mode="loglog",
                 metric_type="integral",
                 X=None):
    """Вычисляет невязку по форме для двух кривых.

    Проводится в режиме производной (обычная или log-log), затем сравнение
    производных по выбранной метрике.
    """
    x1 = np.asarray(x1, dtype=float)
    y1 = np.asarray(y1, dtype=float)
    x2 = np.asarray(x2, dtype=float)
    y2 = np.asarray(y2, dtype=float)

    if x1.size == 0 or x2.size == 0:
        return float('inf')

    mask1 = (x1 > 0) & (y1 > 0)
    mask2 = (x2 > 0) & (y2 > 0)
    x1p, y1p = x1[mask1], y1[mask1]
    x2p, y2p = x2[mask2], y2[mask2]

    if x1p.size < 2 or x2p.size < 2:
        return float('inf')

    x1d, alpha1 = compute_derivative(x1p, y1p, mode=derivative_mode)
    x2d, alpha2 = compute_derivative(x2p, y2p, mode=derivative_mode)

    if alpha1.size == 0 or alpha2.size == 0:
        return float('inf')

    xmin = max(np.min(x1d), np.min(x2d))
    xmax = min(np.max(x1d), np.max(x2d))
    if xmin >= xmax or not np.isfinite(xmin) or not np.isfinite(xmax):
        return float('inf')

    if X is None:
        n = max(min(alpha1.size, alpha2.size, 300), 2)
        if derivative_mode == "loglog":
            X = np.logspace(np.log10(xmin), np.log10(xmax), n)
        else:
            X = np.linspace(xmin, xmax, n)
    else:
        X = np.asarray(X, dtype=float)

    alpha1_i = interp1d(x1d, alpha1, bounds_error=False, fill_value=np.nan)(X)
    alpha2_i = interp1d(x2d, alpha2, bounds_error=False, fill_value=np.nan)(X)
    mask = np.isfinite(alpha1_i) & np.isfinite(alpha2_i)
    if np.count_nonzero(mask) < 2:
        return float('inf')

    return compute_metric(alpha1_i[mask], alpha2_i[mask], metric_type=metric_type, X=X[mask])


def sample_misfit(sample, x_fact, y_fact):
    """
    Вычисляет невязку между образцом из библиотеки и фактической кривой.
    sample: словарь с ключом 'dynamic', содержащим 'X' и 'Y' (как массивы или pandas Series)
    x_fact, y_fact: массивы фактических данных
    Возвращает скалярное значение невязки.
    """
    # Извлекаем референсные данные из образца
    sample_dynamic = sample['dynamic']
    # Преобразуем в numpy arrays, если нужно
    if hasattr(sample_dynamic['X'], 'values'):
        sample_x = sample_dynamic['X'].values
        sample_y = sample_dynamic['Y'].values
    else:
        sample_x = np.asarray(sample_dynamic['X'])
        sample_y = np.asarray(sample_dynamic['Y'])
    
    # Вычисляем логарифмические производные для обеих кривых
    _, alpha_sample = compute_derivative(sample_x, sample_y, mode="loglog")
    _, alpha_fact = compute_derivative(x_fact, y_fact, mode="loglog")
    
    # Выравниваем по длине: берем общую часть
    min_len = min(len(alpha_sample), len(alpha_fact))
    if min_len == 0:
        return float('inf')
    alpha_sample = alpha_sample[:min_len]
    alpha_fact = alpha_fact[:min_len]
    
    # Вычисляем интегральную невязку
    misfit = compute_metric(alpha_sample, alpha_fact, metric_type="integral")
    return misfit