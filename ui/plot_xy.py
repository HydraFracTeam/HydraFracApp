# ui/plot_xy.py

import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt
from pyqtgraph import PlotItem

from core.models import RuntimeSettings
from ui.downsampling import downsample_for_plot


def plot_xy(
    plot: PlotItem,
    X: np.ndarray,
    Y: np.ndarray,
    *,
    clear: bool = False,
    color: tuple = (50,120,220),
    width: int = 2,
    style = Qt.PenStyle.SolidLine,
    name: str = "Калькулированные XY",
    runtime_settings: RuntimeSettings | None = None,
    show_symbols: bool = True,
    symbol_size: int = 4,
):
    """
    Универсальная отрисовка XY-кривой.
    """

    if clear:
        plot.clear()

    threshold = None
    points_per_decade = None

    if runtime_settings is not None:

        threshold = (
            runtime_settings.downsample_threshold
        )

        points_per_decade = (
            runtime_settings.downsample_points_per_decade
        )

    plot.setLabel("bottom", "X")
    plot.setLabel("left", "Y")

    plot.getAxis("bottom").enableAutoSIPrefix(False)
    plot.getAxis("left").enableAutoSIPrefix(False)

    plot.showGrid(x=True, y=True)

    plot.setLogMode(True, True)

    plot_item = (
        plot.getPlotItem()
        if isinstance(plot, pg.PlotWidget)
        else plot
    )

    if plot_item.legend is None:
        plot_item.addLegend()

    X, Y, _, _ = downsample_for_plot(
        x=X,
        y=Y,
        threshold=threshold,
        points_per_decade=points_per_decade,
        log_space=True,
    )

    if len(X) == 0:
        return

    kwargs = {}

    if show_symbols:

        kwargs.update(
            {
                "symbol": "o",
                "symbolSize": symbol_size,
                "symbolBrush": color,
                "symbolPen": pg.mkPen(color=color),
            }
        )

    plot.plot(
        X,
        Y,
        pen=pg.mkPen(
            color=color,
            width=width,
            style=style,
        ),
        name=name,
        **kwargs,
    )
