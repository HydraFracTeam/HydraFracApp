#ui/table_data_builder.py
import pandas as pd
import numpy as np
import hashlib

from PySide6.QtGui import (
    QStandardItemModel,
    QStandardItem,
)

from PySide6.QtWidgets import (
    QTableView,
    QHeaderView,
)

from core.models import (
    ProcessingDynamicData,
    DimensionlessData,
)

_dimensional_df_cache = {}
_dimensionless_df_cache = {}


def _array_cache_key(arr: np.ndarray | None) -> tuple:
    if arr is None:
        return ("none",)
    arr = np.ascontiguousarray(np.asarray(arr))
    digest = hashlib.blake2b(arr.view(np.uint8), digest_size=16).hexdigest()
    return (str(arr.dtype), arr.shape, digest)


def build_dimensional_dataframe(
    processing: ProcessingDynamicData,
) -> pd.DataFrame:
    cache_key = (
        _array_cache_key(processing.t),
        _array_cache_key(processing.P),
        _array_cache_key(processing.dP),
        _array_cache_key(processing.Q),
        _array_cache_key(processing.burde),
    )
    cached = _dimensional_df_cache.get(cache_key)
    if cached is not None:
        return cached

    data = {
        "t": processing.t,
        "P": processing.P,
        "dP": processing.dP,
        "Q": processing.Q,
        "dP/dt": processing.burde,
    }

    df = pd.DataFrame(data)

    df = df.dropna(axis=1, how="all")
    _dimensional_df_cache.clear()
    _dimensional_df_cache[cache_key] = df
    return df


def build_dimensionless_dataframe(
    dimensionless: DimensionlessData,
) -> pd.DataFrame:
    cache_key = (
        _array_cache_key(dimensionless.X),
        _array_cache_key(dimensionless.Y),
    )
    cached = _dimensionless_df_cache.get(cache_key)
    if cached is not None:
        return cached

    data = {
        "X": dimensionless.X,
        "Y": dimensionless.Y,
    }

    df = pd.DataFrame(data)

    df = df.dropna(axis=1, how="all")
    _dimensionless_df_cache.clear()
    _dimensionless_df_cache[cache_key] = df
    return df


def update_data_table_view(
    table_view: QTableView,
    df: pd.DataFrame,
):
    """
    Универсальная отрисовка DataFrame в QTableView.
    """

    model = QStandardItemModel()

    model.setColumnCount(len(df.columns))
    model.setRowCount(len(df))

    model.setHorizontalHeaderLabels(
        df.columns.tolist()
    )

    for row in range(len(df)):

        for col in range(len(df.columns)):

            val = df.iat[row, col]

            if pd.isna(val):
                item = QStandardItem("NaN")
            else:
                item = QStandardItem(f"{val:.6g}")

            item.setEditable(False)

            model.setItem(row, col, item)

    table_view.setModel(model)

    header = table_view.horizontalHeader()

    header.setSectionResizeMode(
        QHeaderView.ResizeMode.Stretch
    )


def clear_data_table(
    table_view: QTableView,
) -> None:
    """
    Полностью очищает таблицу.
    """

    model = QStandardItemModel()

    table_view.setModel(model)
