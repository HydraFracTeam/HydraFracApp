import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotItem

from ui.downsampling import downsample_for_plot


def plot_xy(
    plot: PlotItem,
    X: np.ndarray,
    Y: np.ndarray,
    clear: bool=False,
):
    if clear:
        plot.clear()

    plot.setLabel("bottom", "X")
    plot.setLabel("left", "Y")
    plot.getAxis("bottom").enableAutoSIPrefix(False)
    plot.getAxis("left").enableAutoSIPrefix(False)
    plot.showGrid(x=True,y=True)
    plot.setLogMode(True,True)

    if plot.legend is None:
        plot.addLegend()

    X, Y, _, _ = downsample_for_plot(
        X,
        Y,
        log_space=True,
    )

    if len(X) == 0:
        return

    plot.plot(
        X,
        Y,
        pen=pg.mkPen(color=(50,120,220), width=2),
        name="Калькулированные XY",
    )
