import numpy as np

def normalize_Q_by_n(Q_total: np.ndarray, N: float) -> np.ndarray:
    "Нормировка общего дебита Q на кол-во трещин N"
    return Q_total / N


def calculate_dP(P: np.ndarray, P0: float) -> np.ndarray:
    """
    Вычисляет разность давлений: P0 - P
    """
    # Создаем массив результата
    dP = np.full_like(P, np.nan, dtype=float)
    
    # Создаем маску для не-NaN значений
    not_nan_mask = ~np.isnan(P)
    
    # Вычисляем dP только для валидных значений
    dP[not_nan_mask] = np.abs(P0 - P[not_nan_mask])
    
    return dP
