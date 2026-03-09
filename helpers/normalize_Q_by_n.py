import numpy as np

def normalize_Q_by_n(Q_total: np.ndarray, N: float) -> np.ndarray:
    "Нормировка общего дебита Q на кол-во трещин N"
    return Q_total / N
