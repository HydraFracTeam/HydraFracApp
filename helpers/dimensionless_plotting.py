"""
Модуль для построения графиков безразмерных кривых МГРП
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


class DimensionlessPlotter:
    """Класс для построения графиков безразмерных кривых"""
    
    def __init__(self):
        self.colors = {
            'bilinear': 'red',
            'linear': 'blue', 
            'pseudoradial': 'green',
            'interpolated': 'orange',
            'extrapolated': 'purple',
            'original': 'black'
        }
        
    def plot_dimensionless_curves(self, 
                                 dimensionless_data: DimensionlessParameters,
                                 plot_type: str = 'pressure',
                                 show_uncertainty: bool = False,
                                 uncertainty_data: Optional[Tuple[np.ndarray, np.ndarray]] = None) -> Figure:
        """
        Построение безразмерных кривых
        
        Args:
            dimensionless_data: Безразмерные данные
            plot_type: Тип графика ('pressure', 'flow_rate', 'both')
            show_uncertainty: Показывать ли неопределенность
            uncertainty_data: Данные неопределенности (mean, std)
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        if plot_type in ['pressure', 'both']:
            # Безразмерное давление
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
            # Безразмерный дебит
            dimensionless_flow = dimensionless_data.flow_rate / dimensionless_data.Q
            ax2 = ax.twinx() if plot_type == 'both' else ax
            ax2.loglog(dimensionless_data.Y, dimensionless_flow,
                      's-', color=self.colors['linear'],
                      label='Безразмерный дебит', markersize=4)
            
            if plot_type == 'both':
                ax2.set_ylabel('Безразмерный дебит', color=self.colors['linear'])
                ax2.tick_params(axis='y', labelcolor=self.colors['linear'])
        
        ax.set_ylabel('Ёмкостной параметр Y (безразмерный)')
        ax.set_xlabel('Безразмерное давление' if plot_type != 'both' else 'Безразмерное давление')
        ax.set_title('Безразмерные кривые МГРП')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        return fig
    
    def plot_type_curves_comparison(self, 
                                   dimensionless_data: DimensionlessParameters,
                                   type_curves: Dict[str, Dict],
                                   best_match: Optional[str] = None) -> Figure:
        """
        Сравнение с эталонными кривыми
        
        Args:
            dimensionless_data: Безразмерные данные
            type_curves: Библиотека эталонных кривых
            best_match: Лучшее совпадение
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # График давления
        dimensionless_pressure = dimensionless_data.pressure / dimensionless_data.delta_p_i
        ax1.loglog(dimensionless_data.Y, dimensionless_pressure, 
                  'ko-', label='Данные', markersize=6, linewidth=2)
        
        # График дебита
        dimensionless_flow = dimensionless_data.flow_rate / dimensionless_data.Q
        ax2.loglog(dimensionless_data.Y, dimensionless_flow,
                  'ko-', label='Данные', markersize=6, linewidth=2)
        
        # Добавляем эталонные кривые
        for i, (curve_id, curve_data) in enumerate(type_curves.items()):
            if i >= 5:  # Ограничиваем количество для читаемости
                break
                
            color = self.colors['bilinear'] if i % 3 == 0 else \
                   self.colors['linear'] if i % 3 == 1 else self.colors['pseudoradial']
            
            # Конвертируем время в безразмерный параметр Y для эталонных кривых
            # Используем те же параметры, что и для исходных данных
            Y_curve = (dimensionless_data.Q * dimensionless_data.B * curve_data['time']) / \
                     (24 * dimensionless_data.phi * dimensionless_data.c_t * 
                      dimensionless_data.h * dimensionless_data.L**2 * dimensionless_data.delta_p_i)
            
            # Давление
            ax1.loglog(Y_curve, curve_data['bilinear_pressure'] / 100,
                      '--', color=color, alpha=0.7, linewidth=1)
            
            # Дебит
            ax2.loglog(Y_curve, curve_data['bilinear_flow'] / 50,
                      '--', color=color, alpha=0.7, linewidth=1)
        
        # Выделяем лучшее совпадение
        if best_match and best_match in type_curves:
            curve_data = type_curves[best_match]
            # Конвертируем время в безразмерный параметр Y
            Y_best = (dimensionless_data.Q * dimensionless_data.B * curve_data['time']) / \
                    (24 * dimensionless_data.phi * dimensionless_data.c_t * 
                     dimensionless_data.h * dimensionless_data.L**2 * dimensionless_data.delta_p_i)
            
            ax1.loglog(Y_best, curve_data['bilinear_pressure'] / 100,
                      '-', color='red', linewidth=3, label='Лучшее совпадение')
            ax2.loglog(Y_best, curve_data['bilinear_flow'] / 50,
                      '-', color='red', linewidth=3, label='Лучшее совпадение')
        
        ax1.set_ylabel('Ёмкостной параметр Y (безразмерный)')
        ax1.set_xlabel('Безразмерное давление')
        ax1.set_title('Сравнение с эталонными кривыми (давление)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        ax2.set_ylabel('Ёмкостной параметр Y (безразмерный)')
        ax2.set_xlabel('Безразмерный дебит')
        ax2.set_title('Сравнение с эталонными кривыми (дебит)')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        plt.tight_layout()
        return fig
    
    def plot_interpolation_results(self, 
                                  original_data: DimensionlessParameters,
                                  interpolated_pressure: np.ndarray,
                                  interpolated_flow: np.ndarray,
                                  target_times: np.ndarray,
                                  method_name: str = 'Интерполяция') -> Figure:
        """
        Результаты интерполяции
        
        Args:
            original_data: Исходные данные
            interpolated_pressure: Интерполированное давление
            interpolated_flow: Интерполированный дебит
            target_times: Целевые временные точки
            method_name: Название метода
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Давление
        ax1.semilogy(original_data.t, original_data.pressure, 
                    'ko-', label='Исходные данные', markersize=6)
        ax1.semilogy(target_times, interpolated_pressure, 
                    'ro-', label=method_name, markersize=4)
        ax1.set_xlabel('Время, ч')
        ax1.set_ylabel('Давление, атм')
        ax1.set_title(f'Интерполяция давления - {method_name}')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Дебит
        ax2.semilogy(original_data.t, original_data.flow_rate, 
                    'ko-', label='Исходные данные', markersize=6)
        ax2.semilogy(target_times, interpolated_flow, 
                    'ro-', label=method_name, markersize=4)
        ax2.set_xlabel('Время, ч')
        ax2.set_ylabel('Дебит, м³/сут')
        ax2.set_title(f'Интерполяция дебита - {method_name}')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        plt.tight_layout()
        return fig
    
    def plot_extrapolation_results(self, 
                                  original_data: DimensionlessParameters,
                                  extrapolated_pressure: np.ndarray,
                                  extrapolated_flow: np.ndarray,
                                  future_times: np.ndarray,
                                  method_name: str = 'Экстраполяция') -> Figure:
        """
        Результаты экстраполяции
        
        Args:
            original_data: Исходные данные
            extrapolated_pressure: Экстраполированное давление
            extrapolated_flow: Экстраполированный дебит
            future_times: Будущие временные точки
            method_name: Название метода
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Давление
        ax1.semilogy(original_data.t, original_data.pressure, 
                    'ko-', label='Исходные данные', markersize=6)
        ax1.semilogy(future_times, extrapolated_pressure, 
                    'go-', label=method_name, markersize=4)
        ax1.set_xlabel('Время, ч')
        ax1.set_ylabel('Давление, атм')
        ax1.set_title(f'Экстраполяция давления - {method_name}')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Дебит
        ax2.semilogy(original_data.t, original_data.flow_rate, 
                    'ko-', label='Исходные данные', markersize=6)
        ax2.semilogy(future_times, extrapolated_flow, 
                    'go-', label=method_name, markersize=4)
        ax2.set_xlabel('Время, ч')
        ax2.set_ylabel('Дебит, м³/сут')
        ax2.set_title(f'Экстраполяция дебита - {method_name}')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        plt.tight_layout()
        return fig


class PyQtGraphDimensionlessPlotter:
    """PyQtGraph версия построителя безразмерных графиков"""
    
    def __init__(self):
        self.colors = {
            'bilinear': (255, 0, 0),      # Красный
            'linear': (0, 0, 255),        # Синий
            'pseudoradial': (0, 255, 0),  # Зеленый
            'interpolated': (255, 165, 0), # Оранжевый
            'extrapolated': (128, 0, 128), # Фиолетовый
            'original': (0, 0, 0)         # Черный
        }
    
    def create_dimensionless_plot(self, 
                                 plot_widget: PlotWidget,
                                 dimensionless_data: DimensionlessParameters,
                                 plot_type: str = 'pressure') -> None:
        """
        Создание графика безразмерных кривых в PyQtGraph
        
        Args:
            plot_widget: Виджет для отображения
            dimensionless_data: Безразмерные данные
            plot_type: Тип графика
        """
        plot_widget.clear()
        plot_widget.setLabel('left', 'Безразмерное давление' if plot_type == 'pressure' else 'Безразмерный дебит')
        plot_widget.setLabel('bottom', 'Ёмкостной параметр Y')
        plot_widget.setTitle('Безразмерные кривые МГРП')
        plot_widget.setLogMode(x=True, y=True)
        
        if plot_type == 'pressure':
            dimensionless_pressure = dimensionless_data.pressure / dimensionless_data.delta_p_i
            plot_widget.plot(dimensionless_data.Y, dimensionless_pressure,
                           pen=mkPen(color=self.colors['original'], width=2),
                           symbol='o', symbolSize=6,
                           name='Безразмерное давление')
        else:
            dimensionless_flow = dimensionless_data.flow_rate / dimensionless_data.Q
            plot_widget.plot(dimensionless_data.Y, dimensionless_flow,
                           pen=mkPen(color=self.colors['linear'], width=2),
                           symbol='s', symbolSize=6,
                           name='Безразмерный дебит')
    
    def add_type_curves(self, 
                       plot_widget: PlotWidget,
                       type_curves: Dict[str, Dict],
                       max_curves: int = 5) -> None:
        """
        Добавление эталонных кривых на график
        
        Args:
            plot_widget: Виджет для отображения
            type_curves: Библиотека эталонных кривых
            max_curves: Максимальное количество кривых
        """
        colors = [self.colors['bilinear'], self.colors['linear'], self.colors['pseudoradial']]
        
        for i, (curve_id, curve_data) in enumerate(type_curves.items()):
            if i >= max_curves:
                break
                
            color = colors[i % len(colors)]
            
            # Давление
            plot_widget.plot(curve_data['time'], curve_data['bilinear_pressure'] / 100,
                           pen=mkPen(color=color, width=1, style=2),  # Пунктир
                           name=f'Эталонная кривая {i+1}')
    
    def add_interpolation_results(self, 
                                 plot_widget: PlotWidget,
                                 target_times: np.ndarray,
                                 interpolated_pressure: np.ndarray,
                                 interpolated_flow: np.ndarray,
                                 plot_type: str = 'pressure') -> None:
        """
        Добавление результатов интерполяции
        
        Args:
            plot_widget: Виджет для отображения
            target_times: Целевые временные точки
            interpolated_pressure: Интерполированное давление
            interpolated_flow: Интерполированный дебит
            plot_type: Тип графика
        """
        if plot_type == 'pressure':
            plot_widget.plot(target_times, interpolated_pressure,
                           pen=mkPen(color=self.colors['interpolated'], width=2),
                           symbol='o', symbolSize=4,
                           name='Интерполированные данные')
        else:
            plot_widget.plot(target_times, interpolated_flow,
                           pen=mkPen(color=self.colors['interpolated'], width=2),
                           symbol='s', symbolSize=4,
                           name='Интерполированные данные')
    
    def add_extrapolation_results(self, 
                                 plot_widget: PlotWidget,
                                 future_times: np.ndarray,
                                 extrapolated_pressure: np.ndarray,
                                 extrapolated_flow: np.ndarray,
                                 plot_type: str = 'pressure') -> None:
        """
        Добавление результатов экстраполяции
        
        Args:
            plot_widget: Виджет для отображения
            future_times: Будущие временные точки
            extrapolated_pressure: Экстраполированное давление
            extrapolated_flow: Экстраполированный дебит
            plot_type: Тип графика
        """
        if plot_type == 'pressure':
            plot_widget.plot(future_times, extrapolated_pressure,
                           pen=mkPen(color=self.colors['extrapolated'], width=2),
                           symbol='^', symbolSize=4,
                           name='Экстраполированные данные')
        else:
            plot_widget.plot(future_times, extrapolated_flow,
                           pen=mkPen(color=self.colors['extrapolated'], width=2),
                           symbol='^', symbolSize=4,
                           name='Экстраполированные данные')


# Функции для удобного использования
def plot_dimensionless_analysis(time: pd.Series,
                               pressure: pd.Series,
                               flow_rate: pd.Series,
                               well_params: Dict[str, float],
                               plot_type: str = 'pressure') -> Figure:
    """Быстрое построение анализа безразмерных кривых"""
    # Конвертируем в безразмерные параметры
    dimensionless_data = convert_to_dimensionless_curves(
        time, pressure, flow_rate, well_params
    )
    
    # Создаем график
    plotter = DimensionlessPlotter()
    return plotter.plot_dimensionless_curves(dimensionless_data, plot_type)


def plot_interpolation_comparison(time: pd.Series,
                                 pressure: pd.Series,
                                 flow_rate: pd.Series,
                                 well_params: Dict[str, float],
                                 target_times: np.ndarray,
                                 target_params: Dict[str, float],
                                 method: str = 'rbf') -> Figure:
    """Сравнение методов интерполяции"""
    # Получаем интерполированные данные
    interpolated_pressure, interpolated_flow = interpolate_dimensionless_curves(
        time, pressure, flow_rate, well_params, target_times, target_params, method
    )
    
    # Конвертируем исходные данные
    dimensionless_data = convert_to_dimensionless_curves(
        time, pressure, flow_rate, well_params
    )
    
    # Создаем график
    plotter = DimensionlessPlotter()
    return plotter.plot_interpolation_results(
        dimensionless_data, interpolated_pressure, interpolated_flow, 
        target_times, f'Интерполяция ({method})'
    )


def plot_extrapolation_comparison(time: pd.Series,
                                 pressure: pd.Series,
                                 flow_rate: pd.Series,
                                 well_params: Dict[str, float],
                                 future_times: np.ndarray,
                                 extrapolation_params: Dict[str, float],
                                 method: str = 'physics_constrained') -> Figure:
    """Сравнение методов экстраполяции"""
    # Получаем экстраполированные данные
    extrapolated_pressure, extrapolated_flow = extrapolate_dimensionless_curves(
        time, pressure, flow_rate, well_params, future_times, extrapolation_params, method
    )
    
    # Конвертируем исходные данные
    dimensionless_data = convert_to_dimensionless_curves(
        time, pressure, flow_rate, well_params
    )
    
    # Создаем график
    plotter = DimensionlessPlotter()
    return plotter.plot_extrapolation_results(
        dimensionless_data, extrapolated_pressure, extrapolated_flow,
        future_times, f'Экстраполяция ({method})'
    )
