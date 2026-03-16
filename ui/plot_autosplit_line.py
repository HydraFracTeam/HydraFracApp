import pyqtgraph as pg
from PySide6.QtCore import Qt


def plot_autosplit_line(
    plot: pg.PlotItem,
    split_time: float,
    split_pressure: float,
) -> None:
    """
    Draw vertical autosplit line and marker on pressure plot.

    Parameters
    ----------
    plot : pg.PlotItem
        Target pyqtgraph plot.

    split_time : float
        Time coordinate of split point.

    split_pressure : float
        Pressure value at split point.
    """

    if plot is None:
        return

    line = pg.InfiniteLine(
        pos=split_time,
        angle=90,
        pen=pg.mkPen(color="yellow", width=2, style=Qt.DashLine),
        label="AUTO SPLIT",
        labelOpts={
            "position": 0.95,
            "color": "yellow",
            "fill": (0, 0, 0, 100),
        },
    )

    plot.addItem(line)

    scatter = pg.ScatterPlotItem(
        x=[split_time],
        y=[split_pressure],
        pen=pg.mkPen(color="yellow", width=2),
        brush=pg.mkBrush(color="yellow"),
        size=10,
        symbol="o",
    )

    plot.addItem(scatter)
