import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotItem

from core.models import RuntimeSettings
from ui.downsampling import downsample_for_plot


def plot_burde(
    plot: PlotItem,
    t: np.ndarray,
    burde: np.ndarray,
    clear: bool=False,
    runtime_settings: RuntimeSettings | None = None,
):
    if clear:
        plot.clear()
    
    threshold = None
    points_per_decade = None
    if runtime_settings is not None:
        threshold = runtime_settings.downsample_threshold
        points_per_decade = runtime_settings.downsample_points_per_decade

    plot.setLabel("bottom","t")
    plot.setLabel("left","dP/dln(t)")
    plot.getAxis("bottom").enableAutoSIPrefix(False)
    plot.getAxis("left").enableAutoSIPrefix(False)
    plot.showGrid(x=True,y=True)
    plot.setLogMode(True,True)

    if plot.legend is None:
        plot.addLegend()

    t, burde, _, _ = downsample_for_plot(
        x=t,
        y=burde,
        threshold=threshold,
        points_per_decade=points_per_decade,
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
