import numpy as np

from core.models import (
    ProcessingDynamicData,
    ProcessingOperationResult,
)


def remove_pressure_outliers(
    data: ProcessingDynamicData,
    window_percent: float = 0.01,
    relative_threshold: float = 0.015,
) -> ProcessingOperationResult:

    """
    Удаление выбросов давления с помощью:
    - локанной медианы,
    - относительного отклонения,
    - мягкой коррекции выбросов.

    Вместо полного удаления точки
    выброс ограничивается относительно
    локального тренда.

    Это позволяет:
    - сохранить локальную форму кривой,
    - уменьшить влияние spike-артефактов,
    - избежать фазовых искажений derivative.
    """

    if data is None:
        raise ValueError(
            "Данные для поиска выбросов не переданы!"
        )

    P = data.P.copy()

    mask_valid = np.isfinite(P)
    n_valid = int(mask_valid.sum())

    window = int(
        n_valid * window_percent
    )

    # минимально разумное окно
    window = max(window, 5)

    # окно должно быть нечетным
    if window % 2 == 0:
        window += 1
        
    if n_valid < 5:
        return ProcessingOperationResult(
            data=data,
            operation="pressure_outlier_removal",
            details=[
                (
                    "Удаление выбросов давления: "
                    "недостаточно точек для обработки"
                ),
            ],
        )

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

    corrected_count = 0

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

        if median == 0:
            continue

        relative_deviation = (
            np.abs(P[i] - median)
            / np.abs(median)
        )

        if relative_deviation > relative_threshold:

            outlier_mask[i] = True

            corrected_count += 1

            # Мягкая коррекция выброса

            sign = np.sign(
                P[i] - median
            )

            P[i] = (
                median
                + sign
                * relative_threshold
                * np.abs(median)
            )

    # первая точка не трогаем
    outlier_mask[0] = False

    total_points = len(P)

    outlier_percent = (
        corrected_count
        / total_points
        * 100
    )

    data.P = P

    data.is_P_interpolated = False
    data.is_Q_interpolated = False

    details = [
        (
            "Удаление выбросов давления: "
            f"скорректировано выбросов = {corrected_count}"
        ),

        (
            "Удаление выбросов давления: "
            f"изменено {outlier_percent:.2f}% ряда"
        ),

        (
            "Удаление выбросов давления: "
            f"window={window} "
            f"({window_percent:.1%} ряда), "
            f"relative_threshold={relative_threshold:.3f}"
        ),
    ]

    return ProcessingOperationResult(
        data=data,
        operation="pressure_outlier_removal",
        details=details,
    )
