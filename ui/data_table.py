import numpy as np
import pandas as pd

from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QTableView, QHeaderView

from core.models import ProcessingDynamicData, DimensionlessData


def update_data_table_view(table_view: QTableView, processing: ProcessingDynamicData , dimensionless: DimensionlessData = None):
    """
    Обновляет таблицу данных пользователя.
    """

    data = {
        "t": processing.t,
        "P": processing.P,
        "dP": processing.dP,
        "Q": processing.Q,
    }

    if processing.P_interpolated is not None:
        data["P_interpolated"] = processing.P_interpolated

    if dimensionless is not None:
        data["X"] = dimensionless.X
        data["Y"] = dimensionless.Y

    df = pd.DataFrame(data)

    # удаляем колонки, где ВСЕ значения NaN
    df = df.dropna(axis=1, how="all")

    model = QStandardItemModel()

    model.setColumnCount(len(df.columns))
    model.setRowCount(len(df))

    model.setHorizontalHeaderLabels(df.columns.tolist())

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
    header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

def clear_data_table(table_view: QTableView) -> None:
    """
    Полностью очищает таблицу пользовательских данных.
    """

    model = QStandardItemModel()
    table_view.setModel(model)
