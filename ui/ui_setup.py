"""
Модуль для наполнения UI компонентов приложения.
Работает ТОЛЬКО с элементами, созданными в main_ui.ui
"""
from PySide6.QtWidgets import ( QMainWindow,
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableView
)


from ui.ui import Ui_MainWindow
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout


def setup_add_interface(app: Ui_MainWindow) -> None:
    """
    Инициализация динамических элементов UI:
    - графики (pyqtgraph)
    - таблица данных
    """

    setup_timeseries_tab(app)
    setup_type_curves_tab(app)


# ------------------------------------------------------------------
# Безразмерные кривые
# ------------------------------------------------------------------


def attach_pg_to_widget(container: QMainWindow) -> pg.PlotItem:
    """
    Встраивает pyqtgraph в QWidget из .ui
    и возвращает PlotItem для рисования
    """
    if container is None:
        raise RuntimeError("Graph container widget not found")

    layout = container.layout()
    if layout is None:
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

    plot_widget = pg.PlotWidget()
    plot_widget.showGrid(x=True, y=True)

    layout.addWidget(plot_widget)

    return plot_widget.getPlotItem()


def setup_timeseries_tab(app: Ui_MainWindow) -> None:
    app.ui.p_graphic = attach_pg_to_widget(app.ui.p_graphic)
    app.ui.q_graphic = attach_pg_to_widget(app.ui.q_graphic)
    app.ui.dim_plot = attach_pg_to_widget(app.ui.dim_plot)


# ------------------------------------------------------------------
# Эталонные кривые
# ------------------------------------------------------------------

def setup_type_curves_tab(app: QMainWindow) -> None:
    placeholder = app.findChild(
        QWidget, "type_curves_plot_placeholder"
    )

    layout = placeholder.layout()
    if layout is None:
        layout = QVBoxLayout(placeholder)

    app.ui.type_curves_widget = pg.PlotWidget()
    app.ui.type_curves_widget.setLogMode(True, True)
    app.ui.type_curves_widget.showGrid(x=True, y=True)
    app.ui.type_curves_widget.setLabel('left', 'Дебит, м³/сут')
    app.ui.type_curves_widget.setLabel('bottom', 'Время, ч')

    layout.addWidget(app.ui.type_curves_widget)

