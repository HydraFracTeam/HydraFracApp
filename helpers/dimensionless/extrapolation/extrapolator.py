"""
Модуль экстраполяции размерных параметров (P, dP, Q).
"""

import numpy as np
from typing import Tuple
from sklearn.base import BaseEstimator


def extrapolate_parameters(
    model_P: BaseEstimator,
    model_Q: BaseEstimator,
    P_start: float,
    t_future: np.ndarray,
    static_features: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Экстраполирует P, Q, dP на n шагов вперёд по времени.
    
    Args:
        model_P, model_Q, model_dP: Обученные модели для каждой величины
        t_future: временные точки для экстраполяции
        static_features: Статические параметры [Skin, h, ...]
    
    Returns:
        P_ext, Q_ext, dP_ext
    """
    
    # Добавляем статические признаки к каждому моменту времени
    X_future = np.hstack([
        np.tile(static_features, (len(t_future), 1)),
        t_future.reshape(-1, 1)
    ])
    
    P_ext = model_P.predict(X_future)
    Q_ext = model_Q.predict(X_future)
    # dP_ext = model_dP.predict(X_future)
    print(f"P_ext origin: {P_ext}")
    P_ext = np.clip(P_ext, a_min=0.0, a_max=None)
    
    dP_ext = P_start - P_ext
    
    import pandas as pd
    print(pd.DataFrame([P_ext, dP_ext, Q_ext]))
    
    return P_ext, dP_ext, Q_ext
