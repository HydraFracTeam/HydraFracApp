# ui/solutions_view.py
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel
)
from PySide6.QtCore import Qt
import pyqtgraph as pg

from solver.solver_wrapper import SolverResult
from core.app_state import AppState

from ui import plot_reference_family

class SolutionView(QWidget):

    def __init__(
        self,
        solution,
        app_state
    ):
        super().__init__()

        self.solution:SolverResult=solution
        self.app_state:AppState=app_state

        layout=QVBoxLayout(self)

        label=QLabel(
            f"S={solution.S_opt:.2f}; "
            f"k={solution.k_opt:.2f}; "
            f"L={solution.L_opt:.2f}; "
            f"error={solution.error_value:.2f}"
        )

        label.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(label)

        self.plot = pg.PlotWidget()

        self.plot.setLogMode(
            x=True,
            y=True
        )

        self.plot.showGrid(
            x=True,
            y=True,
            alpha=0.35
        )

        self.plot.addLegend(
            offset=(10,10)
        )

        self.plot.setLabel('bottom', 'X')
        self.plot.setLabel('left', 'Y')

        self.plot.getAxis("bottom").enableAutoSIPrefix(False)
        self.plot.getAxis("left").enableAutoSIPrefix(False)

        layout.addWidget(
            self.plot
        )

        self.draw()


    def draw(self):
        plot_reference_family(
            plot=self.plot,
            factual_dimensionless=self.app_state.dimensionless,
            reference_curves=self.solution.reference_curves,
            runtime_settings=self.app_state.runtime_settings,
        )
