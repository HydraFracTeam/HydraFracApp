import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotItem

from ui.downsampling import downsample_for_plot


def plot_debit(
    plot: PlotItem,
    t: np.ndarray,
    Q: np.ndarray,
    Q_interpolated_mask: np.ndarray | None = None,
    Q_extrapolated_mask: np.ndarray | None = None,
    clear: bool = True,
):
    if clear:
        plot.clear()

    plot.setTitle("Дебит во времени")
    plot.setLabel("bottom", "Время, ч")
    plot.setLabel("left", "Дебит, м³/сут")
    plot.showGrid(x=True, y=True)

    if plot.legend is None:
        plot.addLegend()

    if len(t) == 0:
        return

    t, Q, interp_mask, extra_mask = downsample_for_plot(
        t,
        Q,
        Q_interpolated_mask,
        Q_extrapolated_mask,
    )

    plot.plot(
        t,
        Q,
        pen=pg.mkPen(color=(50,150,50), width=2),
        connect="finite",
        name="Q(t)",
    )

    if interp_mask is not None and np.any(interp_mask):

        plot.plot(
            t[interp_mask],
            Q[interp_mask],
            pen=None,
            symbol="o",
            symbolSize=2,
            symbolBrush=(255,165,0),
            name="Интерполировано",
        )

    if extra_mask is not None and np.any(extra_mask):

        plot.plot(
            t[extra_mask],
            Q[extra_mask],
            pen=None,
            symbol="o",
            symbolSize=2,
            symbolBrush=(80,120,255),
            name="Экстраполировано",
        )
