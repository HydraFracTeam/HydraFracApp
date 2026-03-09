import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotItem


def plot_xy(
    plot: PlotItem,
    X: np.ndarray,
    Y: np.ndarray,
    label: str = "XY",
    color=(50, 120, 220),
    width: int = 2,
    clear: bool = False,
):
    """
    Универсальная функция построения XY кривых.

    Подходит для:
    - пользовательских XY
    - reference curves
    - solver iteration curves
    """

    if clear:
        plot.clear()
        
    plot.setLabel("bottom", "X")
    plot.setLabel("left", "Y")
    plot.showGrid(x=True, y=True)

    plot.setLogMode(True, True)
    
    if plot.legend is None:
        plot.addLegend()

    mask = np.isfinite(X) & np.isfinite(Y)

    if not mask.any():
        return

    plot.plot(
        X[mask],
        Y[mask],
        pen=pg.mkPen(color=color, width=width),
        name=label,
    )
