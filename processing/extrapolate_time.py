import numpy as np
from core.models import ProcessingDynamicData


def extrapolate_time(
    data: ProcessingDynamicData,
    extend_fraction: float = 0.5,
) -> ProcessingDynamicData:
    """
    Экстраполирует временную сетку.

    Добавляет новые точки времени, используя средний шаг.

    extend_fraction = 0.5 → добавляется 50% новых точек.
    """

    if data.is_t_extrapolated:
        raise RuntimeError("Время уже экстраполировано.")

    t = data.t

    if len(t) < 2:
        raise ValueError("Недостаточно точек для экстраполяции.")

    # средний шаг времени
    dt = np.mean(np.diff(t))

    n = len(t)
    n_new = max(int(n * extend_fraction), 1)

    t_last = t[-1]

    t_new = t_last + dt * np.arange(1, n_new + 1)

    t_ext = np.concatenate([t, t_new])

    # маска экстраполированных точек
    mask = np.zeros_like(t_ext, dtype=bool)
    mask[n:] = True

    # обновляем структуру
    data.t = t_ext
    data.t_extrapolated_mask = mask
    data.is_t_extrapolated = True

    return data
