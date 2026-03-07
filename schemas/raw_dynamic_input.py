from typing import Optional, List
from pydantic import BaseModel, field_validator, model_validator
import numpy as np


class RawDynamicDataInput(BaseModel):
    """
    Сырые динамические данные пользователя.
    Загружаются из CSV.
    """

    t: List[float]
    P: List[float]
    Q: Optional[List[float]] = None

    MIN_POINTS: int = 20

    @model_validator(mode="after")
    def validate_lengths(self):
        n = len(self.t)

        if n < self.MIN_POINTS:
            raise ValueError(f"Minimum number of time points is {self.MIN_POINTS}")

        if len(self.P) != n:
            raise ValueError("Length of P must match length of t")

        if self.Q is not None and len(self.Q) != n:
            raise ValueError("Length of Q must match length of t")

        return self

    @field_validator("t")
    @classmethod
    def validate_time(cls, v):

        arr = np.array(v, dtype=float)

        if np.isnan(arr).any():
            raise ValueError("Time array cannot contain NaN")

        if np.any(arr < 0):
            raise ValueError("Time values must be non-negative")

        # проверка монотонности
        if not np.all(np.diff(arr) > 0):
            raise ValueError("Time values must be strictly increasing")

        return v

    @field_validator("P")
    @classmethod
    def validate_pressure(cls, v):

        arr = np.array(v, dtype=float)

        if np.any(arr < 0):
            raise ValueError("Pressure values must be non-negative")

        return v

    @field_validator("Q")
    @classmethod
    def validate_flow(cls, v):

        if v is None:
            return v

        arr = np.array(v, dtype=float)

        if np.any(arr < 0):
            raise ValueError("Дебит должен быть неотрцительным")

        return v
