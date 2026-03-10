import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotItem


def plot_burde(
    plot: PlotItem,
    t: np.ndarray,
    burde: np.ndarray,
    label: str = "Бурде",
    color=(200, 80, 60),
    width: int = 2,
    clear: bool = False,
):
    """
    Отрисовка производной Бурде.
    """

    if clear:
        plot.clear()

    plot.setLabel("bottom", "t")
    plot.setLabel("left", "dP/dln(t)")
    plot.showGrid(x=True, y=True)
    plot.setLogMode(True, True)

    if plot.legend is None:
        plot.addLegend()

    mask = np.isfinite(t) & np.isfinite(burde)

    if not mask.any():
        return

    plot.plot(
        t[mask],
        burde[mask],
        pen=pg.mkPen(color=color, width=width),
        name=label,
    )
