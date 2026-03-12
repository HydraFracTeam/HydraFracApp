import numpy as np
from scipy.interpolate import interp1d


def build_common_grid(x1, x2, n_points=200, log_grid=True):
    """
    Строит общую сетку X на пересечении диапазонов двух кривых.
    """

    xmin = max(np.min(x1), np.min(x2))
    xmax = min(np.max(x1), np.max(x2))

    if xmax <= xmin:
        return None

    if log_grid:

        if xmin <= 0:
            xmin = np.min([v for v in [np.min(x1), np.min(x2)] if v > 0])

        grid = np.exp(
            np.linspace(np.log(xmin), np.log(xmax), n_points)
        )

    else:

        grid = np.linspace(xmin, xmax, n_points)

    return grid


def interpolate_to_grid(x, y, grid):
    """
    Интерполяция кривой на заданную сетку.
    """

    f = interp1d(
        x,
        y,
        bounds_error=False,
        fill_value=np.nan
    )

    y_interp = f(grid)

    mask = ~np.isnan(y_interp)

    return grid[mask], y_interp[mask]


def align_curves(x1, y1, x2, y2, n_points=200, log_grid=True):
    """
    Приводит две кривые к общей сетке X.
    """

    grid = build_common_grid(x1, x2, n_points, log_grid)

    if grid is None:
        return None

    x1g, y1g = interpolate_to_grid(x1, y1, grid)
    x2g, y2g = interpolate_to_grid(x2, y2, grid)

    mask = (
        ~np.isnan(y1g)
        & ~np.isnan(y2g)
        & (y1g > 0)
        & (y2g > 0)
    )

    if np.sum(mask) < 10:
        return None

    return (
        grid[mask],
        y1g[mask],
        y2g[mask]
    )