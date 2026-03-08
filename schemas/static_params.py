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

    Q_constant: Optional[float] = None

    @field_validator("W")
    @classmethod
    def validate_W(cls, v):
        if v <= 0:
            raise ValueError("Длина пласта должна быть положительной")
        return v

    @field_validator("h")
    @classmethod
    def validate_h(cls, v):
        if v <= 0:
            raise ValueError("Высота пласта должна быть положительной")
        return v

    @field_validator("mu")
    @classmethod
    def validate_mu(cls, v):
        if v <= 0:
            raise ValueError("Вязкость должна быть положительной")
        return v

    @field_validator("ct")
    @classmethod
    def validate_ct(cls, v):
        if v <= 0:
            raise ValueError("Общая сжимаемость должна быть положительной")
        return v

    @field_validator("phi")
    @classmethod
    def validate_phi(cls, v):
        if not (0 <= v <= 1):
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

        if v < 0:
            raise ValueError("Дебит должен быть неотрицательным")

        return v
