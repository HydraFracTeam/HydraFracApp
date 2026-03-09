import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotItem


def plot_pressure(
    plot: PlotItem,
    t: np.ndarray,
    P: np.ndarray,
    clear: bool = True,
) -> None:
    """
    Отрисовка графика давления P(t)
    """

    if clear:
        plot.clear()

    plot.setTitle("Давление во времени")
    plot.setLabel("bottom", "Время, ч")
    plot.setLabel("left", "Давление")
    plot.showGrid(x=True, y=True)

    mask = np.isfinite(t) & np.isfinite(P)

    if not mask.any():
        return

    plot.plot(
        t[mask],
        P[mask],
        pen=pg.mkPen(color=(200, 50, 50), width=2),
        name="P(t)",
    )
