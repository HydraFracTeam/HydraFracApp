import numpy as np

from core.models import ProcessingDynamicData, ProcessingOperationResult


def _validate_input(data: ProcessingDynamicData) -> None:

    if data.is_Q_interpolated:
        raise RuntimeError("Интерполяция уже выполнена")

    if data.Q is None:
        raise ValueError("Массив Q отсутствует")

    if len(data.Q) == 0:
        raise ValueError("Массив Q пуст")


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


def interpolate_debit(
    data: ProcessingDynamicData
) -> ProcessingOperationResult:
    """
    Восстановление дебита методом продолжения тренда (step interpolation).
    """

    _validate_input(data)

    Q = data.Q.copy()

    n = len(Q)

    mask_missing = np.isnan(Q)

    if np.all(mask_missing):
        raise ValueError("Q содержит только значения NaN")

    # --- найти первый валидный элемент
    first_valid_idx = np.where(~mask_missing)[0][0]

    # заполнить начало
    Q[:first_valid_idx] = Q[first_valid_idx]

    last_value = Q[first_valid_idx]

    # основной проход
    for i in range(first_valid_idx + 1, n):

        if np.isnan(Q[i]):
            Q[i] = last_value
        else:
            last_value = Q[i]

    # маска интерполированных точек
    data.Q_interpolated_mask = mask_missing

    # обновить ряд
    data.Q = Q
    data.is_Q_interpolated = True

    n_interpolated = int(mask_missing.sum())

    restored_percent = (
        n_interpolated / n * 100
    )

    gap_segments = _calculate_gap_segments(mask_missing)

    max_gap = _calculate_max_gap(mask_missing)

    details = [
        f"Интерполяция дебита: восстановлено точек = {n_interpolated}",
        f"Интерполяция дебита: восстановлено {restored_percent:.2f}% ряда",
        f"Интерполяция дебита: количество gap-сегментов = {gap_segments}",
        f"Интерполяция дебита: максимальный gap = {max_gap} точек",
    ]

    return ProcessingOperationResult(
        data=data,
        operation="debit_interpolation",
        details=details,
    )
