import numpy as np

from core.models import ProcessingDynamicData


def extend_masks_to_time_grid(data: ProcessingDynamicData) -> ProcessingDynamicData:

    t = data.t
    n = len(t)

    def extend_mask(mask):

        if mask is None:
            return None

        if len(mask) == n:
            return mask

        extended = np.zeros(n, dtype=bool)
        extended[:len(mask)] = mask
        return extended

    data.P_interpolated_mask = extend_mask(data.P_interpolated_mask)
    data.Q_interpolated_mask = extend_mask(data.Q_interpolated_mask)

    data.t_extrapolated_mask = extend_mask(data.t_extrapolated_mask)
    data.P_extrapolated_mask = extend_mask(data.P_extrapolated_mask)
    data.Q_extrapolated_mask = extend_mask(data.Q_extrapolated_mask)

    return data
