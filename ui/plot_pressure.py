import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotItem

from ui.downsampling import downsample_for_plot


def plot_pressure(
    plot: PlotItem,
    t: np.ndarray,
    P: np.ndarray,
    P_interpolated_mask: np.ndarray | None = None,
    P_extrapolated_mask: np.ndarray | None = None,
    clear: bool = True,
):
    if clear:
        plot.clear()

    plot.setTitle("Давление во времени")
    plot.setLabel("bottom", "Время, ч")
    plot.setLabel("left", "Давление, кгс/см²")
    plot.getAxis("bottom").enableAutoSIPrefix(False)
    plot.getAxis("left").enableAutoSIPrefix(False)
    plot.showGrid(x=True, y=True)

    if plot.legend is None:
        plot.addLegend()

    if len(t) == 0:
        return

    t, P, interp_mask, extra_mask = downsample_for_plot(
        t,
        P,
        P_interpolated_mask,
        P_extrapolated_mask,
    )

    plot.plot(
        t,
        P,
        pen=pg.mkPen(color=(200,50,50), width=2),
        connect="finite",
        name="P(t)",
    )

    if interp_mask is not None and np.any(interp_mask):

        plot.plot(
            t[interp_mask],
            P[interp_mask],
            pen=None,
            symbol="o",
            symbolSize=2,
            symbolBrush=(255,165,0),
            name="Интерполировано",
        )

    if extra_mask is not None and np.any(extra_mask):

        plot.plot(
            t[extra_mask],
            P[extra_mask],
            pen=None,
            symbol="o",
            symbolSize=2,
            symbolBrush=(80,120,255),
            name="Экстраполировано",
        )
