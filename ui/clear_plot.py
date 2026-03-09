from pyqtgraph import PlotItem


def clear_plot(plot: PlotItem) -> None:
    """
    Очищает график pyqtgraph.
    """

    plot.clear()

    plot.setTitle("")
    plot.setLabel("bottom", "")
    plot.setLabel("left", "")
