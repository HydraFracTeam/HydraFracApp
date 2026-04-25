from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel
)

from PySide6.QtCore import Qt

import pyqtgraph as pg


class SolutionView(QWidget):

    def __init__(
        self,
        solution,
        app_state
    ):
        super().__init__()

        self.solution=solution
        self.app_state=app_state

        layout=QVBoxLayout(self)

        label=QLabel(
            f"S={solution.S_opt:.2f} "
            f"k={solution.k_opt:.2f} "
            f"L={solution.L_opt:.2f}"
        )

        label.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(label)

        self.plot=pg.PlotWidget()

        self.plot.setLogMode(
            x=True,
            y=True
        )
        self.plot.setLogMode(x=True, y=True)
        self.plot.showGrid(x=True, y=True, alpha=0.35)

        layout.addWidget(
            self.plot
        )

        self.draw()


    def draw(self):

        self.plot.clear()
        self.plot.showGrid(
            x=True,
            y=True,
            alpha=0.3
        )

        x=self.app_state.dimensionless.X
        y=self.app_state.dimensionless.Y

        self.plot.plot(
            x,y,
            name="Fact",
            pen=pg.mkPen(width=2),
            symbol='o',
            symbolSize=3
        )

        ref=self.solution.reference_curves

        if ref and ref.main:

            self.plot.plot(
                ref.main.dimensionless.X,
                ref.main.dimensionless.Y,
                name="Best fit",
                pen=pg.mkPen(
                    width=3,
                    style=Qt.DashLine
                )
            )

        if ref and ref.neighbours:

            for n in ref.neighbours:

                self.plot.plot(
                    n.dimensionless.X,
                    n.dimensionless.Y,
                    name=f"Skin {n.skin_offset:+d}",
                    pen=pg.mkPen(width=1)
                )
