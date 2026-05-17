import pandas as pd

def export_dataframe_to_csv(
    filepath: str,
    df: pd.DataFrame,
) -> None:
    """
    Экспорт DataFrame в CSV.
    """

    if df is None or df.empty:
        raise ValueError(
            "Нет данных для экспорта"
        )

    df.to_csv(filepath, index=False)
