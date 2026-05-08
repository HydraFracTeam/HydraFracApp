import numpy as np

from core.models import (
    ProcessingDynamicData,
    ProcessingOperationResult,
)


def extrapolate_time(
    data: ProcessingDynamicData,
    extend_fraction: float = 0.5,
) -> ProcessingOperationResult:
    """
    Экстраполяция временной сетки.
    """

    if data is None:
        raise ValueError(
            "Динамические данные для предобработки еще не сформированы."
        )

    if data.is_t_extrapolated:
        raise RuntimeError(
            "Время уже экстраполировано."
        )

    t = data.t

    if len(t) < 2:
        raise ValueError(
            "Недостаточно точек для экстраполяции."
        )

    dt = float(np.mean(np.diff(t)))

    n = len(t)

    n_new = max(
        int(n * extend_fraction),
        1,
    )

    t_last = t[-1]

    t_new = (
        t_last
        + dt * np.arange(1, n_new + 1)
    )

    t_ext = np.concatenate([t, t_new])

    mask = np.zeros_like(
        t_ext,
        dtype=bool,
    )

    mask[n:] = True

    data.t = t_ext
    data.t_extrapolated_mask = mask
    data.is_t_extrapolated = True

    total_points = len(t_ext)

    extrapolated_percent = (
        n_new / total_points * 100
    )

    details = [
        f"Экстраполяция времени: добавлено точек = {n_new}",
        f"Экстраполяция времени: добавлено {extrapolated_percent:.2f}% ряда",
        f"Экстраполяция времени: средний шаг времени = {dt:.4f}",
    ]

    return ProcessingOperationResult(
        data=data,
        operation="time_extrapolation",
        details=details,
    )
