"""
Модуль экстраполяции размерных параметров (P, dP, Q).
Чистый интерфейс без зависимости от self.
"""

import numpy as np
from typing import Tuple, Optional
from sklearn.base import BaseEstimator


def extrapolate_parameters(
    model: BaseEstimator,
    P_current: float,
    dP_current: float,
    Q_current: float,
    static_features: np.ndarray,
    dt: float,
    n: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Экстраполирует размерные параметры P, dP, Q на n шагов вперед.
    
    Args:
        model: Обученная модель (Ridge, Poly, RF и т.д.)
        P_current: Текущее значение давления
        dP_current: Текущее значение приращения давления
        Q_current: Текущее значение дебита
        static_features: Статичные параметры скважины [Skin, h, N, W, L, a/L]
        dt: Шаг времени
        n: Количество шагов экстраполяции
    
    Returns:
        (P_ext, dP_ext, Q_ext): Экстраполированные массивы
    """
    predictions = []
    current_values = np.array([P_current, dP_current, Q_current])
    
    for _ in range(n):
        # Формируем признаковый вектор
        features = np.hstack([static_features, current_values]).reshape(1, -1)
        
        # Предсказываем следующие значения
        pred = model.predict(features)[0]
        
        # Обновляем текущие значения для следующей итерации
        current_values = pred
        predictions.append(pred)
    
    predictions = np.array(predictions)
    
    return predictions[:, 0], predictions[:, 1], predictions[:, 2]

