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

from ui.downsampling import downsample_for_plot

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

        self.plot.clear()

        # factual curve

        x = self.app_state.dimensionless.X
        y = self.app_state.dimensionless.Y

        threshold = self.app_state.runtime_settings.downsample_threshold
        points_per_decade = self.app_state.runtime_settings.downsample_points_per_decade
        
        x,y,_,_ = downsample_for_plot(
            x=x,
            y=y,
            threshold=threshold,
            points_per_decade=points_per_decade,
            log_space=True
        )

        self.plot.plot(
            x,
            y,
            name="Фактическая кривая",
            pen=pg.mkPen(
                color=(30,30,30),
                width=2
            ),
            symbol='o',
            symbolSize=4,
            symbolBrush=(30,30,30)
        )

        ref = self.solution.reference_curves

        # best fit

        if ref and ref.main:

            xr = ref.main.dimensionless.X
            yr = ref.main.dimensionless.Y

            xr,yr,_,_ = downsample_for_plot(
                xr,
                yr,
                threshold=threshold,
                points_per_decade=points_per_decade,
                log_space=True
            )

            self.plot.plot(
                xr,
                yr,
                name="Эталонная кривая",
                pen=pg.mkPen(
                    color=(220,50,47),
                    width=3,
                    style=Qt.DashLine
                )
            )


        # ----------------------
        # neighbours
        # ----------------------

        colors = {
            -2: (38,139,210),
            -1: (133,153,0),
            1: (181,137,0),
            2: (108,113,196)
        }


        if ref and ref.neighbours:

            for n in ref.neighbours:

                xn = n.dimensionless.X
                yn = n.dimensionless.Y

                xn,yn,_,_ = downsample_for_plot(
                    xn,
                    yn,
                    threshold=threshold,
                    points_per_decade=points_per_decade,
                    log_space=True
                )

                c = colors.get(
                    n.skin_offset,
                    (120,120,120)
                )

                self.plot.plot(
                    xn,
                    yn,
                    name=f"Сосед: Skin {n.skin_offset:+d}",
                    pen=pg.mkPen(
                        color=c,
                        width=1.5
                    )
                )
