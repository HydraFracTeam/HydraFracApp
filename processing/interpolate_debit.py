import numpy as np
from core.app_state import ProcessingDynamicData


def _validate_input(data: ProcessingDynamicData) -> None:

    if data.is_Q_interpolated:
        raise RuntimeError("Интерполяция уже выполнена")

    if data.Q is None:
        raise ValueError("Массив Q отсутствует")

    if len(data.Q) == 0:
        raise ValueError("Массив Q пуст")


def interpolate_debit(data: ProcessingDynamicData) -> ProcessingDynamicData:
    """
    Восстановление дебита методом продолжения тренда (step interpolation).

    Пример:
    [nan,100,100,nan,nan,80,nan,60,nan]
    ->
    [100,100,100,100,100,80,80,60,60]
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

    return data
