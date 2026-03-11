import numpy as np
from scipy.interpolate import PchipInterpolator

from core.app_state import ProcessingDynamicData


def _validate_input(data: ProcessingDynamicData) -> None:
    

    if data.is_P_interpolated:
        raise RuntimeError("Интерполяция уже выполнена")

    if data.t is None or data.P is None:
        raise ValueError("t и P должны быть определены")

    if len(data.t) != len(data.P):
        raise ValueError("t и P должны иметь одинаковую длину")

    if np.any(np.isnan(data.t)):
        raise ValueError("t не должен содержать значения NaN")

    if len(data.t) < 2:
        raise ValueError("Недостаточно точек")


def interpolate_pressure(data: ProcessingDynamicData) -> ProcessingDynamicData:
    if not data:
        return
    
    _validate_input(data)

    t = data.t
    P = data.P.copy()

    mask_valid = ~np.isnan(P)
    mask_missing = np.isnan(P)

    if mask_valid.sum() < 2:
        raise ValueError("Необходимо как минимум 2 допустимые точки давления")

    t_known = t[mask_valid]
    P_known = P[mask_valid]

    interpolator = PchipInterpolator(t_known, P_known, extrapolate=False)

    P_full = interpolator(t)

    # сохраняем оригинальные значения
    P_full[mask_valid] = P_known

    # только интерполированные точки
    P_interpolated = np.full_like(P_full, np.nan)
    P_interpolated[mask_missing] = P_full[mask_missing]

    # запись результатов
    data.P = P_full
    data.P_interpolated_mask = mask_missing
    data.is_P_interpolated = True

    return data
