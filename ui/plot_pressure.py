import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotItem


def plot_pressure(
    plot: PlotItem,
    t: np.ndarray,
    P: np.ndarray,
    P_interpolated_mask: np.ndarray | None = None,
    P_extrapolated_mask: np.ndarray | None = None,
    clear: bool = True,
) -> None:

    if clear:
        plot.clear()

    plot.setTitle("Давление во времени")
    plot.setLabel("bottom", "Время, ч")
    plot.setLabel("left", "Давление")
    plot.showGrid(x=True, y=True)
    # plot.setLogMode(x=True, y=False)

    if plot.legend is None:
        plot.addLegend()

    if len(t) == 0:
        return

    # основная линия давления (с разрывами на NaN)
    plot.plot(
        t,
        P,
        pen=pg.mkPen(color=(200, 50, 50), width=2),
        connect="finite",
        name="P(t)",
    )

    finite_mask = np.isfinite(t) & np.isfinite(P)

    # интерполированные точки
    if P_interpolated_mask is not None and np.any(P_interpolated_mask):

        interp_mask = P_interpolated_mask & finite_mask

        plot.plot(
            t[interp_mask],
            P[interp_mask],
            pen=None,
            symbol="o",
            symbolSize=8,
            symbolBrush=(255, 165, 0),
            name="Интерполировано",
        )

    # экстраполированные точки
    if P_extrapolated_mask is not None and np.any(P_extrapolated_mask):

        extra_mask = P_extrapolated_mask & finite_mask

        plot.plot(
            t[extra_mask],
            P[extra_mask],
            pen=None,
            symbol="t",
            symbolSize=9,
            symbolBrush=(80, 120, 255),
            name="Экстраполировано",
        )
