import numpy as np

from core.models import (
    ProcessingDynamicData,
    ProcessingOperationResult,
)


def remove_pressure_outliers(
    data: ProcessingDynamicData,
    window: int = 7,
    threshold: float = 7.0,
) -> ProcessingOperationResult:

    if data is None:
        raise ValueError(
            "Данные для поиска выбросов не переданы!"
        )

    P = data.P.copy()

    mask_valid = np.isfinite(P)

    if mask_valid.sum() < window:

        return ProcessingOperationResult(
            data=data,
            operation="pressure_outlier_removal",
            details=[
                "Удаление выбросов давления: недостаточно точек для обработки",
            ],
        )

    half = window // 2

    outlier_mask = np.zeros_like(
        P,
        dtype=bool,
    )

    for i in range(len(P)):

        if not mask_valid[i]:
            continue

        left = max(0, i - half)

        right = min(
            len(P),
            i + half + 1,
        )

        window_vals = P[left:right]

        window_vals = window_vals[
            np.isfinite(window_vals)
        ]

        if len(window_vals) < 3:
            continue

        median = np.median(window_vals)

        mad = np.median(
            np.abs(window_vals - median)
        )

        if mad == 0:
            continue

        score = (
            np.abs(P[i] - median) / mad
        )

        if score > threshold:
            outlier_mask[i] = True

    # сохраняем первую точку
    outlier_mask[0] = False

    n_outliers = int(
        np.sum(outlier_mask)
    )

    total_points = len(P)

    outlier_percent = (
        n_outliers / total_points * 100
    )

    P[outlier_mask] = np.nan

    data.P = P

    data.is_P_interpolated = False
    data.is_Q_interpolated = False

    details = [
        f"Удаление выбросов давления: найдено выбросов = {n_outliers}",
        f"Удаление выбросов давления: удалено {outlier_percent:.2f}% ряда",
        (
            "Удаление выбросов давления: "
            f"window={window}, threshold={threshold}"
        ),
    ]

    return ProcessingOperationResult(
        data=data,
        operation="pressure_outlier_removal",
        details=details,
    )
