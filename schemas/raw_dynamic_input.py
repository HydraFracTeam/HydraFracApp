from typing import Optional, List
from pydantic import BaseModel, field_validator, model_validator
import numpy as np

from config import settings

class RawDynamicDataInput(BaseModel):
    """
    Сырые динамические данные пользователя.
    Загружаются из CSV или вставляются из буфера обмена.
    """

    t: List[float]
    P: List[float]
    Q: Optional[List[float]] = None

    MIN_POINTS: int = settings.MIN_POINTS_FOR_t

    @model_validator(mode="after")
    def validate_lengths(self):
        n = len(self.t)

        if n < self.MIN_POINTS:
            raise ValueError(f"Минимальное количество временных точек равно {self.MIN_POINTS}")

        if len(self.P) != n:
            raise ValueError("Длина P должна совпадать с длиной t")

        if self.Q is not None and len(self.Q) != n:
            raise ValueError("Длина Q должна совпадать с длиной t")

        return self

    @field_validator("t")
    @classmethod
    def validate_time(cls, v):

        arr = np.array(v, dtype=float)

        if np.isnan(arr).any():
            raise ValueError("Временной массив не может содержать NaN")

        if np.any(arr < 0):
            raise ValueError("Временные значения должны быть неотрицательными")

        # проверка монотонности
        if not np.all(np.diff(arr) > 0):
            raise ValueError("Временные значения должны строго возрастать")

        return v

    @field_validator("P")
    @classmethod
    def validate_pressure(cls, v):

        arr = np.array(v, dtype=float)

        if np.any(arr < 0):
            raise ValueError("Значения давления должны быть неотрицательными")

        return v

    @field_validator("Q")
    @classmethod
    def validate_flow(cls, v):

        if v is None:
            return v

        arr = np.array(v, dtype=float)

        if np.any(arr < 0):
            raise ValueError("Дебит должен быть неотрицательным")

        return v
