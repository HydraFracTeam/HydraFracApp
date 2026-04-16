import numpy as np
from scipy.signal import savgol_filter

from core.models import ProcessingDynamicData


def smooth_pressure(
    data: ProcessingDynamicData,
    window_length: int = 9,
    polyorder: int = 3,
) -> ProcessingDynamicData:
    """
    Сглаживание давления методом Savitzky–Golay.

    Параметры
    ----------
    window_length : размер окна сглаживания (должен быть нечётным)
    polyorder : степень локального полинома
    """

    if data is None:
        raise ValueError("ProcessingDynamicData is None")

    P = data.P
    t = data.t

    if P is None:
        raise ValueError("Pressure array is None")

    if len(P) < window_length:
        # если данных мало — уменьшаем окно
        window_length = max(3, len(P) // 2 * 2 + 1)

    if window_length % 2 == 0:
        window_length += 1

    # маска реальных значений
    mask = np.isfinite(P) & (t > 1)

    if mask.sum() < polyorder + 2:
        return data

    P_smooth = P.copy()

    P_valid = P[mask]

    P_valid_smooth = savgol_filter(
        P_valid,
        window_length=window_length,
        polyorder=polyorder,
    )

    P_smooth[mask] = P_valid_smooth

    data.P = P_smooth

    return data
