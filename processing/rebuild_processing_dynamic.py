from core.models import ProcessingDynamicData, DimensionlessData, RawDynamicData
from schemas import StaticParams
from helpers import (
    calculate_dP,
    calculate_burde,
    normalize_Q_by_n,
    )

def rebuild_processing_dynamic(
    raw_data: RawDynamicData,
    static_data: StaticParams,
    current_processing_data: ProcessingDynamicData | None
    ) -> ProcessingDynamicData:

        raw = raw_data
        static = static_data
        current = current_processing_data
        
        # источник данных
        if current is None:

            t = raw.t
            P = raw.P.copy()
            Q = raw.Q.copy()

            Q_is_normalized = False

            P_interpolated_mask = None
            is_P_interpolated = False

            Q_interpolated_mask = None
            is_Q_interpolated = False

            t_extrapolated_mask = None
            is_t_extrapolated = None
            
            P_extrapolated_mask = None
            is_P_extrapolated = False

            Q_extrapolated_mask = None
            is_Q_extrapolated = False

        else:

            t = current.t
            P = current.P
            Q = current.Q

            Q_is_normalized = current.is_Q_normalized

            P_interpolated_mask = current.P_interpolated_mask
            is_P_interpolated = current.is_P_interpolated

            Q_interpolated_mask = current.Q_interpolated_mask
            is_Q_interpolated = current.is_Q_interpolated

            t_extrapolated_mask = current.t_extrapolated_mask
            is_t_extrapolated = current.is_t_extrapolated
            
            P_extrapolated_mask = current.P_extrapolated_mask
            is_P_extrapolated = current.is_P_extrapolated

            Q_extrapolated_mask = current.Q_extrapolated_mask
            is_Q_extrapolated = current.is_Q_extrapolated

        # нормализация дебита
        if not Q_is_normalized:

            Q = normalize_Q_by_n(Q_total=Q, N=static.N)

            Q_is_normalized = True

        # расчет dP
        dP = calculate_dP(P=P, P0=static.P0)

        # Bourdet
        burde = calculate_burde(t=t, dP=dP)

        return ProcessingDynamicData(
            t=t,
            P=P,
            Q=Q,
            dP=dP,

            is_Q_normalized=Q_is_normalized,

            burde=burde,

            P_interpolated_mask=P_interpolated_mask,
            is_P_interpolated=is_P_interpolated,

            Q_interpolated_mask=Q_interpolated_mask,
            is_Q_interpolated=is_Q_interpolated,

            t_extrapolated_mask=t_extrapolated_mask,
            is_t_extrapolated=is_t_extrapolated,
            
            P_extrapolated_mask=P_extrapolated_mask,
            is_P_extrapolated=is_P_extrapolated,

            Q_extrapolated_mask=Q_extrapolated_mask,
            is_Q_extrapolated=is_Q_extrapolated,
        )
