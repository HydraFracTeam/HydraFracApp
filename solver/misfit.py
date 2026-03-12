import numpy as np
from scipy.interpolate import interp1d
from .derivative import compute_derivative
from .metrics import compute_metric
import logging

logger = logging.getLogger(__name__)


def misfit(x1, y1, x2, y2, derivative_mode, metric_type, n_points):

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

    mask = (~np.isnan(y1i)) & (~np.isnan(y2i))

    if np.sum(mask) < 30:
        logger.debug(f"    [misfit] Слишком мало точек после интерполяции: {np.sum(mask)} (нужно ≥30)")
        return np.inf

    xg = x_grid[mask]
    y1g = y1i[mask]
    y2g = y2i[mask]

    X1, alpha1 = compute_derivative(xg, y1g, derivative_mode)
    X2, alpha2 = compute_derivative(xg, y2g, derivative_mode)

    return compute_metric(alpha1, alpha2, metric_type)