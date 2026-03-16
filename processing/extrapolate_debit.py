import numpy as np

from core.models import ProcessingDynamicData


def extrapolate_debit(
    data: ProcessingDynamicData,
) -> ProcessingDynamicData:
    """
    Экстраполирует дебит, продлевая последнее известное значение
    на новые точки времени.
    """

    if data is None:
        raise ValueError("ProcessingDynamicData is None")

    if data.is_Q_extrapolated:
        raise RuntimeError("Debit already extrapolated")

    if not data.is_t_extrapolated:
        raise RuntimeError("Time must be extrapolated first")

    t = data.t
    Q = data.Q

    if Q is None:
        raise ValueError("Debit array is None")

    # число исходных точек
    n_original = np.sum(~data.t_extrapolated_mask)

    Q_train = Q[:n_original]

    if np.isnan(Q_train).any():
        raise ValueError("Training debit contains NaN")

    # если время расширено — расширяем Q
    if len(Q) < len(t):

        Q_ext = np.full(len(t), np.nan)
        Q_ext[:len(Q)] = Q

        Q = Q_ext

    # последнее значение дебита
    Q_last = Q_train[-1]

    # будущие точки
    future_mask = data.t_extrapolated_mask

    Q[future_mask] = Q_last

    data.Q = Q
    data.Q_extrapolated_mask = future_mask
    data.is_Q_extrapolated = True

    return data
