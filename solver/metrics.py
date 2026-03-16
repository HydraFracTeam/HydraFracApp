import numpy as np
from scipy.integrate import trapezoid


def compute_metric(a1, a2, metric_type):
    """
    Вычисление метрики различия между двумя массивами.
    
    Args:
        a1 (np.ndarray): Первый массив
        a2 (np.ndarray): Второй массив
        metric_type (str): 'L2', 'L1' или 'integral'
        
    Returns:
        float: Значение метрики
        
    Raises:
        ValueError: Если неизвестный тип метрики
    """

    if metric_type == "L2":
        return np.sum((a1 - a2) ** 2)

    elif metric_type == "L1":
        return np.sum(np.abs(a1 - a2))

    elif metric_type == "integral":
        return np.abs(trapezoid(a1) - trapezoid(a2))

    else:
        raise ValueError("Unknown metric")