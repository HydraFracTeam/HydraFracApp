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
                               time: pd.Series,
                               pressure: pd.Series,
                               flow_rate: pd.Series,
                               checked_groups: Dict[str, bool],
                               validation_data: Optional[Dict] = None,
                               X_data: Optional[pd.Series] = None,
                               Y_data: Optional[pd.Series] = None,
                               show_calculated_XY: bool = False) -> None:
    """
    Отображает графики, сгруппированные по плоскостям отображения.
    
    Args:
        plot_widget: Виджет графика PyQtGraph
        dim_data: Безразмерные данные
        time: Временной ряд
        pressure: Давление
        flow_rate: Дебит
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
    has_dim = checked_groups.get('dimensionless', False) or checked_groups.get('cb_XY_plot', False)
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
            plot_widget.plot(time.values, pressure.values,
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
            plot_widget.plot(time.values, flow_rate.values,
                            pen=pg.mkPen(color=(50, 150, 50), width=2),
                            name="Q(t)", 
                            connect='finite')
        
        plot_widget.setTitle("Реальные параметры скважины")
        plot_widget.addLegend()
        return  # Реальные параметры в своем пространстве
    
    # ГРУППА 2: Безразмерные кривые - плоскость (X, pD/qD/tD/CD)
    # Все безразмерные кривые отображаются в плоскости X-Y
    if has_dim:
        # Используем X и Y из данных, если они есть, иначе используем расчётные
        if X_data is not None and Y_data is not None:
            # Преобразуем в numpy массивы (без ограничения снизу, так как не log-log)
            X = X_data.values.astype(float)
            Y = Y_data.values.astype(float)
            # Расчётные X и Y для сравнения (если нужно)
            X_calc = dim_data.X.astype(float)
            Y_calc = dim_data.Y.astype(float)
        else:
            # Используем только расчётные значения
            X = dim_data.X.astype(float)
            Y = dim_data.Y.astype(float)
            X_calc = None
            Y_calc = None
        
        # --- Проверка и нормализация диапазонов ---
        # Убираем NaN
        pD = pD.astype(float)
        qD = qD.astype(float)

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

        # Гарантируем, что диапазон данных корректен
        if np.allclose(np.nanmin(X), np.nanmax(X)) or np.allclose(np.nanmin(pD), np.nanmax(pD)):
            print("⚠️ Предупреждение: диапазон X или pD слишком узкий для отображения")

        plot_widget.setLogMode(x=False, y=False)
        plot_widget.setLabel('bottom', 'X (безразмерный фильтрационный параметр)')
        plot_widget.setLabel('left', 'Безразмерный параметр')
        plot_widget.setTitle("Безразмерные кривые МГРП")
        
        # Строим только выбранные графики
        if checked_groups.get('cb_dim_pD', False):
            # Используем отфильтрованные массивы X и pD
            mask = np.isfinite(X) & np.isfinite(pD)
            if np.any(mask):
                plot_widget.plot(X[mask], pD[mask],
                                pen=pg.mkPen(color=(200, 50, 50), width=2),
                                name="pD(X)",
                                connect='finite')
        
        if checked_groups.get('cb_dim_dpD', False):
            # Вычисляем производную на отфильтрованных данных
            Yc = np.clip(Y, 1e-30, None)
            # Для обычного графика используем производную по Y, а не по log(Y)
            dpdY = np.gradient(pD, Yc)
            mask = np.isfinite(X) & np.isfinite(dpdY)
            if np.any(mask):
                plot_widget.plot(X[mask], dpdY[mask],
                                pen=pg.mkPen(color=(150, 0, 150), width=2),
                                name="dpD/dY(X)",
                                connect='finite')
        
        if checked_groups.get('cb_dim_tD', False):
            # Используем отфильтрованные массивы X и Y
            mask = np.isfinite(X) & np.isfinite(Y)
            if np.any(mask):
                plot_widget.plot(X[mask], Y[mask],
                                pen=pg.mkPen(color=(0, 120, 200), width=2),
                                name="tD (Y)",
                                connect='finite')
        
        if checked_groups.get('cb_dim_CD', False):
            # Вычисляем CD на отфильтрованных данных
            Yc = np.clip(np.abs(Y), 1e-30, None)
            pD_clip = np.clip(np.abs(pD), 1e-30, None)
            
            # Для обычного графика используем производную по Y
            dpdY = np.gradient(pD_clip, Yc)
            CD = np.abs(Yc * dpdY)
            CD = np.clip(CD, 1e-10, 1e10)  # ограничиваем диапазон
            CD /= np.nanmax(CD) if np.nanmax(CD) != 0 else 1  # нормализация

            mask = np.isfinite(X) & np.isfinite(CD)
            if np.any(mask):
                plot_widget.plot(X[mask], CD[mask],
                                pen=pg.mkPen(color=(0, 180, 80), width=2),
                                name="CD(X)",
                                connect='finite')
        
        # Отображаем X-Y график (пары точек X-Y из данных), если установлен флаг
        if checked_groups.get('cb_XY_plot', False):
            if X_data is not None and Y_data is not None:
                # Используем исходные данные напрямую, без нормализации
                # Убеждаемся, что индексы совпадают
                X_raw = X_data.values.astype(float)
                Y_raw = Y_data.values.astype(float)
                
                # Проверяем, что данные имеют одинаковую длину
                min_len = min(len(X_raw), len(Y_raw))
                if min_len > 0:
                    X_raw = X_raw[:min_len]
                    Y_raw = Y_raw[:min_len]
                    
                    mask_xy = np.isfinite(X_raw) & np.isfinite(Y_raw)
                    if np.any(mask_xy):
                        # Убеждаемся, что у нас есть несколько точек
                        X_plot = X_raw[mask_xy]
                        Y_plot = Y_raw[mask_xy]
                        if len(X_plot) > 0:
                            plot_widget.plot(X_plot, Y_plot,
                                            pen=pg.mkPen(color=(100, 150, 255), width=2),
                                            symbol='o', symbolSize=5,
                                            name="X-Y (из данных)",
                                            connect='finite')
            elif X is not None and Y is not None:
                # Если данных нет, используем расчётные для X-Y графика
                # Но используем исходные значения до нормализации
                # Получаем их из dim_data напрямую
                X_raw = dim_data.X.astype(float)
                Y_raw = dim_data.Y.astype(float)
                
                # Проверяем, что данные имеют одинаковую длину
                min_len = min(len(X_raw), len(Y_raw))
                if min_len > 0:
                    X_raw = X_raw[:min_len]
                    Y_raw = Y_raw[:min_len]
                    
                    mask_xy = np.isfinite(X_raw) & np.isfinite(Y_raw)
                    if np.any(mask_xy):
                        X_plot = X_raw[mask_xy]
                        Y_plot = Y_raw[mask_xy]
                        if len(X_plot) > 0:
                            plot_widget.plot(X_plot, Y_plot,
                                            pen=pg.mkPen(color=(100, 150, 255), width=2),
                                            symbol='o', symbolSize=5,
                                            name="X-Y (расчётные)",
                                            connect='finite')
        
        # Отображаем расчётные X и Y, если установлен флаг и они отличаются от данных
        if show_calculated_XY and X_calc is not None and Y_calc is not None:
            # Проверяем, что расчётные значения действительно отличаются
            if not np.allclose(X, X_calc, rtol=1e-3) or not np.allclose(Y, Y_calc, rtol=1e-3):
                # Отображаем расчётные значения пунктирной линией
                mask_calc = np.isfinite(X_calc) & np.isfinite(Y_calc)
                if np.any(mask_calc):
                    plot_widget.plot(X_calc[mask_calc], Y_calc[mask_calc],
                                    pen=pg.mkPen(color=(200, 200, 0), width=1, 
                                                style=pg.QtCore.Qt.DashLine),
                                    name="Расчётные X и Y")
        
        # Добавляем эталонные кривые, если есть
        if validation_data:
            try:
                ref_dim = validation_data.get('ref_dim')
                if ref_dim:
                    pD_ref = ref_dim.pressure / (ref_dim.delta_p_i if ref_dim.delta_p_i != 0 else 1.0)
                    # Используем расчётные X из эталонных данных
                    ref_X = ref_dim.X.astype(float)
                    mask_rp = np.isfinite(ref_X) & np.isfinite(pD_ref)
                    if np.any(mask_rp):
                        plot_widget.plot(ref_X[mask_rp], pD_ref[mask_rp],
                                        pen=pg.mkPen(color=(120, 120, 120), width=2, 
                                                    style=pg.QtCore.Qt.DashLine),
                                        name="Эталон pD(X)")
            except Exception:
                pass
        
        plot_widget.addLegend()
        return  # Безразмерные кривые в своем пространстве
    
    # ГРУППА 3: Типовые кривые - плоскость (Y, pD)
    # Типовые кривые отображаются в плоскости Y-pD
    if has_type:
        plot_widget.setLogMode(x=False, y=False)
        plot_widget.setLabel('bottom', 'Y (безразмерный ёмкостной параметр)')
        plot_widget.setLabel('left', 'pD (безразмерное давление)')
        plot_widget.setTitle("Типовые кривые")
        
        # Используем Y из данных или расчётных значений для определения диапазона
        # Если типовые кривые выбраны отдельно (без безразмерных), используем dim_data.Y
        if Y_data is not None and len(Y_data) > 0:
            y_min = float(Y_data.min())
            y_max = float(Y_data.max())
        else:
            # Используем Y из dim_data
            y_min = float(np.min(dim_data.Y))
            y_max = float(np.max(dim_data.Y))
        
        # Используем линейную сетку вместо логарифмической
        y_ref = np.linspace(max(y_min, 1e-3), max(y_max, 1e2), 100)
        
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
            t = time.values
            G = (2.0 / np.sqrt(np.pi)) * np.sqrt(np.clip(t, 0.0, None))
            mask = ~np.isnan(G)
            if np.any(mask):
                plot_widget.plot(t[mask], G[mask],
                                pen=pg.mkPen(color=(100, 100, 200), width=2),
                                name="G-функция")
            return
        
        if checked_groups.get('cb_mbt', False):
            # Material Balance Time: плоскость (t_mb, Q)
            plot_widget.setLogMode(x=False, y=False)
            plot_widget.setLabel('bottom', 'Material Balance Time')
            plot_widget.setLabel('left', 'Дебит Q, м³/сут')
            plot_widget.setTitle("Material Balance Time")
            
            # Вычисляем MBT
            q0 = flow_rate.iloc[0] if len(flow_rate) > 0 else 1.0
            if q0 != 0:
                dt = np.gradient(time.values)
                cum = np.cumsum(flow_rate.values * dt)
                t_mb = cum / q0
                mask = (t_mb > 0) & (flow_rate.values > 0)
                if np.any(mask):
                    plot_widget.plot(t_mb[mask], flow_rate.values[mask],
                                    pen=pg.mkPen(color=(150, 100, 50), width=2),
                                    name="MBT")
            return
    
    # Если ничего не выбрано, просто очищаем график и показываем пустую область
    if not (has_real or has_dim or has_type or has_special):
        plot_widget.setLogMode(x=False, y=False)
        plot_widget.setLabel('bottom', 'X (безразмерный фильтрационный параметр)')
        plot_widget.setLabel('left', 'Безразмерный параметр')
        plot_widget.setTitle("Безразмерные кривые МГРП")
        plot_widget.showGrid(x=True, y=True)
        plot_widget.addLegend()
        return  # Просто показываем пустой график без данных


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
            ax.plot(dimensionless_data.Y, dimensionless_pressure, 
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
            ax.plot(dimensionless_data.Y, dimensionless_flow,
                     's-', color=self.colors['original'],
                      label='Безразмерный дебит', markersize=4)
        
        ax.set_xlabel('Y (безразмерный ёмкостной параметр)')
        ax.set_ylabel('Безразмерная величина')
        ax.set_title('Безразмерные кривые МГРП')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def plot_interpolation_results(self, original_data: DimensionlessParameters,
                                  interpolated_current_well_pressure: np.ndarray,
                                  interpolated_flow: np.ndarray,
                                  target_current_well_times: np.ndarray,
                                  method_name: str = 'Интерполяция') -> Figure:
        """Построение результатов интерполяции"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        pD_orig = original_data.pressure / original_data.delta_p_i
        ax.plot(original_data.Y, pD_orig, 'o-', color='black', 
                 label='Исходные данные', markersize=4)
        ax.plot(target_current_well_times, interpolated_current_well_pressure / original_data.delta_p_i,
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
        plot_widget.setLogMode(x=False, y=False)
        
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
def plot_dimensionless_analysis(current_well_time: pd.Series,
                               current_well_pressure: pd.Series,
                               current_well_flow_rate: pd.Series,
                               well_params: Dict[str, float],
                               plot_type: str = 'current_well_pressure') -> Figure:
    """Быстрое построение анализа безразмерных кривых"""
    dimensionless_data = convert_to_dimensionless_curves(
        current_well_time, current_well_pressure, current_well_flow_rate, well_params
    )
    plotter = DimensionlessPlotter()
    return plotter.plot_dimensionless_curves(dimensionless_data, plot_type)


def plot_extrapolation_comparison(current_well_time: pd.Series,
                                 current_well_pressure: pd.Series,
                                 current_well_flow_rate: pd.Series,
                                 well_params: Dict[str, float],
                                 future_current_well_times: np.ndarray,
                                 extrapolation_params: Dict[str, float],
                                 method: str = 'physics_constrained') -> Figure:
    """Сравнение экстраполяции"""
    dimensionless_data = convert_to_dimensionless_curves(
        current_well_time, current_well_pressure, current_well_flow_rate, well_params
    )
    
    extrapolated_current_well_pressure, extrapolated_flow = extrapolate_dimensionless_curves(
        current_well_time, current_well_pressure, current_well_flow_rate, well_params, future_current_well_times, extrapolation_params, method
    )
    
    plotter = DimensionlessPlotter()
    return plotter.plot_dimensionless_curves(dimensionless_data, 'pressure')


def plot_interpolation_comparison(
    current_well_time: pd.Series,
    current_well_pressure: pd.Series,
    current_well_flow_rate: pd.Series,
    well_params: Dict[str, float],
    target_current_well_times: np.ndarray,
    target_params: Dict[str, float],
    method: str = 'adaptive'
) -> Figure:
    """Сравнение методов интерполяции"""
    from helpers.dimensionless_interpolating import DimensionlessCurveInterpolator
    
    dimensionless_data = convert_to_dimensionless_curves(
        current_well_time, current_well_pressure, current_well_flow_rate, well_params
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
