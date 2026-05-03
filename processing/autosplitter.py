import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

MIN_POINTS = 50
MIN_PRESSURE_RANGE = 1.0


# UTILS

def _smooth_signal(p: np.ndarray, window: int = 11) -> np.ndarray:
    """Простое сглаживание."""
    if window < 3:
        return p

    kernel = np.ones(window) / window
    return np.convolve(p, kernel, mode="same")


def _compute_slopes(t: np.ndarray, p: np.ndarray, window: int) -> np.ndarray:
    """Slope через линейную регрессию."""
    n = len(t)

    if n < window:
        return np.array([])

    slopes = np.zeros(n - window + 1)

    for i in range(n - window + 1):
        t_w = t[i:i + window]
        p_w = p[i:i + window]

        # нормализация времени (ВАЖНО)
        t_w = t_w - t_w[0]

        if np.allclose(t_w, 0):
            slopes[i] = 0.0
            continue

        slopes[i] = np.polyfit(t_w, p_w, 1)[0]

    return slopes


def _fallback_split(p: np.ndarray) -> int:
    """Устойчивый fallback через минимум."""
    p_smooth = _smooth_signal(p, window=21)

    window = 10
    means = np.array([
        np.mean(p_smooth[i:i + window])
        for i in range(len(p_smooth) - window)
    ])

    return int(np.argmin(means))


# MAIN DETECTOR

def detect_split_point(
    t: np.ndarray,
    p: np.ndarray,
    min_points: int = MIN_POINTS,
    min_pressure_range: float = MIN_PRESSURE_RANGE,
    window: int = 50,
    stable_window: int = 20,
    smooth: bool = True,
) -> Optional[int]:
    """
    Детекция КСД/КВД через смену тренда давления.
    """

    if len(t) < max(min_points, window * 2):
        return None

    pressure_range = np.max(p) - np.min(p)
    if pressure_range < min_pressure_range:
        return None

    # --- сглаживание ---
    p_proc = _smooth_signal(p) if smooth else p

    # --- slopes ---
    slopes = _compute_slopes(t, p_proc, window)

    if len(slopes) < stable_window * 2:
        return None

    # --- порог значимости ---
    eps = max(np.std(slopes) * 0.1, 1e-8)

    start = stable_window
    end = len(slopes) - stable_window

    for i in range(start, end):
        left_mean = np.mean(slopes[i - stable_window:i])
        right_mean = np.mean(slopes[i:i + stable_window])

        if left_mean < -eps and right_mean > eps:
            split_idx = i + window // 2
            confidence = right_mean - left_mean

            logger.info(
                f"Split: idx={split_idx}, t={t[split_idx]:.2f}, conf={confidence:.4f}"
            )
            return split_idx

    # --- fallback ---
    idx = _fallback_split(p)
    logger.info(f"Fallback split: idx={idx}, t={t[idx]:.2f}")
    return idx


# SPLIT DATA

def split_data(
    t: np.ndarray,
    p: np.ndarray,
    q: Optional[np.ndarray] = None,
    split_idx: Optional[int] = None
) -> Tuple[dict, Optional[dict]]:
    """
    Разделение данных:

    КСД — участок с отрицательным трендом давления  
    КВД — участок с положительным трендом
    """

    if split_idx is None:
        split_idx = detect_split_point(t, p)

    if split_idx is None:
        return {
            't': t,
            'p': p,
            'q': q,
            'name': 'КСД',
            'range': (0, len(t))
        }, None

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


# UI INFO

def get_split_info(t: np.ndarray, p: np.ndarray) -> Optional[dict]:
    split_idx = detect_split_point(t, p)

    if split_idx is None:
        return None

    return {
        'index': split_idx,
        'time': t[split_idx],
        'pressure': p[split_idx],
        'time_ksd_end': t[split_idx - 1] if split_idx > 0 else t[0],
        'time_kvd_start': t[split_idx],
        'ksd_points': split_idx,
        'kvd_points': len(t) - split_idx,
        'ksd_percent': (split_idx / len(t)) * 100,
        'kvd_percent': ((len(t) - split_idx) / len(t)) * 100
    }
