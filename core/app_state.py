from dataclasses import dataclass
from typing import Optional

from core.models import (
    RawDynamicData,
    ReferenceCurve,
    SolverState,
    ProcessingDynamicData,
    DimensionlessData,
)
from schemas import (
    StaticParams,
    OptimizeThresholds,
)


@dataclass
class AppState:
    """
    Central application state container.
    Stores all runtime data used by UI and solver.
    """

    raw_dynamic_data: Optional[RawDynamicData] = None # хранит изначальные динамические данные, ненормированный дебит, используется при откате как оригинал
    
    processing_dynamic_data: Optional[ProcessingDynamicData] = None # содержит изменяемые динамические, с ними происходит обработка данных, от них считаем XY и прочее
    
    dimensionless: Optional[DimensionlessData] = None # используется для хранения безразмерных значений как X, Y, возможно, других
    
    static_params: Optional[StaticParams] = None # статичные параметры пласта и скважины при вводе (опциональный постоянный дебит), не меняются на протяжении сеанса
    
    optimize_thresholds: Optional[OptimizeThresholds] = None # границы для полудлины трещины L и проницаемости k
    
    reference_curve: Optional[ReferenceCurve] = None # моделька для текущей эталонной кривой, может позже поменяться 

    solver_state: Optional[SolverState] = None # параметры солвера, хранит данные решения и невязку

