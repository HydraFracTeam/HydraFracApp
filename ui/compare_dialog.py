# compare_dialog.py

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QSplitter
)
from PySide6.QtCore import Qt

from ui.solution_view import SolutionView


class CompareDialog(QDialog):

    def __init__(self, solutions, app_state, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Сравнение решений")
        self.resize(1600, 900)

        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Vertical)

        top = QSplitter(Qt.Horizontal)
        bottom = QSplitter(Qt.Horizontal)

        # верхние 2
        for sol in solutions[:2]:
            top.addWidget(
                SolutionView(sol, app_state)
            )

        # нижние 3
        for sol in solutions[2:]:
            bottom.addWidget(
                SolutionView(sol, app_state)
            )

        splitter.addWidget(top)
        splitter.addWidget(bottom)

        splitter.setSizes([500, 500])

        layout.addWidget(splitter)
