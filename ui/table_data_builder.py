#ui/table_data_builder.py
import pandas as pd

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


def build_dimensional_dataframe(
    processing: ProcessingDynamicData,
) -> pd.DataFrame:

    data = {
        "t": processing.t,
        "P": processing.P,
        "dP": processing.dP,
        "Q": processing.Q,
        "dP/dt": processing.burde,
    }

    df = pd.DataFrame(data)

    return df.dropna(axis=1, how="all")


def build_dimensionless_dataframe(
    dimensionless: DimensionlessData,
) -> pd.DataFrame:

    data = {
        "X": dimensionless.X,
        "Y": dimensionless.Y,
    }

    df = pd.DataFrame(data)

    return df.dropna(axis=1, how="all")


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
