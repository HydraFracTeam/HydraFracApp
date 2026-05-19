import numpy as np
from scipy.signal import savgol_filter

from core.models import (
    ProcessingDynamicData,
    ProcessingOperationResult,
)


def smooth_pressure(
    data: ProcessingDynamicData,
    window_length: int | None = None,
    polyorder: int = 3,
) -> ProcessingOperationResult:
    """
    Savitzky–Golay smoothing.
    """

    if data is None:
        raise ValueError(
            "ProcessingDynamicData is None"
        )

    P = data.P

    t = data.t

    if P is None:
        raise ValueError(
            "Pressure array is None"
        )

    mask = np.isfinite(P) & (t > 1)

    if mask.sum() < polyorder + 2:

        return ProcessingOperationResult(
            data=data,
            operation="pressure_smoothing",
            details=[
                "Сглаживание давления: недостаточно точек для обработки",
            ],
        )

    P_valid = P[mask]

    if window_length is None:

        n = len(P_valid)

        window_length = int(n * 0.05)

        if window_length % 2 == 0:
            window_length += 1

    if window_length >= len(P_valid):

        window_length = len(P_valid) - 1

        if window_length % 2 == 0:
            window_length -= 1

    if window_length <= polyorder:

        return ProcessingOperationResult(
            data=data,
            operation="pressure_smoothing",
            details=[
                "Сглаживание давления: окно сглаживания слишком мало",
            ],
        )

    P_valid_smooth = savgol_filter(
        P_valid,
        window_length=window_length,
        polyorder=polyorder,
    )

    P_smooth = P.copy()

    P_smooth[mask] = P_valid_smooth

    data.P = P_smooth

    details = [
        (
            "Сглаживание давления: "
            f"window={window_length}, "
            f"polyorder={polyorder}"
        ),
    ]

    return ProcessingOperationResult(
        data=data,
        operation="pressure_smoothing",
        details=details,
    )
