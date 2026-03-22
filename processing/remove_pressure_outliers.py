import numpy as np
from core.models import ProcessingDynamicData


def remove_pressure_outliers(
    data: ProcessingDynamicData,
    window: int = 7,
    threshold: float = 7.0,
) -> ProcessingDynamicData:

    if data is None:
        raise ValueError("Данные для поиска выбросов не переданы!")

    P = data.P.copy()

    mask_valid = np.isfinite(P)

    if mask_valid.sum() < window:
        return data

    half = window // 2

    outlier_mask = np.zeros_like(P, dtype=bool)

    for i in range(len(P)):

        if not mask_valid[i]:
            continue

        left = max(0, i - half)
        right = min(len(P), i + half + 1)

        window_vals = P[left:right]
        window_vals = window_vals[np.isfinite(window_vals)]

        if len(window_vals) < 3:
            continue

        median = np.median(window_vals)
        mad = np.median(np.abs(window_vals - median))

        if mad == 0:
            continue

        score = np.abs(P[i] - median) / mad

        if score > threshold:
            outlier_mask[i] = True

    outlier_mask[0] = False # чтобы не съело первую точку давления
    
    # превращаем выбросы в NaN
    P[outlier_mask] = np.nan

    data.P = P
    data.is_P_interpolated = False

    return data
