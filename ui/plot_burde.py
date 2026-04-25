import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotItem

from ui.downsampling import downsample_for_plot


def plot_burde(
    plot: PlotItem,
    t: np.ndarray,
    burde: np.ndarray,
    clear: bool=False,
):
    if clear:
        plot.clear()

    plot.setLabel("bottom","t")
    plot.setLabel("left","dP/dln(t)")
    plot.showGrid(x=True,y=True)
    plot.setLogMode(True,True)

    if plot.legend is None:
        plot.addLegend()

    t, burde, _, _ = downsample_for_plot(
        t,
        burde,
        log_space=True,
    )

    if len(t)==0:
        return

    plot.plot(
        t,
        burde,
        pen=pg.mkPen(color=(200,80,60), width=2),
        name="Бурде",
    )
