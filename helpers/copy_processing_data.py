# helpers/copy_processing_data.py
from core.models import ProcessingDynamicData


def copy_processing_data(src: ProcessingDynamicData) -> ProcessingDynamicData:
    """
    Lightweight copy of ProcessingDynamicData.

    Instead of deepcopy (which recursively copies all Python internals),
    this function manually creates a new dataclass instance and calls
    .copy() on each numpy array. Scalars and booleans are copied by value.
    """
    return ProcessingDynamicData(
        t=src.t.copy(),
        P=src.P.copy(),
        Q=src.Q.copy(),
        dP=src.dP.copy() if src.dP is not None else None,
        burde=src.burde.copy() if src.burde is not None else None,
        is_Q_normalized=src.is_Q_normalized,
        P_interpolated_mask=src.P_interpolated_mask.copy() if src.P_interpolated_mask is not None else None,
        is_P_interpolated=src.is_P_interpolated,
        Q_interpolated_mask=src.Q_interpolated_mask.copy() if src.Q_interpolated_mask is not None else None,
        is_Q_interpolated=src.is_Q_interpolated,
        t_extrapolated_mask=src.t_extrapolated_mask.copy() if src.t_extrapolated_mask is not None else None,
        is_t_extrapolated=src.is_t_extrapolated,
        P_extrapolated_mask=src.P_extrapolated_mask.copy() if src.P_extrapolated_mask is not None else None,
        is_P_extrapolated=src.is_P_extrapolated,
        Q_extrapolated_mask=src.Q_extrapolated_mask.copy() if src.Q_extrapolated_mask is not None else None,
        is_Q_extrapolated=src.is_Q_extrapolated,
    )
