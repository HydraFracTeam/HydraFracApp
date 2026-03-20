"""
Модуль автосплиттера для разделения КСД и КВД.

Автоматически обнаруживает склейку КСД (кривая стабилизации давления) 
и КВД (кривая восстановления давления) в одном временном ряду.

Алгоритм:
- Базовый критерий по времени:
  t ≤ 50000 → КСД (кривая стабилизации давления)
  t > 50000.01 → КВД (кривая восстановления давления)
"""

import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Пороговые значения
MIN_POINTS = 50
MIN_PRESSURE_RANGE = 1.0  # Минимальный размах давления для активации

# Пороговое значение времени для разделения КСД/КВД
# t ≤ 50000 - КСД (кривая стабилизации давления)
# t > 50000.01 - КВД (кривая восстановления давления)
SPLIT_TIME_KSD_END = 50000.0      # Последняя точка КСД
SPLIT_TIME_KVD_START = 50000.01   # Первая точка КВД


def detect_split_point(
    t: np.ndarray, 
    p: np.ndarray,
    min_points: int = MIN_POINTS,
    min_pressure_range: float = MIN_PRESSURE_RANGE
) -> Optional[int]:
    """
    Определение точки разделения КСД и КВД.
    
    Базовый критерий:
    - t ≤ 50000 → КСД (включительно)
    - t > 50000.01 → КВД (строго больше)
    
    Args:
        t: Время
        p: Давление
        min_points: Минимальное количество точек для анализа
        min_pressure_range: Минимальный размах давления
        
    Returns:
        Optional[int]: Индекс первой точки КВД или None если склейка не обнаружена
    """
    # Проверка условий активации
    if len(t) < min_points:
        logger.debug(f"Автосплиттер пропущен: недостаточно точек ({len(t)} < {min_points})")
        return None
    
    pressure_range = np.max(p) - np.min(p)
    if pressure_range < min_pressure_range:
        logger.debug(f"Автосплиттер пропущен: маленький размах давления ({pressure_range:.2f} < {min_pressure_range})")
        return None
    
    # Проверяем, есть ли данные за пределами порога
    # (т.е. есть ли в данных и КСД и КВД)
    has_ksd = np.any(t <= SPLIT_TIME_KSD_END)
    has_kvd = np.any(t >= SPLIT_TIME_KVD_START)
    
    if not (has_ksd and has_kvd):
        logger.debug("Склейка не обнаружена: отсутствуют данные КСД или КВД")
        return None
    
    # Находим первый индекс где t >= 50000.01 (начало КВД)
    for i in range(len(t)):
        if t[i] >= SPLIT_TIME_KVD_START:
            logger.info(f"Обнаружена точка разделения КСД/КВД на индексе {i} (t={t[i]:.2f})")
            return i
    
    logger.debug("Точка разделения не обнаружена")
    return None


def split_data(
    t: np.ndarray,
    p: np.ndarray,
    q: Optional[np.ndarray] = None,
    split_idx: Optional[int] = None
) -> Tuple[dict, dict]:
    """
    Разделение данных на КСД и КВД.
    
    КСД: t <= 50000 (включительно)
    КВД: t > 50000.01 (строго больше)
    
    Args:
        t: Время
        p: Давление
        q: Дебит (опционально)
        split_idx: Индекс точки разделения
        
    Returns:
        Tuple[dict, dict]: (ksd_data, kvd_data)
    """
    if split_idx is None:
        split_idx = detect_split_point(t, p)
    
    if split_idx is None:
        # Склейка не обнаружена - возвращаем пустой КВД
        ksd_data = {
            't': t,
            'p': p,
            'q': q,
            'name': 'КСД',
            'range': (0, len(t))
        }
        kvd_data = None
    else:
        # Разделяем данные
        # КСД: от начала до split_idx (включая точку с t=50000)
        # КВД: от split_idx до конца (начиная с точки t>50000.01)
        ksd_data = {
            't': t[:split_idx],
            'p': p[:split_idx],
            'q': q[:split_idx] if q is not None else None,
            'name': 'КСД',
            'range': (0, split_idx)
        }
        kvd_data = {
            't': t[split_idx:],
            'p': p[split_idx:],
            'q': q[split_idx:] if q is not None else None,
            'name': 'КВД',
            'range': (split_idx, len(t))
        }
    
    return ksd_data, kvd_data


def get_split_info(t: np.ndarray, p: np.ndarray) -> Optional[dict]:
    """
    Получение информации о разделении для UI.
    
    Args:
        t: Время
        p: Давление
        
    Returns:
        Optional[dict]: Информация о разделении или None
    """
    split_idx = detect_split_point(t, p)
    
    if split_idx is None:
        return None
    
    return {
        'index': split_idx,
        'time': t[split_idx],  # Время первой точки КВД (> 50000.01)
        'time_ksd_end': SPLIT_TIME_KSD_END,  # 50000 - конец КСД
        'time_kvd_start': SPLIT_TIME_KVD_START,  # 50000.01 - начало КВД
        'pressure': p[split_idx],
        'ksd_points': split_idx,
        'kvd_points': len(t) - split_idx,
        'ksd_percent': (split_idx / len(t)) * 100,
        'kvd_percent': ((len(t) - split_idx) / len(t)) * 100
    }
