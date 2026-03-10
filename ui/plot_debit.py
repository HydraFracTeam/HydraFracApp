import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotItem


def plot_debit(
    plot: PlotItem,
    t: np.ndarray,
    Q: np.ndarray,
    Q_interpolated_mask: np.ndarray | None = None,
    Q_extrapolated_mask: np.ndarray | None = None,
    clear: bool = True,
) -> None:

    if clear:
        plot.clear()

    plot.setTitle("Дебит во времени")
    plot.setLabel("bottom", "Время, ч")
    plot.setLabel("left", "Дебит, м³/сут")
    plot.showGrid(x=True, y=True)
    # plot.setLogMode(x=True, y=False)

    if plot.legend is None:
        plot.addLegend()

    if len(t) == 0:
        return

    # основная линия дебита (с разрывами на NaN)
    plot.plot(
        t,
        Q,
        pen=pg.mkPen(color=(50, 150, 50), width=2),
        connect="finite",
        name="Q(t)",
    )

    finite_mask = np.isfinite(t) & np.isfinite(Q)

    # интерполированные точки
    if Q_interpolated_mask is not None and np.any(Q_interpolated_mask):

        interp_mask = Q_interpolated_mask & finite_mask

        plot.plot(
            t[interp_mask],
            Q[interp_mask],
            pen=None,
            symbol="o",
            symbolSize=8,
            symbolBrush=(255, 165, 0),
            name="Интерполировано",
        )

    # экстраполированные точки
    if Q_extrapolated_mask is not None and np.any(Q_extrapolated_mask):

        extra_mask = Q_extrapolated_mask & finite_mask

        plot.plot(
            t[extra_mask],
            Q[extra_mask],
            pen=None,
            symbol="t",
            symbolSize=9,
            symbolBrush=(80, 120, 255),
            name="Экстраполировано",
        )
