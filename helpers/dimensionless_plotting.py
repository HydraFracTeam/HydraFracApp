"""
Модуль для построения графиков безразмерных кривых МГРП
Поддерживает разные плоскости отображения для разных групп графиков
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from typing import Dict, List, Tuple, Optional, Union
import pyqtgraph as pg
from pyqtgraph import PlotWidget, mkPen, mkBrush
from helpers.dimensionless_analysis import (
    DimensionlessParameters, 
    convert_to_dimensionless_curves,
    interpolate_dimensionless_curves,
    extrapolate_dimensionless_curves,
    create_dimensionless_type_curves
)


def plot_dimensionless_grouped(plot_widget: PlotWidget,
                               dim_data: DimensionlessParameters,
                               current_well_time: pd.Series,
                               current_well_pressure: pd.Series,
                               current_well_flow_rate: pd.Series,
                               checked_groups: Dict[str, bool],
                               validation_data: Optional[Dict] = None) -> None:
    """
    Отображает графики, сгруппированные по плоскостям отображения.
    
    Args:
        plot_widget: Виджет графика PyQtGraph
        dim_data: Безразмерные данные
        current_well_time: Временной ряд
        current_well_pressure: Давление
        current_well_flow_rate: Дебит
        checked_groups: Словарь с флагами выбранных групп:
            - 'real_params': Реальные параметры (P(t), Q(t))
            - 'dimensionless': Безразмерные (pD, dpD/dlogY, tD, CD)
            - 'type_curves': Типовые кривые
            - 'special': Специальные пространства (G-функция, MBT)
        validation_data: Данные для валидации (опционально)
    """
    plot_widget.clear()
    
    # Определяем, какие группы выбраны
    has_real = checked_groups.get('real_params', False)
    has_dim = checked_groups.get('dimensionless', False)
    has_type = checked_groups.get('type_curves', False)
    has_special = checked_groups.get('special', False)
    
    # Безразмерные величины
    pD = dim_data.pressure / (dim_data.delta_p_i if dim_data.delta_p_i != 0 else 1.0)
    qD = dim_data.flow_rate / (dim_data.Q if dim_data.Q != 0 else 1.0)
    
    # ГРУППА 1: Реальные параметры - плоскость (t, P) или (t, Q)
    # Обычные оси (не логарифмические)
    if has_real:
        plot_widget.setLogMode(x=False, y=False)
        plot_widget.setLabel('bottom', 'Время, ч')
        
        if checked_groups.get('cb_real_p', False):
            plot_widget.setLabel('left', 'Давление, атм')
            # Используем connect='finite' для правильного отображения пропусков
            plot_widget.plot(current_well_time.values, current_well_pressure.values,
                            pen=pg.mkPen(color=(200, 50, 50), width=2),
                            name="P(t)", 
                            connect='finite')
        
        if checked_groups.get('cb_real_q', False):
            if checked_groups.get('cb_real_p', False):
                # Если уже есть давление, используем правую ось или переключаем
                plot_widget.setLabel('left', 'Давление / Дебит')
            else:
                plot_widget.setLabel('left', 'Дебит, м³/сут')
            # Используем connect='finite' для правильного отображения пропусков
            plot_widget.plot(current_well_time.values, current_well_flow_rate.values,
                            pen=pg.mkPen(color=(50, 150, 50), width=2),
                            name="Q(t)", 
                            connect='finite')
        
        plot_widget.setTitle("Реальные параметры скважины")
        plot_widget.addLegend()
        return  # Реальные параметры в своем пространстве
    
    # ГРУППА 2: Безразмерные кривые - плоскость log-log (X, pD/qD/tD/CD)
    # Все безразмерные кривые отображаются в log-log плоскости X-Y
    if has_dim:
                # --- Проверка и нормализация диапазонов ---
        # Убираем нули, NaN, отрицательные
        X = np.clip(dim_data.X.astype(float), 1e-12, None)
        Y = np.clip(dim_data.Y.astype(float), 1e-12, None)
        pD = np.clip(pD.astype(float), 1e-12, None)
        qD = np.clip(qD.astype(float), 1e-12, None)

        # Нормализация к 1 при необходимости (чтобы избежать вылетов)
        def normalize_if_flat(arr):
            rng = np.nanmax(arr) - np.nanmin(arr)
            if not np.isfinite(rng) or rng < 1e-6:
                arr = arr / (np.nanmax(arr) if np.nanmax(arr) != 0 else 1.0)
            return arr

        X = normalize_if_flat(X)
        Y = normalize_if_flat(Y)
        pD = normalize_if_flat(pD)
        qD = normalize_if_flat(qD)

        # Для производных – фильтруем шумы и NaN
        if np.any(np.isnan(pD)) or np.any(np.isnan(Y)) or np.any(np.isnan(qD)):
            mask_valid = (~np.isnan(pD)) & (~np.isnan(Y)) & (~np.isnan(qD))
            pD = pD[mask_valid]
            qD = qD[mask_valid]
            Y = Y[mask_valid]
            X = X[mask_valid]

        # Гарантируем, что диапазон данных не коллапсирует в логарифме
        if np.allclose(np.nanmin(X), np.nanmax(X)) or np.allclose(np.nanmin(pD), np.nanmax(pD)):
            print("⚠️ Предупреждение: диапазон X или pD слишком узкий для log-log отображения")

        plot_widget.setLogMode(x=True, y=True)
        plot_widget.setLabel('bottom', 'X (безразмерный фильтрационный параметр)')
        plot_widget.setLabel('left', 'Безразмерный параметр')
        plot_widget.setTitle("Безразмерные кривые МГРП (log-log)")
        
        if checked_groups.get('cb_dim_pD', False):
            # Используем отфильтрованные массивы X и pD
            mask = (X > 0) & (pD > 0) & np.isfinite(X) & np.isfinite(pD)
            if np.any(mask):
                plot_widget.plot(X[mask], pD[mask],
                                pen=pg.mkPen(color=(200, 50, 50), width=2),
                                name="pD(X)",
                                connect='finite')
        
        if checked_groups.get('cb_dim_dpD', False):
            # Вычисляем производную на отфильтрованных данных
            Yc = np.clip(Y, 1e-30, None)
            dpdlogY = np.gradient(pD, np.log10(Yc))
            mask = (X > 0) & np.isfinite(X) & np.isfinite(dpdlogY)
            if np.any(mask):
                plot_widget.plot(X[mask], dpdlogY[mask],
                                pen=pg.mkPen(color=(150, 0, 150), width=2),
                                name="dpD/dlogY(X)",
                                connect='finite')
        
        if checked_groups.get('cb_dim_tD', False):
            # Используем отфильтрованные массивы X и Y
            mask = (X > 0) & (Y > 0) & np.isfinite(X) & np.isfinite(Y)
            if np.any(mask):
                plot_widget.plot(X[mask], Y[mask],
                                pen=pg.mkPen(color=(0, 120, 200), width=2),
                                name="tD (Y)",
                                connect='finite')
        
        if checked_groups.get('cb_dim_CD', False):
            # Вычисляем CD на отфильтрованных данных
            Yc = np.clip(Y, 1e-30, None)
            pD_clip = np.clip(pD, 1e-30, None)
            
            dpdlogY = np.gradient(np.log10(pD_clip), np.log10(Yc))
            CD = np.abs(Yc * dpdlogY)
            CD = np.clip(CD, 1e-10, 1e10)  # ограничиваем диапазон
            CD /= np.nanmax(CD) if np.nanmax(CD) != 0 else 1  # нормализация

            mask = (X > 0) & np.isfinite(X) & np.isfinite(CD)
            if np.any(mask):
                plot_widget.plot(X[mask], CD[mask],
                                pen=pg.mkPen(color=(0, 180, 80), width=2),
                                name="CD(X)",
                                connect='finite')
        
        # Добавляем эталонные кривые, если есть
        if validation_data:
            try:
                ref_dim = validation_data.get('ref_dim')
                if ref_dim:
                    pD_ref = ref_dim.pressure / (ref_dim.delta_p_i if ref_dim.delta_p_i != 0 else 1.0)
                    mask_rp = (~np.isnan(ref_dim.X)) & (~np.isnan(pD_ref)) & (ref_dim.X > 0) & (pD_ref > 0)
                    if np.any(mask_rp):
                        plot_widget.plot(ref_dim.X[mask_rp], pD_ref[mask_rp],
                                        pen=pg.mkPen(color=(120, 120, 120), width=2, 
                                                    style=pg.QtCore.Qt.DashLine),
                                        name="Эталон pD(X)")
            except Exception:
                pass
        
        plot_widget.addLegend()
        return  # Безразмерные кривые в своем пространстве
    
    # ГРУППА 3: Типовые кривые - плоскость log-log (Y, pD)
    # Типовые кривые отображаются в log-log плоскости Y-pD
    if has_type:
        plot_widget.setLogMode(x=True, y=True)
        plot_widget.setLabel('bottom', 'Y (безразмерный ёмкостной параметр)')
        plot_widget.setLabel('left', 'pD (безразмерное давление)')
        plot_widget.setTitle("Типовые кривые (log-log)")
        
        y_ref = np.logspace(-3, 2, 100)
        
        if checked_groups.get('cb_type_gry', False):
            curve = 1.2 / (y_ref ** 0.5)
            plot_widget.plot(y_ref, curve,
                            pen=pg.mkPen(color=(120, 120, 120, 160), width=1, 
                                        style=pg.QtCore.Qt.DashLine),
                            name="Gringarten & Ramey (прибл.)")
        
        if checked_groups.get('cb_type_cinco', False):
            curve = 0.9 / (y_ref ** 0.4)
            plot_widget.plot(y_ref, curve,
                            pen=pg.mkPen(color=(120, 120, 120, 160), width=1, 
                                        style=pg.QtCore.Qt.DotLine),
                            name="Cinco-Ley & Samaniego (прибл.)")
        
        if checked_groups.get('cb_type_valko', False):
            curve = 0.7 / (y_ref ** 0.3)
            plot_widget.plot(y_ref, curve,
                            pen=pg.mkPen(color=(120, 120, 120, 160), width=1),
                            name="Valkó & Economides (прибл.)")
        
        plot_widget.addLegend()
        return  # Типовые кривые в своем пространстве
    
    # ГРУППА 4: Специальные пространства - разные плоскости в зависимости от типа
    if has_special:
        if checked_groups.get('cb_gfunc', False):
            # G-функция Nolte: плоскость (t, G(t))
            plot_widget.setLogMode(x=False, y=False)
            plot_widget.setLabel('bottom', 'Время, ч')
            plot_widget.setLabel('left', 'G(t)')
            plot_widget.setTitle("G-функция Nolte")
            
            # Вычисляем G-функцию
            t = current_well_time.values
            G = (2.0 / np.sqrt(np.pi)) * np.sqrt(np.clip(t, 0.0, None))
            mask = ~np.isnan(G)
            if np.any(mask):
                plot_widget.plot(t[mask], G[mask],
                                pen=pg.mkPen(color=(100, 100, 200), width=2),
                                name="G-функция")
            return
        
        if checked_groups.get('cb_mbt', False):
            # Material Balance Time: плоскость (t_mb, Q)
            plot_widget.setLogMode(x=True, y=True)
            plot_widget.setLabel('bottom', 'Material Balance Time')
            plot_widget.setLabel('left', 'Дебит Q, м³/сут')
            plot_widget.setTitle("Material Balance Time")
            
            # Вычисляем MBT
            q0 = current_well_flow_rate.iloc[0] if len(current_well_flow_rate) > 0 else 1.0
            if q0 != 0:
                dt = np.gradient(current_well_time.values)
                cum = np.cumsum(current_well_flow_rate.values * dt)
                t_mb = cum / q0
                mask = (t_mb > 0) & (current_well_flow_rate.values > 0)
                if np.any(mask):
                    plot_widget.plot(t_mb[mask], current_well_flow_rate.values[mask],
                                    pen=pg.mkPen(color=(150, 100, 50), width=2),
                                    name="MBT")
            return
    
    # Если ничего не выбрано, показываем базовый безразмерный график
    plot_widget.setLogMode(x=True, y=True)
    plot_widget.setLabel('bottom', 'X (безразмерный фильтрационный параметр)')
    plot_widget.setLabel('left', 'pD (безразмерное давление)')
    plot_widget.setTitle("Безразмерные кривые МГРП")
    
    # Пересчитываем pD для fallback (без фильтрации)
    pD_fallback = dim_data.pressure / (dim_data.delta_p_i if dim_data.delta_p_i != 0 else 1.0)
    mask = (~np.isnan(dim_data.X)) & (~np.isnan(pD_fallback)) & (dim_data.X > 0) & (pD_fallback > 0) & np.isfinite(dim_data.X) & np.isfinite(pD_fallback)
    if np.any(mask):
        plot_widget.plot(dim_data.X[mask], pD_fallback[mask],
                        pen=pg.mkPen(color=(200, 50, 50), width=2),
                        name="pD(X)",
                        connect='finite')
    plot_widget.addLegend()
    plot_widget.showGrid(x=True, y=True)


# Классы и функции для matplotlib (оставляем для совместимости)
class DimensionlessPlotter:
    """Класс для построения графиков с использованием matplotlib"""
    def __init__(self):
        self.colors = {
            'bilinear': 'red',
            'linear': 'blue', 
            'pseudoradial': 'green',
            'interpolated': 'orange',
            'extrapolated': 'purple',
            'original': 'black'
        }
        
    def plot_dimensionless_curves(self, dimensionless_data: DimensionlessParameters,
                                 plot_type: str = 'pressure',
                                 show_uncertainty: bool = False,
                                 uncertainty_data: Optional[Tuple[np.ndarray, np.ndarray]] = None) -> Figure:
        """Построение безразмерных кривых с matplotlib"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        if plot_type in ['pressure', 'both']:
            dimensionless_pressure = dimensionless_data.pressure / dimensionless_data.delta_p_i
            ax.loglog(dimensionless_data.Y, dimensionless_pressure, 
                     'o-', color=self.colors['original'], 
                     label='Безразмерное давление', markersize=4)
            
            if show_uncertainty and uncertainty_data is not None:
                mean, std = uncertainty_data
                ax.fill_between(dimensionless_data.Y, 
                              mean - 2*std, mean + 2*std,
                              alpha=0.3, color=self.colors['interpolated'],
                              label='95% доверительный интервал')
        
        if plot_type in ['flow_rate', 'both']:
            dimensionless_flow = dimensionless_data.flow_rate / dimensionless_data.Q
            ax.loglog(dimensionless_data.Y, dimensionless_flow,
                     's-', color=self.colors['original'],
                      label='Безразмерный дебит', markersize=4)
        
        ax.set_xlabel('Y (безразмерный ёмкостной параметр)')
        ax.set_ylabel('Безразмерная величина')
        ax.set_title('Безразмерные кривые МГРП')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def plot_interpolation_results(self, original_data: DimensionlessParameters,
                                  interpolated_pressure: np.ndarray,
                                  interpolated_flow: np.ndarray,
                                  target_times: np.ndarray,
                                  method_name: str = 'Интерполяция') -> Figure:
        """Построение результатов интерполяции"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        pD_orig = original_data.pressure / original_data.delta_p_i
        ax.loglog(original_data.Y, pD_orig, 'o-', color='black', 
                 label='Исходные данные', markersize=4)
        ax.loglog(target_times, interpolated_pressure / original_data.delta_p_i,
                 '--', color='orange', label=f'{method_name} (давление)', linewidth=2)
        
        ax.set_xlabel('Y (безразмерный ёмкостной параметр)')
        ax.set_ylabel('pD (безразмерное давление)')
        ax.set_title('Сравнение интерполяции')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return fig


class PyQtGraphDimensionlessPlotter:
    """Класс для построения графиков с использованием PyQtGraph"""
    def __init__(self):
        self.colors = {
            'original': (0, 0, 255, 180),
            'interpolated': (255, 165, 0, 180),
            'extrapolated': (128, 0, 128, 180)
        }
    
    def create_dimensionless_plot(self, plot_widget: PlotWidget,
                                 dimensionless_data: DimensionlessParameters,
                                 plot_type: str = 'pressure') -> None:
        """Создание безразмерного графика в PyQtGraph"""
        plot_widget.clear()
        plot_widget.setLabel('bottom', 'X (безразмерный фильтрационный параметр)')
        plot_widget.setLabel('left', 'Y (безразмерный ёмкостной параметр)')
        plot_widget.setTitle('Безразмерные кривые МГРП')
        plot_widget.setLogMode(x=True, y=True)
        
        try:
            pD = dimensionless_data.pressure / dimensionless_data.delta_p_i if dimensionless_data.delta_p_i != 0 else np.zeros_like(dimensionless_data.pressure)
            qD = dimensionless_data.flow_rate / (dimensionless_data.Q if dimensionless_data.Q != 0 else 1.0)
            values = pD if plot_type == 'pressure' else qD
            
            vmin, vmax = np.nanmin(values), np.nanmax(values)
            if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
                vmin, vmax = 0.0, 1.0
            
            cmap = pg.colormap.get('CET-L4') if hasattr(pg, 'colormap') else None
            brushes = None
            if cmap is not None:
                colors = cmap.map((values - vmin) / (vmax - vmin), mode='qcolor')
                brushes = colors
            
            spots = [{"pos": (float(x), float(y)), "brush": (brushes[i] if brushes is not None else (0, 0, 255, 180)), "size": 7} 
                     for i, (x, y) in enumerate(zip(dimensionless_data.X, dimensionless_data.Y))]
            scatter = pg.ScatterPlotItem()
            scatter.addPoints(spots)
            plot_widget.addItem(scatter)
        except Exception:
            plot_widget.plot(dimensionless_data.X, dimensionless_data.Y, 
                           pen=mkPen(color=self.colors['original'], width=2), 
                           name='Траектория')


# Функции для удобного использования
def plot_dimensionless_analysis(time: pd.Series,
                               pressure: pd.Series,
                               flow_rate: pd.Series,
                               well_params: Dict[str, float],
                               plot_type: str = 'pressure') -> Figure:
    """Быстрое построение анализа безразмерных кривых"""
    dimensionless_data = convert_to_dimensionless_curves(
        time, pressure, flow_rate, well_params
    )
    plotter = DimensionlessPlotter()
    return plotter.plot_dimensionless_curves(dimensionless_data, plot_type)


def plot_extrapolation_comparison(time: pd.Series,
                                 pressure: pd.Series,
                                 flow_rate: pd.Series,
                                 well_params: Dict[str, float],
                                 future_times: np.ndarray,
                                 extrapolation_params: Dict[str, float],
                                 method: str = 'physics_constrained') -> Figure:
    """Сравнение экстраполяции"""
    dimensionless_data = convert_to_dimensionless_curves(
        time, pressure, flow_rate, well_params
    )
    
    extrapolated_pressure, extrapolated_flow = extrapolate_dimensionless_curves(
        time, pressure, flow_rate, well_params, future_times, extrapolation_params, method
    )
    
    plotter = DimensionlessPlotter()
    return plotter.plot_dimensionless_curves(dimensionless_data, 'pressure')


def plot_interpolation_comparison(
    time: pd.Series,
    pressure: pd.Series,
    flow_rate: pd.Series,
    well_params: Dict[str, float],
    target_times: np.ndarray,
    target_params: Dict[str, float],
    method: str = 'adaptive'
) -> Figure:
    """Сравнение методов интерполяции"""
    from helpers.dimensionless_interpolating import DimensionlessCurveInterpolator
    
    dimensionless_data = convert_to_dimensionless_curves(
        time, pressure, flow_rate, well_params
    )

    skin = target_params.get("Skin", well_params.get('skin', 0.0))
    N = target_params.get("N", well_params.get('N', 1))
    aL = target_params.get("a_L", well_params.get('a_L', 0.1))
    
    param_grid = np.array([[skin, N, aL]])
    Y_grid = np.asarray(dimensionless_data.Y)
    P_curves = np.asarray([dimensionless_data.pressure / dimensionless_data.delta_p_i])

    interp = DimensionlessCurveInterpolator(
        methods=('linear', 'rbf', 'gp'),
        constraints=dict(monotonic=True, positive=True, smooth=True, clip_range=(0, 5))
    )
    interp.fit(param_grid, Y_grid, P_curves)

    interpolated_curve = interp.predict(skin, N, aL)

    plotter = DimensionlessPlotter()
    fig = plotter.plot_dimensionless_curves(dimensionless_data, 'pressure')
    ax = fig.axes[0]
    ax.loglog(interpolated_curve.index.values, interpolated_curve.values,
              '--', color='orange', label='Интерполированная кривая', linewidth=2)
    ax.legend()

    return fig
