from dataclasses import dataclass
import numpy as np
from typing import Optional, List

from schemas.static_params import StaticParams


@dataclass
class RefStaticParams:
    """Статические параметры референсной кривой из БД (без валидации)."""
    Skin: Optional[float] = None
    h: float = 0.0
    N: int = 1
    W: float = 0.0
    L: float = 0.0
    aL: float = 0.0


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
    is_P_interpolated: bool = False
    
    Q_interpolated_mask: Optional[np.ndarray] = None
    is_Q_interpolated: bool = False

    # экстраполяция
    t_extrapolated_mask: Optional[np.ndarray] = None
    is_t_extrapolated: bool = False
    
    P_extrapolated_mask: Optional[np.ndarray] = None
    is_P_extrapolated: bool = False
    
    Q_extrapolated_mask: Optional[np.ndarray] = None
    is_Q_extrapolated: bool = False
    
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
class MainRefCurve:
    """Лучшая подобранная эталонная кривая после оптимизации."""
    dimensionless: DimensionlessData
    static_params: RefStaticParams


@dataclass
class NeighbourRefCurve:
    """Одна соседняя кривая (Skin±1, Skin±2)."""
    dimensionless: DimensionlessData
    skin_offset: int  # -2, -1, +1, +2 — для цветовой маркировки на графике


@dataclass
class ReferenceCurves:
    """Коллекция референсных кривых: лучшая + соседи."""
    main: Optional[MainRefCurve] = None
    neighbours: Optional[List[NeighbourRefCurve]] = None
