from pydantic import BaseModel, field_validator, model_validator


class OptimizeThresholds(BaseModel):

    L_min: float
    L_max: float

    k_min: float
    k_max: float

    @field_validator("L_min", "L_max", "k_min", "k_max")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Границы оптимизации должны быть положительными")
        return v

    @model_validator(mode="after")
    def validate_bounds(self):

        if self.L_max < self.L_min:
            raise ValueError("L_max должно быть >= L_min")

        if self.k_max < self.k_min:
            raise ValueError("k_max должно быть >= k_min")

        return self
