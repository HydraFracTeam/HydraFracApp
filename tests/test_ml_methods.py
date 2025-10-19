#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для ML-методов и проверки физической адекватности результатов
"""

import sys
import os
import pandas as pd
import numpy as np
import pytest
import matplotlib.pyplot as plt
from pathlib import Path

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.ml_methods import (
    MLInterpolator, MLFilter, AdvancedInterpolator, 
    apply_ml_interpolation, apply_ml_filter, detect_outliers, clean_data
)

# Создаем директорию для тестовых данных и результатов
TEST_DATA_DIR = Path("tests/test_data")
TEST_DATA_DIR.mkdir(exist_ok=True)

# Создаем директорию для результатов тестов
TEST_RESULTS_DIR = Path("tests/test_results")
TEST_RESULTS_DIR.mkdir(exist_ok=True)


def generate_test_data():
    """Генерирует тестовые данные с различными типами искажений"""
    # Базовая синусоида
    x = np.linspace(0, 10, 100)
    y_base = np.sin(x)
    
    # Добавляем шум
    y_noisy = y_base + np.random.normal(0, 0.1, size=len(x))
    
    # Добавляем выбросы
    y_with_outliers = y_noisy.copy()
    outlier_indices = np.random.choice(len(x), size=5, replace=False)
    y_with_outliers[outlier_indices] = y_with_outliers[outlier_indices] + np.random.choice([-1, 1], size=5) * 2
    
    # Добавляем пропуски
    y_with_gaps = y_noisy.copy()
    gap_indices = np.random.choice(len(x), size=10, replace=False)
    y_with_gaps[gap_indices] = np.nan
    
    # Создаем периодический сигнал с трендом
    y_trend = y_base + 0.1 * x
    
    # Создаем ступенчатый сигнал
    y_step = np.zeros_like(x)
    y_step[x > 3] = 1
    y_step[x > 6] = 2
    y_step = y_step + np.random.normal(0, 0.05, size=len(x))
    
    # Создаем DataFrame
    df = pd.DataFrame({
        'x': x,
        'y_base': y_base,
        'y_noisy': y_noisy,
        'y_with_outliers': y_with_outliers,
        'y_with_gaps': y_with_gaps,
        'y_trend': y_trend,
        'y_step': y_step
    })
    
    # Сохраняем данные
    df.to_csv(TEST_DATA_DIR / "ml_test_data.csv", index=False)
    
    return df


def plot_results(original, processed, title, filename):
    """Строит график сравнения оригинальных и обработанных данных"""
    plt.figure(figsize=(10, 6))
    plt.plot(original.index, original.values, 'b-', label='Оригинал')
    plt.plot(processed.index, processed.values, 'r-', label='Обработанные')
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.savefig(TEST_RESULTS_DIR / filename)
    plt.close()


class TestMLInterpolation:
    """Тесты для ML-интерполяции"""
    
    @pytest.fixture
    def test_data(self):
        """Создает или загружает тестовые данные"""
        test_file = TEST_DATA_DIR / "ml_test_data.csv"
        if test_file.exists():
            return pd.read_csv(test_file)
        else:
            return generate_test_data()
    
    def test_random_forest_interpolation(self, test_data):
        """Тестирует интерполяцию Random Forest"""
        x = pd.Series(test_data['x'])
        y = pd.Series(test_data['y_with_gaps'])
        
        # Применяем интерполяцию
        y_interpolated = apply_ml_interpolation(x, y, method='random_forest')
        
        # Проверяем, что нет NaN значений
        assert not y_interpolated.isna().any(), "Интерполяция должна заполнить все NaN значения"
        
        # Проверяем физическую адекватность: значения должны быть в разумном диапазоне
        assert y_interpolated.min() >= -1.5, "Минимальное значение должно быть не меньше -1.5"
        assert y_interpolated.max() <= 1.5, "Максимальное значение должно быть не больше 1.5"
        
        # Проверяем корреляцию с базовым сигналом (без шума)
        y_base = pd.Series(test_data['y_base'])
        correlation = y_interpolated.corr(y_base)
        assert correlation > 0.7, f"Корреляция с базовым сигналом должна быть высокой, получено: {correlation}"
        
        # Визуализация результатов
        plot_results(y, y_interpolated, 
                    f"Random Forest интерполяция (корреляция: {correlation:.2f})", 
                    "rf_interpolation.png")
    
    def test_polynomial_interpolation(self, test_data):
        """Тестирует полиномиальную интерполяцию"""
        x = pd.Series(test_data['x'])
        y = pd.Series(test_data['y_with_gaps'])
        
        # Применяем интерполяцию
        y_interpolated = apply_ml_interpolation(x, y, method='polynomial')
        
        # Проверяем, что нет NaN значений
        assert not y_interpolated.isna().any(), "Интерполяция должна заполнить все NaN значения"
        
        # Визуализация результатов
        plot_results(y, y_interpolated, "Полиномиальная интерполяция", "poly_interpolation.png")


class TestMLFiltering:
    """Тесты для ML-фильтрации"""
    
    @pytest.fixture
    def test_data(self):
        """Создает или загружает тестовые данные"""
        test_file = TEST_DATA_DIR / "ml_test_data.csv"
        if test_file.exists():
            return pd.read_csv(test_file)
        else:
            return generate_test_data()
    
    def test_savitzky_golay_filter(self, test_data):
        """Тестирует фильтр Савицкого-Голея"""
        y_noisy = pd.Series(test_data['y_noisy'])
        y_base = pd.Series(test_data['y_base'])
        
        # Применяем фильтр
        y_filtered = apply_ml_filter(y_noisy, method='savitzky_golay', window_length=11, polyorder=2)
        
        # Проверяем, что нет NaN значений
        assert not y_filtered.isna().any(), "Фильтрация не должна создавать NaN значения"
        
        # Проверяем, что фильтрация улучшает корреляцию с базовым сигналом
        corr_before = y_noisy.corr(y_base)
        corr_after = y_filtered.corr(y_base)
        assert corr_after > corr_before, f"Фильтрация должна улучшать корреляцию: до={corr_before:.2f}, после={corr_after:.2f}"
        
        # Проверяем физическую адекватность: сглаживание не должно менять амплитуду сильно
        assert abs(y_filtered.max() - y_base.max()) < 0.3, "Максимальные значения не должны сильно отличаться"
        assert abs(y_filtered.min() - y_base.min()) < 0.3, "Минимальные значения не должны сильно отличаться"
        
        # Визуализация результатов
        plot_results(y_noisy, y_filtered, 
                    f"Фильтр Савицкого-Голея (корреляция: {corr_after:.2f})", 
                    "savgol_filter.png")
    
    def test_kalman_filter(self, test_data):
        """Тестирует фильтр Калмана"""
        y_noisy = pd.Series(test_data['y_noisy'])
        
        # Применяем фильтр
        y_filtered = apply_ml_filter(y_noisy, method='kalman')
        
        # Проверяем, что нет NaN значений
        assert not y_filtered.isna().any(), "Фильтрация не должна создавать NaN значения"
        
        # Визуализация результатов
        plot_results(y_noisy, y_filtered, "Фильтр Калмана", "kalman_filter.png")


class TestOutlierDetection:
    """Тесты для обнаружения выбросов"""
    
    @pytest.fixture
    def test_data(self):
        """Создает или загружает тестовые данные"""
        test_file = TEST_DATA_DIR / "ml_test_data.csv"
        if test_file.exists():
            return pd.read_csv(test_file)
        else:
            return generate_test_data()
    
    def test_iqr_outlier_detection(self, test_data):
        """Тестирует обнаружение выбросов методом IQR"""
        y_with_outliers = pd.Series(test_data['y_with_outliers'])
        
        # Обнаруживаем выбросы
        outliers = detect_outliers(y_with_outliers, method='iqr', threshold=1.5)
        
        # Проверяем, что найдены выбросы
        assert outliers.sum() > 0, "Должны быть обнаружены выбросы"
        assert outliers.sum() < len(y_with_outliers) * 0.2, "Выбросов должно быть не более 20%"
        
        # Визуализация результатов
        plt.figure(figsize=(10, 6))
        plt.scatter(y_with_outliers.index, y_with_outliers.values, c=['red' if o else 'blue' for o in outliers])
        plt.title(f"Обнаружение выбросов (IQR): найдено {outliers.sum()} выбросов")
        plt.grid(True)
        plt.savefig(TEST_RESULTS_DIR / "iqr_outliers.png")
        plt.close()
    
    def test_zscore_outlier_detection(self, test_data):
        """Тестирует обнаружение выбросов методом Z-score"""
        y_with_outliers = pd.Series(test_data['y_with_outliers'])
        
        # Обнаруживаем выбросы
        outliers = detect_outliers(y_with_outliers, method='zscore', threshold=2.0)
        
        # Проверяем, что найдены выбросы
        assert outliers.sum() > 0, "Должны быть обнаружены выбросы"
        
        # Визуализация результатов
        plt.figure(figsize=(10, 6))
        plt.scatter(y_with_outliers.index, y_with_outliers.values, c=['red' if o else 'blue' for o in outliers])
        plt.title(f"Обнаружение выбросов (Z-score): найдено {outliers.sum()} выбросов")
        plt.grid(True)
        plt.savefig(TEST_RESULTS_DIR / "zscore_outliers.png")
        plt.close()


class TestComplexDataCleaning:
    """Тесты для комплексной очистки данных"""
    
    @pytest.fixture
    def test_data(self):
        """Создает или загружает тестовые данные"""
        test_file = TEST_DATA_DIR / "ml_test_data.csv"
        if test_file.exists():
            return pd.read_csv(test_file)
        else:
            return generate_test_data()
    
    def test_clean_data(self, test_data):
        """Тестирует комплексную очистку данных"""
        x = pd.Series(test_data['x'])
        y_with_outliers = pd.Series(test_data['y_with_outliers'])
        y_base = pd.Series(test_data['y_base'])
        
        # Очищаем данные
        x_clean, y_clean = clean_data(x, y_with_outliers, 
                                      outlier_method='iqr', 
                                      filter_method='savitzky_golay')
        
        # Проверяем, что нет NaN значений
        assert not y_clean.isna().any(), "Очистка не должна создавать NaN значения"
        
        # Проверяем, что очистка улучшает корреляцию с базовым сигналом
        corr_before = y_with_outliers.corr(y_base)
        # Приводим к одинаковым индексам для корректного сравнения
        y_base_clean = y_base[x_clean.index]
        corr_after = y_clean.corr(y_base_clean)
        
        assert corr_after > corr_before, f"Очистка должна улучшать корреляцию: до={corr_before:.2f}, после={corr_after:.2f}"
        
        # Визуализация результатов
        plt.figure(figsize=(10, 6))
        plt.plot(x, y_with_outliers, 'b-', label='Исходные данные')
        plt.plot(x_clean, y_clean, 'r-', label='Очищенные данные')
        plt.plot(x, y_base, 'g--', label='Базовый сигнал')
        plt.title(f"Комплексная очистка данных (корреляция: {corr_after:.2f})")
        plt.legend()
        plt.grid(True)
        plt.savefig(TEST_RESULTS_DIR / "complex_cleaning.png")
        plt.close()


if __name__ == "__main__":
    # Генерируем тестовые данные
    print("Генерация тестовых данных...")
    test_data = generate_test_data()
    print(f"Тестовые данные сохранены в {TEST_DATA_DIR / 'ml_test_data.csv'}")
    
    # Запускаем тесты
    pytest.main(["-xvs", __file__])
