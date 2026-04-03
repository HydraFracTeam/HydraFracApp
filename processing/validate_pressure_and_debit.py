import numpy as np
from core.models import ProcessingDynamicData


def validate_pressure_and_debit(
    data: ProcessingDynamicData,
) -> None:
    """
    Проверяет, что массивы давления (P) и дебита (Q)
    не содержат пропусков и валидны для расчёта.

    Raises
    ------
    ValueError
        Если данные некорректны
    """

    if data is None:
        raise ValueError("ProcessingDynamicData is None")

    if data.P is None or data.Q is None:
        raise ValueError("Данные давления (P) или дебита (Q) отсутствуют")

    if len(data.P) == 0 or len(data.Q) == 0:
        raise ValueError("Пустые массивы P или Q")

    if len(data.P) != len(data.Q):
        raise ValueError("P и Q должны иметь одинаковую длину")

    if not np.isfinite(data.P).all() or not np.isfinite(data.Q).all():
        raise ValueError(
            "Обнаружены пропуски или некорректные значения (NaN/inf) в P или Q"
        )
