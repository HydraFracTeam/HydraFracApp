import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotItem

def plot_debit(
    plot: PlotItem,
    t: np.ndarray,
    Q: np.ndarray,
    clear: bool = True,
) -> None:
    """
    Отрисовка графика дебита Q(t)
    """

    if clear:
        plot.clear()

    plot.setTitle("Дебит во времени")
    plot.setLabel("bottom", "Время, ч")
    plot.setLabel("left", "Дебит, м³/сут")
    plot.showGrid(x=True, y=True)

    mask = np.isfinite(t) & np.isfinite(Q)

    if not mask.any():
        return

    plot.plot(
        t[mask],
        Q[mask],
        pen=pg.mkPen(color=(50, 150, 50), width=2),
        name="Q(t)",
    )


