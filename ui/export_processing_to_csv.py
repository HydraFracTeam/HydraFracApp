import pandas as pd
from core.models import ProcessingDynamicData, DimensionlessData


def export_processing_to_csv(
    filepath: str,
    processing: ProcessingDynamicData,
    dimensionless: DimensionlessData | None = None,
) -> None:
    """
    Экспортирует текущие данные в CSV.
    """

    if processing is None:
        raise ValueError("Нет данных для экспорта")

    data = {
        "t": processing.t,
        "P": processing.P,
        "dP": processing.dP,
        "Q": processing.Q,
        "dP/dt": processing.burde,
    }

    if dimensionless is not None:
        data["X"] = dimensionless.X
        data["Y"] = dimensionless.Y

    df = pd.DataFrame(data)

    # удаляем полностью пустые колонки
    df = df.dropna(axis=1, how="all")

    df.to_csv(filepath, index=False)
