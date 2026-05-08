import numpy as np

from core.models import (
    ProcessingDynamicData,
    ProcessingOperationResult,
)


def extrapolate_debit(
    data: ProcessingDynamicData,
) -> ProcessingOperationResult:
    """
    Экстраполяция дебита
    продолжением последнего значения.
    """

    if data is None:
        raise ValueError(
            "ProcessingDynamicData равна None"
        )

    if data.is_Q_extrapolated:
        raise RuntimeError(
            "Экстраполяция дебита уже выполнена"
        )

    if not data.is_t_extrapolated:
        raise RuntimeError(
            "Сначала необходимо экстраполировать время"
        )

    t = data.t

    Q = data.Q

    if Q is None:
        raise ValueError(
            "Массив дебита отсутствует"
        )

    n_original = int(
        np.sum(~data.t_extrapolated_mask)
    )

    Q_train = Q[:n_original]

    if np.isnan(Q_train).any():
        raise ValueError(
            "Обучающий ряд дебита содержит NaN"
        )

    if len(Q) < len(t):

        Q_ext = np.full(len(t), np.nan)

        Q_ext[:len(Q)] = Q

        Q = Q_ext

    Q_last = float(Q_train[-1])

    future_mask = data.t_extrapolated_mask

    Q[future_mask] = Q_last

    data.Q = Q

    data.Q_extrapolated_mask = future_mask

    data.is_Q_extrapolated = True

    n_extrapolated = int(
        np.sum(future_mask)
    )

    total_points = len(Q)

    extrapolated_percent = (
        n_extrapolated / total_points * 100
    )

    details = [
        f"Экстраполяция дебита: добавлено точек = {n_extrapolated}",
        f"Экстраполяция дебита: добавлено {extrapolated_percent:.2f}% ряда",
        f"Экстраполяция дебита: последнее значение дебита = {Q_last:.4f}",
    ]

    return ProcessingOperationResult(
        data=data,
        operation="debit_extrapolation",
        details=details,
    )
