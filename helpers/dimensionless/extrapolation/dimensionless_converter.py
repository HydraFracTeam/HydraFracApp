"""
Модуль нормированного вычисления безразмерных параметров X, Y.
Безопасные формулы с защитой от деления на ноль и обработкой выбросов.
"""

import numpy as np
from typing import Tuple, Optional


def compute_dimensionless_xy(
    t: np.ndarray,
    P: np.ndarray,
    dP: np.ndarray,
    Q: np.ndarray,
    well_params: dict,
    dP_threshold: float = 1e-6
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Вычисляет безразмерные параметры X, Y с безопасными формулами.
    
    Args:
        t: Время, ч
        P: Давление, атм
        dP: Приращение давления, атм
        Q: Дебит, м³/сут
        well_params: Параметры скважины {k, h, mu, B, phi, ct, L}
        dP_threshold: Порог для валидности dP
    
    Returns:
        (X, Y, valid_mask): Безразмерные параметры и маска валидности
    """
    # Извлекаем параметры
    k = well_params.get('k', 1.0)
    h = well_params.get('h', 10.0)
    mu = well_params.get('mu', 1.0)
    B = well_params.get('B', 1.0)
    phi = well_params.get('phi', 0.1)
    c_t = well_params.get('ct', 1e-4)
    L = well_params.get('L', 100.0)
    
    # Защита от деления на ноль и отрицательных значений
    dP_safe = np.where(np.abs(dP) < dP_threshold, dP_threshold, dP)
    dP_safe = np.where(dP_safe < 0, dP_threshold, dP_safe)  # Защита знака dP
    
    Q_safe = np.where(np.abs(Q) < 1e-12, 1e-12, Q)
    Q_safe = np.where(Q_safe < 0, 1e-12, Q_safe)  # Защита знака Q
    
    # Маска валидности (dP > threshold)
    valid_mask = np.abs(dP) >= dP_threshold
    
    # Фильтрация выбросов в логарифмическом пространстве
    # Вычисляем log(dP) и log(Q) для обнаружения выбросов
    log_dP = np.log10(np.maximum(dP_safe, 1e-10))
    log_Q = np.log10(np.maximum(Q_safe, 1e-10))
    
    # Простая фильтрация выбросов через IQR
    def filter_outliers_log(values: np.ndarray, factor: float = 1.5) -> np.ndarray:
        """Фильтрует выбросы в логарифмическом пространстве"""
        q1 = np.nanpercentile(values, 25)
        q3 = np.nanpercentile(values, 75)
        iqr = q3 - q1
        lower_bound = q1 - factor * iqr
        upper_bound = q3 + factor * iqr
        return (values >= lower_bound) & (values <= upper_bound)
    
    dP_outlier_mask = filter_outliers_log(log_dP)
    Q_outlier_mask = filter_outliers_log(log_Q)
    outlier_mask = dP_outlier_mask & Q_outlier_mask
    
    # Объединяем маски валидности
    valid_mask = valid_mask & outlier_mask
    
    # Фильтрационный параметр X
    # X = (0.00864 * k * h * dP) / (mu * B * Q)
    X = (0.00864 * k * h * dP_safe) / (mu * B * Q_safe)
    
    # Ёмкостной параметр Y
    # Y = (Q * B * t) / (24 * phi * c_t * h * L² * dP)
    Y = (Q_safe * B * t) / (24 * phi * c_t * h * L**2 * dP_safe)
    
    # Применяем маску валидности (устанавливаем NaN для невалидных точек)
    X = np.where(valid_mask, X, np.nan)
    Y = np.where(valid_mask, Y, np.nan)
    
    return X, Y, valid_mask

