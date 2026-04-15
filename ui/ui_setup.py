"""
Модуль для наполнения UI компонентов приложения.
Работает ТОЛЬКО с элементами, созданными в main_ui.ui
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPalette, QColor

import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock

from ui.ui import Ui_MainWindow

# Тёмная тема для графиков
BG_COLOR = '#1e1e1e'
TEXT_COLOR = '#cccccc'
AXIS_COLOR = '#888888'
DOCK_LABEL_BG = '#3a3a3a'
DOCK_LABEL_FG = '#cccccc'
DOCK_LABEL_BORDER = '#555555'

def _make_dock(name: str, title: str, size=(500, 300), log_x=False, log_y=False) -> tuple[Dock, pg.PlotWidget]:
    """Создаёт док с PlotWidget."""
    plot = pg.PlotWidget()
    plot.showGrid(x=True, y=True)
    plot.setBackground(BG_COLOR)
    if log_x:
        plot.setLogMode(x=True)
    if log_y:
        plot.setLogMode(y=True)

    dock = Dock(name, size=size)
    dock.addWidget(plot)
    return dock, plot


def setup_dock_area(app) -> None:
    """
    Создаёт DockArea в plot_dock контейнере из .ui
    и 4 дока: P(t), Q(t), XY, Burde.
    """
    container = app.ui.plot_dock
    if container is None:
        raise RuntimeError("plot_dock widget not found in UI")

    # Создаём DockArea
    dock_area = DockArea()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(dock_area)
    app.ui.dock_area = dock_area

    # --- Док: Давление P(t) ---
    dock_p, p_plot = _make_dock("P(t) — Давление", "P(t)", size=(500, 300))
    p_plot.setLabel('left', 'Давление, кгс/см²', color=TEXT_COLOR)
    p_plot.setLabel('bottom', 'Время, ч', color=TEXT_COLOR)
    p_plot.getAxis('left').setPen(AXIS_COLOR)
    p_plot.getAxis('bottom').setPen(AXIS_COLOR)
    p_plot.getAxis('left').setTextPen(TEXT_COLOR)
    p_plot.getAxis('bottom').setTextPen(TEXT_COLOR)

    app.ui.dock_pressure = dock_p
    app.ui.plot_pressure = p_plot.getPlotItem()

    # --- Док: Дебит Q(t) ---
    dock_q, q_plot = _make_dock("Q(t) — Дебит", "Q(t)", size=(500, 300))
    q_plot.setLabel('left', 'Дебит, м³/сут', color=TEXT_COLOR)
    q_plot.setLabel('bottom', 'Время, ч', color=TEXT_COLOR)
    q_plot.getAxis('left').setPen(AXIS_COLOR)
    q_plot.getAxis('bottom').setPen(AXIS_COLOR)
    q_plot.getAxis('left').setTextPen(TEXT_COLOR)
    q_plot.getAxis('bottom').setTextPen(TEXT_COLOR)

    app.ui.dock_debit = dock_q
    app.ui.plot_debit = q_plot.getPlotItem()

    # --- Док: Безразмерные X-Y ---
    dock_xy, xy_plot = _make_dock("X-Y (log-log)", "XY", size=(500, 300), log_x=True, log_y=True)
    xy_plot.setLabel('left', 'Y', color=TEXT_COLOR)
    xy_plot.setLabel('bottom', 'X', color=TEXT_COLOR)
    xy_plot.getAxis('left').setPen(AXIS_COLOR)
    xy_plot.getAxis('bottom').setPen(AXIS_COLOR)
    xy_plot.getAxis('left').setTextPen(TEXT_COLOR)
    xy_plot.getAxis('bottom').setTextPen(TEXT_COLOR)

    app.ui.dock_xy = dock_xy
    app.ui.plot_xy = xy_plot.getPlotItem()

    # --- Док: Производная Бурде ---
    dock_b, b_plot = _make_dock("Бурде (log-log)", "Burde", size=(500, 300), log_x=True, log_y=True)
    b_plot.setLabel('left', "d(ΔP)/d(ln t)", color=TEXT_COLOR)
    b_plot.setLabel('bottom', 'Время, ч', color=TEXT_COLOR)
    b_plot.getAxis('left').setPen(AXIS_COLOR)
    b_plot.getAxis('bottom').setPen(AXIS_COLOR)
    b_plot.getAxis('left').setTextPen(TEXT_COLOR)
    b_plot.getAxis('bottom').setTextPen(TEXT_COLOR)

    app.ui.dock_burde = dock_b
    app.ui.plot_burde = b_plot.getPlotItem()
    
    
    dock_area.addDock(dock_p)
    dock_area.addDock(dock_q, 'right', dock_p)
    dock_area.addDock(dock_xy, 'bottom', dock_p)
    dock_area.addDock(dock_b, 'bottom', dock_q)

    # Скрываем все доки при старте (отложенно, чтобы DockArea успел проинициализироваться)
    for d in [dock_q, dock_xy, dock_b]:
        QTimer.singleShot(0, d.hide)
