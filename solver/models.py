"""
Модели данных для solver модуля.
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class CurveData:
    """Данные кривой X-Y."""
    x: np.ndarray
    y: np.ndarray


@dataclass
class StaticParams:
    """Статические параметры для библиотеки кривых."""
    h: float
    N: float
    W: float
    L: float
    a_L: float
