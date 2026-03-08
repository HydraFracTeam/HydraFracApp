from typing import Optional
from pydantic import BaseModel, field_validator


class StaticParams(BaseModel):

    W: float
    h: float
    mu: float
    phi: float
    B: float
    ct: float
    N: int
    aL: float

    Q_constant: Optional[float] = None

    @field_validator("W", "h", "mu", "ct")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Параметр должен быть положительным")
        return v

    @field_validator("phi")
    @classmethod
    def validate_phi(cls, v):
        if not (0 < v < 1):
            raise ValueError("Пористость должна быть между 0 и 1")
        return v

    @field_validator("B")
    @classmethod
    def validate_B(cls, v):
        if v <= 0:
            raise ValueError("Объемный коэффициент должен быть положительным")
        return v

    @field_validator("N")
    @classmethod
    def validate_N(cls, v):
        if v < 2:
            raise ValueError("Количество трещин должно быть >= 2")
        return v

    @field_validator("Q_constant")
    @classmethod
    def validate_Q(cls, v):
        if v is None:
            return v

        if v <= 0:
            raise ValueError("Дебит должен быть положительным")

        return v
