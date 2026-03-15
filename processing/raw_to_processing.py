import numpy as np

from core.models import RawDynamicData, ProcessingDynamicData


def raw_to_processing(raw: RawDynamicData) -> ProcessingDynamicData:
    """
    Создаёт ProcessingDynamicData из RawDynamicData.
    Все служебные поля и маски устанавливаются в значения по умолчанию.
    """

    if raw is None:
        raise ValueError("RawDynamicData is None")

    return ProcessingDynamicData(
        t=raw.t.copy(),
        P=raw.P.copy(),
        Q=raw.Q.copy(),
        dP=np.full_like(raw.P, np.nan),

        is_Q_normalized=False,

        burde=None,

        # интерполяция
        P_interpolated_mask=None,
        is_P_interpolated=False,

        Q_interpolated_mask=None,
        is_Q_interpolated=False,

        # экстраполяция времени
        t_extrapolated_mask=None,
        is_t_extrapolated=False,

        # экстраполяция давления
        P_extrapolated_mask=None,
        is_P_extrapolated=False,

        # экстраполяция дебита
        Q_extrapolated_mask=None,
        is_Q_extrapolated=False,
    )
