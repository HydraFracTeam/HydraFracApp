import numpy as np

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableView, QPushButton,
    QHBoxLayout, QApplication, QHeaderView, QMessageBox,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QKeySequence

from utils import format_pydantic_error
from schemas.raw_dynamic_input import RawDynamicDataInput
from core.models import RawDynamicData


class PasteDataDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Вставка динамических данных")
        self.resize(750, 500)

        layout = QVBoxLayout(self)

        # таблица
        self.table = QTableView()
        layout.addWidget(self.table)

        self.model = QStandardItemModel()
        self.model.setColumnCount(3)
        self.model.setHorizontalHeaderLabels(["t", "P", "Q"])
        self.model.setRowCount(100)

        self.table.setModel(self.model)

        # UX таблицы
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)

        # кнопки
        btn_layout = QHBoxLayout()

        self.paste_btn = QPushButton("Вставить из буфера")
        self.reset_btn = QPushButton("Очистить таблицу")
        self.ok_btn = QPushButton("Ввести данные")
        self.cancel_btn = QPushButton("Отмена")

        btn_layout.addWidget(self.paste_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        # connections
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        self.reset_btn.clicked.connect(self.clear_table)
        self.ok_btn.clicked.connect(self.validate_and_accept)
        self.cancel_btn.clicked.connect(self.reject)

    # --------------------------------------------------
    # Очистка таблицы
    # --------------------------------------------------

    def clear_table(self):
        """
        Полная очистка таблицы.
        """
        self.model.removeRows(0, self.model.rowCount())
        self.model.setRowCount(100)

    # --------------------------------------------------
    # Excel / CSV paste
    # --------------------------------------------------
    def paste_from_clipboard(self):

        clipboard = QApplication.clipboard()
        text = clipboard.text()

        if not text:
            return

        rows = text.strip().split("\n")

        # текущая выбранная ячейка
        index = self.table.currentIndex()

        start_row = index.row() if index.isValid() else 0
        start_col = index.column() if index.isValid() else 0

        # расширяем таблицу если нужно
        required_rows = start_row + len(rows)
        if required_rows > self.model.rowCount():
            self.model.setRowCount(required_rows)

        for r_offset, row in enumerate(rows):

            if "\t" in row:
                values = row.split("\t")
            else:
                values = row.split(",")

            for c_offset, val in enumerate(values):

                col = start_col + c_offset
                row_idx = start_row + r_offset

                if col >= self.model.columnCount():
                    break

                item = QStandardItem(val.strip())
                self.model.setItem(row_idx, col, item)
    # Ctrl+V
    def keyPressEvent(self, event):

        if event.matches(QKeySequence.Paste):
            self.paste_from_clipboard()
            return

        super().keyPressEvent(event)

    # --------------------------------------------------
    # Извлечение данных
    # --------------------------------------------------

    def get_data(self) -> RawDynamicData:

        t, P, Q = [], [], []

        rows = self.model.rowCount()

        for r in range(rows):

            t_item = self.model.item(r, 0)
            p_item = self.model.item(r, 1)
            q_item = self.model.item(r, 2)

            if not t_item or not p_item:
                continue

            t_val = t_item.text().strip()
            p_val = p_item.text().strip()

            if t_val == "" or p_val == "":
                continue

            t.append(float(t_val))
            P.append(float(p_val))

            if q_item and q_item.text().strip():
                Q.append(float(q_item.text()))
            else:
                Q.append(np.nan)

        if len(t) == 0:
            raise ValueError("Не введены данные t и P")

        # проверяем колонку Q
        if all(np.isnan(v) for v in Q):
            Q = None

        validated = RawDynamicDataInput(
            t=t,
            P=P,
            Q=None if Q is None else Q
        )

        return RawDynamicData(
            t=np.asarray(validated.t),
            P=np.asarray(validated.P),
            Q=None if validated.Q is None else np.asarray(validated.Q),
            is_Q_in_dynamic_input=validated.Q is not None
        )

    def validate_and_accept(self):
        """
        Проверяет данные перед закрытием окна.
        Если есть ошибка — показывает сообщение и
        не закрывает диалог.
        """

        try:
            self.get_data()  # проверяем валидность
        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка данных",
                format_pydantic_error(e)
            )
            return

        # если всё хорошо — закрываем окно
        self.accept()
