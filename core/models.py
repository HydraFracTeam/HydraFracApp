from dataclasses import dataclass
import numpy as np
from typing import Optional


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
    
    # интерполяция
    P_interpolated_mask: Optional[np.ndarray] = None
    Q_interpolated_mask: Optional[np.ndarray] = None
    is_interpolated: bool = False

    # экстраполяция
    t_extrapolated_mask: Optional[np.ndarray] = None
    P_extrapolated_mask: Optional[np.ndarray] = None
    Q_extrapolated_mask: Optional[np.ndarray] = None
    is_extrapolated: bool = False
    
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


@dataclass
class ReferenceCurve:
    dynamic_data: RawDynamicData
    dimensionless: DimensionlessData
    static_params: StaticParams
