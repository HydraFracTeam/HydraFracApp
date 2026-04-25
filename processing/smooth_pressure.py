import numpy as np
from scipy.signal import savgol_filter

from core.models import ProcessingDynamicData


def smooth_pressure(
    data: ProcessingDynamicData,
    window_length: int | None = None,
    polyorder: int = 3,
) -> ProcessingDynamicData:
    """
    Savitzky–Golay smoothing
    с динамическим окном.
    """

    if data is None:
        raise ValueError("ProcessingDynamicData is None")

    P = data.P
    t = data.t

    if P is None:
        raise ValueError("Pressure array is None")

    mask = np.isfinite(P) & (t > 1)

    if mask.sum() < polyorder + 2:
        return data

    P_valid = P[mask]

    # динамическое окно

    if window_length is None:

        n = len(P_valid)

        window_length = int(max(9,n * 0.01))

        if window_length % 2 == 0:
            window_length += 1

    if window_length >= len(P_valid):
        window_length = len(P_valid) - 1

        if window_length % 2 == 0:
            window_length -= 1

    if window_length <= polyorder:
        return data
    print(window_length)

    # --------------------------

    P_valid_smooth = savgol_filter(
        P_valid,
        window_length=window_length,
        polyorder=polyorder,
    )

    P_smooth = P.copy()
    P_smooth[mask] = P_valid_smooth

    data.P = P_smooth

    return data
