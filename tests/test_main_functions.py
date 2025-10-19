#!/usr/bin/env python3
"""
Тесты для функций main.py
"""

import sys
import os
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.well_data import WellTimeSeries

# Импортируем функции из main.py
from main import (
    compute_dimensionless_parameters,
    set_logarithmic_axes, 
    invert_y_axis
)


class TestMainFunctions:
    """Тесты для функций main.py"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        # Создаем тестовые данные
        self.time = np.array([1, 2, 3, 4, 5])
        self.pressure = np.array([100, 95, 90, 85, 80])
        self.flow_rate = np.array([50, 45, 40, 35, 30])
        
        self.well_data = WellTimeSeries(
            time=pd.Series(self.time),
            pressure=pd.Series(self.pressure),
            flow_rate=pd.Series(self.flow_rate),
            thickness=10.0,
            fracture_length=100.0,
            skin=0.0,
            fractures_count=1,
            a_l_ratio=0.1
        )
    
    def test_compute_dimensionless_parameters_basic(self):
        """Тест базового вычисления безразмерных параметров"""
        X, Y = compute_dimensionless_parameters(
            self.well_data, 
            self.time, 
            self.pressure, 
            self.flow_rate
        )
        
        # Проверяем, что результат не пустой
        assert len(X) == len(self.time)
        assert len(Y) == len(self.time)
        
        # Проверяем, что значения положительные
        assert np.all(X > 0)
        assert np.all(Y > 0)
        
        # Проверяем, что X и Y имеют разумные значения
        assert np.all(np.isfinite(X))
        assert np.all(np.isfinite(Y))
    
    def test_compute_dimensionless_parameters_formulas(self):
        """Тест правильности формул безразмерных параметров"""
        X, Y = compute_dimensionless_parameters(
            self.well_data, 
            self.time, 
            self.pressure, 
            self.flow_rate
        )
        
        # Типичные значения для нефти
        k = 10e-15  # проницаемость, м² (10 мД)
        mu = 0.001  # вязкость, Па*с (1 сП)
        B = 1.2     # объемный коэффициент нефти
        phi = 0.15  # пористость
        ct = 1e-5   # общая сжимаемость, 1/атм
        h = 10.0    # толщина пласта
        L = 100.0   # длина трещины
        delta_p_i = self.pressure.mean()
        
        # Проверяем X для первого значения
        Q = self.flow_rate[0]
        X_expected = (0.00864 * k * h * delta_p_i) / (mu * B * Q)
        assert abs(X[0] - X_expected) < 1e-10
        
        # Проверяем Y для первого значения
        t = self.time[0]
        Y_expected = (Q * B * t) / (24 * phi * ct * h * L**2 * delta_p_i)
        assert abs(Y[0] - Y_expected) < 1e-10
    
    def test_compute_dimensionless_parameters_edge_cases(self):
        """Тест граничных случаев"""
        # Тест с нулевыми значениями
        zero_flow_rate = np.zeros_like(self.flow_rate)
        X, Y = compute_dimensionless_parameters(
            self.well_data, 
            self.time, 
            self.pressure, 
            zero_flow_rate
        )
        
        # Должны быть защищены от деления на ноль
        assert np.all(np.isfinite(X))
        assert np.all(np.isfinite(Y))
        
        # Тест с очень малыми значениями
        small_flow_rate = np.full_like(self.flow_rate, 1e-10)
        X, Y = compute_dimensionless_parameters(
            self.well_data, 
            self.time, 
            self.pressure, 
            small_flow_rate
        )
        
        assert np.all(np.isfinite(X))
        assert np.all(np.isfinite(Y))
    
    def test_set_logarithmic_axes(self):
        """Тест установки логарифмических осей"""
        # Создаем мок для plot_widget
        mock_plot = Mock()
        
        # Вызываем функцию
        set_logarithmic_axes(mock_plot)
        
        # Проверяем, что был вызван setLogMode
        mock_plot.setLogMode.assert_called_once_with(x=True, y=True)
    
    def test_set_logarithmic_axes_exception(self):
        """Тест обработки исключений в set_logarithmic_axes"""
        # Создаем мок, который вызывает исключение
        mock_plot = Mock()
        mock_plot.setLogMode.side_effect = Exception("Test exception")
        
        # Функция не должна падать
        set_logarithmic_axes(mock_plot)
        
        # Проверяем, что исключение было обработано
        mock_plot.setLogMode.assert_called_once()
    
    def test_invert_y_axis(self):
        """Тест инверсии Y-оси"""
        # Создаем мок для plot_widget
        mock_plot = Mock()
        mock_axis = Mock()
        mock_axis.range = [0, 100]
        mock_plot.getAxis.return_value = mock_axis
        
        # Вызываем функцию
        invert_y_axis(mock_plot)
        
        # Проверяем, что был вызван setYRange с инвертированными значениями
        mock_plot.getAxis.assert_called_once_with('left')
        mock_plot.setYRange.assert_called_once_with(100, 0)
    
    def test_invert_y_axis_no_range(self):
        """Тест инверсии Y-оси без диапазона"""
        # Создаем мок для plot_widget
        mock_plot = Mock()
        mock_axis = Mock()
        mock_axis.range = None
        mock_plot.getAxis.return_value = mock_axis
        
        # Вызываем функцию
        invert_y_axis(mock_plot)
        
        # Проверяем, что setYRange не был вызван
        mock_plot.getAxis.assert_called_once_with('left')
        mock_plot.setYRange.assert_not_called()
    
    def test_invert_y_axis_exception(self):
        """Тест обработки исключений в invert_y_axis"""
        # Создаем мок, который вызывает исключение
        mock_plot = Mock()
        mock_plot.getAxis.side_effect = Exception("Test exception")
        
        # Функция не должна падать
        invert_y_axis(mock_plot)
        
        # Проверяем, что исключение было обработано
        mock_plot.getAxis.assert_called_once()


class TestMainIntegration:
    """Интеграционные тесты для main.py"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        # Создаем QApplication для тестов GUI
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    @patch('main.QApplication')
    def test_application_startup(self, mock_qapp):
        """Тест запуска приложения"""
        # Мокаем QApplication
        mock_app = Mock()
        mock_qapp.return_value = mock_app
        
        # Импортируем и создаем приложение
        from main import MyApp
        
        # Создаем экземпляр приложения
        app = MyApp()
        
        # Проверяем, что приложение создалось
        assert app is not None
        assert hasattr(app, 'well_data_list')
        assert hasattr(app, 'current_well_index')
    
    def test_plot_types_available(self):
        """Тест доступности типов графиков"""
        from main import MyApp
        
        app = MyApp()
        
        # Проверяем, что все требуемые типы графиков доступны
        required_types = [
            "Безразмерные параметры (X-Y)",
            "Логарифмический P(t) с инверсией",
            "Логарифмический Q(t)",
            "Логарифмическая производная P"
        ]
        
        # Получаем доступные типы из combo box
        available_types = []
        for i in range(app.plot_type_combo.count()):
            available_types.append(app.plot_type_combo.itemText(i))
        
        for req_type in required_types:
            assert req_type in available_types, f"Тип графика {req_type} не найден"


class TestMainPerformance:
    """Тесты производительности для main.py"""
    
    def test_compute_dimensionless_parameters_performance(self):
        """Тест производительности вычисления безразмерных параметров"""
        import time
        
        # Создаем большие массивы данных
        n_points = 10000
        time_data = np.linspace(1, 100, n_points)
        pressure_data = 100 - 0.1 * time_data + np.random.normal(0, 0.1, n_points)
        flow_rate_data = 50 - 0.05 * time_data + np.random.normal(0, 0.05, n_points)
        
        well_data = WellTimeSeries(
            time=pd.Series(time_data),
            pressure=pd.Series(pressure_data),
            flow_rate=pd.Series(flow_rate_data),
            thickness=10.0,
            fracture_length=100.0,
            skin=0.0,
            fractures_count=1,
            a_l_ratio=0.1
        )
        
        # Измеряем время выполнения
        start_time = time.time()
        X, Y = compute_dimensionless_parameters(
            well_data, 
            time_data, 
            pressure_data, 
            flow_rate_data
        )
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Проверяем, что выполнение заняло разумное время (< 1 секунды)
        assert execution_time < 1.0, f"Выполнение заняло {execution_time:.3f} секунд"
        
        # Проверяем, что результат корректен
        assert len(X) == n_points
        assert len(Y) == n_points
        assert np.all(np.isfinite(X))
        assert np.all(np.isfinite(Y))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
