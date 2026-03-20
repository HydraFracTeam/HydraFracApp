import numpy as np
from scipy.interpolate import interp1d


def interpolate_input_curve(x_fact, y_fact, x_ref):
    """
    Интерполяция пользовательской кривой на сетку эталонной кривой.
    
    Args:
        x_fact (np.ndarray): X координаты входной кривой
        y_fact (np.ndarray): Y координаты входной кривой
        x_ref (np.ndarray): Целевая сетка X
        
    Returns:
        np.ndarray: Интерполированные значения Y
        
    Raises:
        ValueError: Если входная кривая почти не пересекается с сеткой
    """
    """
    Интерполирует пользовательскую кривую на сетку библиотеки.

    Parameters
    ----------
    x_fact : np.ndarray
        X координаты входной кривой

    y_fact : np.ndarray
        Y координаты входной кривой

    x_ref : np.ndarray
        сетка X библиотеки

    Returns
    -------
    y_interp : np.ndarray
        входная кривая на сетке библиотеки
    """

    x_fact = np.asarray(x_fact)
    y_fact = np.asarray(y_fact)

    # сортировка на случай если вход не отсортирован
    order = np.argsort(x_fact)

    x_fact = x_fact[order]
    y_fact = y_fact[order]

    # строим интерполятор
    f = interp1d(
        x_fact,
        y_fact,
        bounds_error=False,
        fill_value=np.nan
    )

    y_interp = f(x_ref)

    # проверяем что есть пересечение диапазонов
    valid_mask = ~np.isnan(y_interp)

    if np.sum(valid_mask) < 10:
        raise ValueError(
            "Входная кривая почти не пересекается с сеткой библиотеки"
        )

    return y_interp


def interpolate_to_grid(x, y, grid):
    """
    Интерполяция кривой на заданную сетку.
    
    Args:
        x: X координаты кривой
        y: Y координаты кривой  
        grid: Целевая сетка
    
    Returns:
        (grid, y_interp): Отфильтрованная сетка и интерполированные значения
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