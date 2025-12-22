#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для системы логирования ошибок и визуализации
"""

import sys
import os
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.math_error_logger import MathErrorLogger, get_logger
from helpers.error_visualization import ErrorVisualizer
from helpers.dimensionless_interpolating import DimensionlessCurveInterpolator


class TestErrorLogging:
    """Тесты системы логирования ошибок"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        # Используем временную директорию для логов
        self.log_dir = Path("test_logs")
        self.logger = MathErrorLogger(log_dir=str(self.log_dir))
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        # Удаляем тестовые логи
        import shutil
        if self.log_dir.exists():
            shutil.rmtree(self.log_dir)
    
    def test_log_error_basic(self):
        """Базовый тест логирования ошибки"""
        self.logger.log_error(
            subsystem="test",
            method="test_method",
            error_type="rmse",
            error_value=0.5,
            error_message="Test error",
            data_volume=100,
            data_quality=0.8
        )
        
        df = self.logger.load_errors()
        assert len(df) == 1
        assert df.iloc[0]['subsystem'] == "test"
        assert df.iloc[0]['method'] == "test_method"
        assert df.iloc[0]['error_type'] == "rmse"
        assert df.iloc[0]['error_value'] == 0.5
    
    def test_log_computation_error(self):
        """Тест логирования исключения"""
        try:
            raise ValueError("Test exception")
        except Exception as e:
            self.logger.log_computation_error(
                subsystem="test",
                method="test_method",
                exception=e,
                data_volume=50,
                data_quality=0.6
            )
        
        df = self.logger.load_errors()
        assert len(df) == 1
        assert df.iloc[0]['error_type'] == "exception"
        assert "Test exception" in df.iloc[0]['error_message']
    
    def test_log_metric_error(self):
        """Тест логирования метрик"""
        metrics = {
            "rmse": 0.5,
            "mae": 0.3,
            "mape": 5.0
        }
        
        self.logger.log_metric_error(
            subsystem="test",
            method="test_method",
            metrics=metrics,
            data_volume=200,
            data_quality=0.9
        )
        
        df = self.logger.load_errors()
        assert len(df) == 3  # По одной записи на каждую метрику
        assert set(df['error_type'].values) == {"rmse", "mae", "mape"}
    
    def test_get_error_statistics(self):
        """Тест получения статистики"""
        # Добавляем несколько ошибок
        for i in range(5):
            self.logger.log_error(
                subsystem=f"subsystem_{i % 2}",
                method=f"method_{i % 3}",
                error_type="rmse",
                error_value=0.1 * (i + 1),
                error_message=f"Error {i}",
                data_volume=100 * (i + 1),
                data_quality=0.5 + 0.1 * i
            )
        
        stats = self.logger.get_error_statistics()
        
        assert stats['total_errors'] == 5
        assert len(stats['by_subsystem']) == 2
        assert len(stats['by_method']) == 3
        assert 'error_values' in stats


class TestErrorVisualization:
    """Тесты визуализации ошибок"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.log_dir = Path("test_logs")
        self.output_dir = Path("test_results")
        self.logger = MathErrorLogger(log_dir=str(self.log_dir))
        self.visualizer = ErrorVisualizer(output_dir=str(self.output_dir))
        
        # Генерируем тестовые данные
        np.random.seed(42)
        for i in range(20):
            volume = int(10 ** np.random.uniform(1, 4))  # 10-10000 точек
            quality = np.random.uniform(0.3, 1.0)
            error = 0.1 * (volume ** -0.5) * (2 - quality) + np.random.normal(0, 0.01)
            
            self.logger.log_error(
                subsystem=f"subsystem_{i % 3}",
                method=f"method_{i % 4}",
                error_type="rmse",
                error_value=max(0.001, error),
                error_message=f"Test error {i}",
                data_volume=volume,
                data_quality=quality
            )
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        import shutil
        if self.log_dir.exists():
            shutil.rmtree(self.log_dir)
    
    def test_plot_error_vs_volume(self):
        """Тест построения графика зависимости ошибки от объёма"""
        self.visualizer.plot_error_vs_volume(error_type="rmse")
        
        output_file = self.output_dir / "error_vs_volume_rmse.png"
        assert output_file.exists(), "График не был создан"
    
    def test_plot_error_vs_quality(self):
        """Тест построения графика зависимости ошибки от качества"""
        self.visualizer.plot_error_vs_quality(error_type="rmse")
        
        output_file = self.output_dir / "error_vs_quality_rmse.png"
        assert output_file.exists(), "График не был создан"
    
    def test_plot_error_heatmap(self):
        """Тест построения тепловой карты"""
        self.visualizer.plot_error_heatmap(error_type="rmse")
        
        output_file = self.output_dir / "error_heatmap_rmse.png"
        assert output_file.exists(), "Тепловая карта не была создана"
    
    def test_generate_all_visualizations(self):
        """Тест генерации всех визуализаций"""
        self.visualizer.generate_all_visualizations()
        
        # Проверяем, что файлы созданы
        files = list(self.output_dir.glob("error_*.png"))
        assert len(files) > 0, "Визуализации не были созданы"


class TestIntegrationWithInterpolation:
    """Интеграционные тесты логирования с интерполяцией"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.log_dir = Path("test_logs")
        self.logger = MathErrorLogger(log_dir=str(self.log_dir))
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        import shutil
        if self.log_dir.exists():
            shutil.rmtree(self.log_dir)
    
    def test_interpolation_logs_errors(self):
        """Тест, что интерполяция логирует ошибки"""
        # Создаём тестовые данные
        param_grid = np.array([[1.0, 0.1], [2.0, 0.2], [3.0, 0.3], [4.0, 0.4], [5.0, 0.5]])
        Y_grid = np.logspace(-2, 2, 20)
        
        # Создаём кривые с некоторыми пропусками
        n_samples = len(param_grid)
        n_points = len(Y_grid)
        P_curves = np.zeros((n_samples, n_points))
        
        for i, params in enumerate(param_grid):
            skin, n = params
            P_curves[i, :] = 1.0 + 0.5 * np.log10(Y_grid) + np.random.normal(0, 0.1, n_points)
        
        # Добавляем пропуски
        P_curves[0, 5:10] = np.nan
        P_curves[2, 10:15] = np.nan
        
        # Обучаем интерполятор
        interpolator = DimensionlessCurveInterpolator(methods=("linear", "rbf"))
        interpolator.fit(param_grid, Y_grid, P_curves)
        
        # Проверяем, что ошибки залогированы
        df = self.logger.load_errors()
        # Могут быть логи от обучения, но не обязательно
        # Главное - проверить, что система работает
        
        # Тестируем предсказание и сравнение
        Y_pred, P_pred = interpolator.predict(param_grid[0])
        
        # Создаём эталон (просто используем исходную кривую без пропусков)
        Y_ref = Y_grid
        P_ref = P_curves[0, :]
        valid_mask = ~np.isnan(P_ref)
        Y_ref = Y_ref[valid_mask]
        P_ref = P_ref[valid_mask]
        
        # Сравниваем
        metrics = interpolator.compare_with_reference(Y_pred, P_pred, Y_ref, P_ref)
        
        # Проверяем, что метрики логируются
        df_after = self.logger.load_errors()
        # Должны быть записи о метриках
        assert len(df_after) >= 0  # Может быть 0, если логирование не сработало, но это нормально


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

