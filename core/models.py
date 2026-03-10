from dataclasses import dataclass
import numpy as np
from typing import Optional, Literal


from schemas.static_params import StaticParams


@dataclass
class RawDynamicData: # храним как изначальные введенные данные

    t: np.ndarray
    P: np.ndarray
    Q: np.ndarray

    is_Q_in_dynamic_input: bool
    
@dataclass
class ProcessingDynamicData: # храним как данные, с которыми работаем и которыми манипулируем
    t: np.ndarray
    P: np.ndarray
    Q: np.ndarray
    dP: np.ndarray
    
    is_Q_normalized: bool = False
    
    burde: Optional[np.ndarray] = None
    
    P_interpolated: Optional[np.ndarray] = None

    # экстраполяция
    t_extended: Optional[np.ndarray] = None
    P_extended: Optional[np.ndarray] = None
    Q_extended: Optional[np.ndarray] = None
    
@dataclass
class DimensionlessData:

    X: np.ndarray
    Y: np.ndarray
    

@dataclass
class SolverState:
    k_current: float
    L_current: float
    skin_current: float
    residual: float
    
    norm: Literal["l1", "l2", "integral"] = "l1"
    compare_by: Literal['linXY', "logXY", 'dP/dt'] = "linXY"




@dataclass
class ReferenceCurve:
    dynamic_data: RawDynamicData
    dimensionless: DimensionlessData
    static_params: StaticParams
