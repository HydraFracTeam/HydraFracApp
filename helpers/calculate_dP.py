import numpy as np

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
