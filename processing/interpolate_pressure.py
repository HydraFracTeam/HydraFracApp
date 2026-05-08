import numpy as np
from scipy.interpolate import PchipInterpolator

from core.app_state import ProcessingDynamicData
from core.models import ProcessingDynamicData, ProcessingOperationResult


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


def _calculate_gap_segments(mask: np.ndarray) -> int:

    if not np.any(mask):
        return 0

    diff = np.diff(mask.astype(int))

    starts = np.sum(diff == 1)

    if mask[0]:
        starts += 1

    return int(starts)


def _calculate_max_gap(mask: np.ndarray) -> int:

    max_gap = 0
    current = 0

    for val in mask:

        if val:
            current += 1
            max_gap = max(max_gap, current)
        else:
            current = 0

    return int(max_gap)


def interpolate_pressure(
    data: ProcessingDynamicData
) -> ProcessingOperationResult:

    if data is None:
        raise ValueError("ProcessingDynamicData равна None")

    _validate_input(data)

    t = data.t
    P = data.P.copy()

    mask_valid = ~np.isnan(P)
    mask_missing = np.isnan(P)

    if mask_valid.sum() < 2:
        raise ValueError("Необходимо как минимум 2 допустимые точки давления")

    t_known = t[mask_valid]
    P_known = P[mask_valid]

    interpolator = PchipInterpolator(
        t_known,
        P_known,
        extrapolate=False,
    )

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

    n_interpolated = int(mask_missing.sum())
    total_points = len(P)

    restored_percent = (
        n_interpolated / total_points * 100
    )

    gap_segments = _calculate_gap_segments(mask_missing)

    max_gap = _calculate_max_gap(mask_missing)

    details = [
        f"Интерполяция давления: восстановлено точек = {n_interpolated}",
        f"Интерполяция давления: восстановлено {restored_percent:.2f}% ряда",
        f"Интерполяция давления: количество gap-сегментов = {gap_segments}",
        f"Интерполяция давления: максимальный gap = {max_gap} точек",
    ]

    return ProcessingOperationResult(
        data=data,
        operation="pressure_interpolation",
        details=details,
    )
