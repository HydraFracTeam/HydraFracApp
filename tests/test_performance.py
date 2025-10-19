#!/usr/bin/env python3
"""
Тесты производительности для приложения
"""

import sys
import os
import pytest
import numpy as np
import pandas as pd
import time
import psutil
import gc
from unittest.mock import Mock, patch

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.well_data import WellTimeSeries
from main import compute_dimensionless_parameters, set_logarithmic_axes, invert_y_axis


class TestPerformance:
    """Тесты производительности"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        # Очищаем память перед тестом
        gc.collect()
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        # Очищаем память после теста
        gc.collect()
    
    def test_compute_dimensionless_parameters_performance(self):
        """Тест производительности вычисления безразмерных параметров"""
        # Создаем большие массивы данных
        n_points = 50000
        time_data = np.linspace(1, 1000, n_points)
        pressure_data = 100 - 0.01 * time_data + np.random.normal(0, 0.1, n_points)
        flow_rate_data = 50 - 0.005 * time_data + np.random.normal(0, 0.05, n_points)
        
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
        
        # Проверяем производительность
        assert execution_time < 2.0, f"Выполнение заняло {execution_time:.3f} секунд (ожидалось < 2.0)"
        
        # Проверяем корректность результата
        assert len(X) == n_points
        assert len(Y) == n_points
        assert np.all(np.isfinite(X))
        assert np.all(np.isfinite(Y))
        
        print(f"✅ Вычисление безразмерных параметров для {n_points} точек: {execution_time:.3f} сек")
    
    def test_memory_usage_compute_dimensionless_parameters(self):
        """Тест использования памяти при вычислении безразмерных параметров"""
        # Получаем начальное использование памяти
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Создаем большие массивы данных
        n_points = 100000
        time_data = np.linspace(1, 1000, n_points)
        pressure_data = 100 - 0.01 * time_data + np.random.normal(0, 0.1, n_points)
        flow_rate_data = 50 - 0.005 * time_data + np.random.normal(0, 0.05, n_points)
        
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
        
        # Выполняем вычисления
        X, Y = compute_dimensionless_parameters(
            well_data, 
            time_data, 
            pressure_data, 
            flow_rate_data
        )
        
        # Получаем финальное использование памяти
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Проверяем, что увеличение памяти разумное (< 500 MB)
        assert memory_increase < 500, f"Увеличение памяти: {memory_increase:.1f} MB (ожидалось < 500)"
        
        print(f"✅ Использование памяти: {memory_increase:.1f} MB для {n_points} точек")
    
    def test_large_dataset_processing(self):
        """Тест обработки больших наборов данных"""
        # Создаем очень большой набор данных
        n_points = 200000
        time_data = np.linspace(1, 10000, n_points)
        pressure_data = 100 - 0.001 * time_data + np.random.normal(0, 0.01, n_points)
        flow_rate_data = 50 - 0.0005 * time_data + np.random.normal(0, 0.005, n_points)
        
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
        
        # Проверяем производительность для больших данных
        assert execution_time < 5.0, f"Обработка {n_points} точек заняла {execution_time:.3f} секунд"
        
        # Проверяем корректность
        assert len(X) == n_points
        assert len(Y) == n_points
        assert np.all(np.isfinite(X))
        assert np.all(np.isfinite(Y))
        
        print(f"✅ Обработка {n_points} точек: {execution_time:.3f} сек")
    
    def test_multiple_wells_performance(self):
        """Тест производительности при обработке нескольких скважин"""
        n_wells = 10
        n_points_per_well = 10000
        
        wells_data = []
        
        # Создаем данные для нескольких скважин
        for i in range(n_wells):
            time_data = np.linspace(1, 1000, n_points_per_well)
            pressure_data = 100 - 0.01 * time_data + np.random.normal(0, 0.1, n_points_per_well)
            flow_rate_data = 50 - 0.005 * time_data + np.random.normal(0, 0.05, n_points_per_well)
            
            well_data = WellTimeSeries(
                time=pd.Series(time_data),
                pressure=pd.Series(pressure_data),
                flow_rate=pd.Series(flow_rate_data),
                thickness=10.0 + i,
                fracture_length=100.0 + i * 10,
                skin=0.0,
                fractures_count=1,
                a_l_ratio=0.1
            )
            wells_data.append(well_data)
        
        # Измеряем время обработки всех скважин
        start_time = time.time()
        
        for well_data in wells_data:
            X, Y = compute_dimensionless_parameters(
                well_data, 
                well_data.time.values, 
                well_data.pressure.values, 
                well_data.flow_rate.values
            )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Проверяем производительность
        assert execution_time < 10.0, f"Обработка {n_wells} скважин заняла {execution_time:.3f} секунд"
        
        print(f"✅ Обработка {n_wells} скважин по {n_points_per_well} точек: {execution_time:.3f} сек")
    
    def test_edge_cases_performance(self):
        """Тест производительности граничных случаев"""
        # Тест с очень малыми значениями
        n_points = 10000
        time_data = np.linspace(1e-10, 1e-5, n_points)
        pressure_data = np.full(n_points, 1e-10)
        flow_rate_data = np.full(n_points, 1e-10)
        
        well_data = WellTimeSeries(
            time=pd.Series(time_data),
            pressure=pd.Series(pressure_data),
            flow_rate=pd.Series(flow_rate_data),
            thickness=1e-10,
            fracture_length=1e-10,
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
        
        # Проверяем, что обработка граничных случаев не замедляет выполнение
        assert execution_time < 1.0, f"Обработка граничных случаев заняла {execution_time:.3f} секунд"
        
        # Проверяем корректность
        assert np.all(np.isfinite(X))
        assert np.all(np.isfinite(Y))
        
        print(f"✅ Обработка граничных случаев: {execution_time:.3f} сек")
    
    def test_concurrent_processing_simulation(self):
        """Симуляция конкурентной обработки"""
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def process_well(well_data, results_queue):
            """Функция для обработки одной скважины"""
            try:
                X, Y = compute_dimensionless_parameters(
                    well_data, 
                    well_data.time.values, 
                    well_data.pressure.values, 
                    well_data.flow_rate.values
                )
                results_queue.put(("success", len(X)))
            except Exception as e:
                results_queue.put(("error", str(e)))
        
        # Создаем несколько скважин
        n_wells = 5
        wells_data = []
        
        for i in range(n_wells):
            n_points = 5000
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
            wells_data.append(well_data)
        
        # Запускаем обработку в отдельных потоках
        threads = []
        start_time = time.time()
        
        for well_data in wells_data:
            thread = threading.Thread(target=process_well, args=(well_data, results_queue))
            threads.append(thread)
            thread.start()
        
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Проверяем результаты
        success_count = 0
        error_count = 0
        
        while not results_queue.empty():
            result_type, result_data = results_queue.get()
            if result_type == "success":
                success_count += 1
            else:
                error_count += 1
        
        # Проверяем, что все скважины обработались успешно
        assert success_count == n_wells, f"Успешно обработано: {success_count}/{n_wells}"
        assert error_count == 0, f"Ошибок: {error_count}"
        
        # Проверяем производительность
        assert execution_time < 5.0, f"Конкурентная обработка заняла {execution_time:.3f} секунд"
        
        print(f"✅ Конкурентная обработка {n_wells} скважин: {execution_time:.3f} сек")


class TestMemoryEfficiency:
    """Тесты эффективности использования памяти"""
    
    def test_memory_cleanup(self):
        """Тест очистки памяти"""
        import gc
        
        # Получаем начальное использование памяти
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Создаем и обрабатываем большие данные
        n_points = 100000
        time_data = np.linspace(1, 1000, n_points)
        pressure_data = 100 - 0.01 * time_data + np.random.normal(0, 0.1, n_points)
        flow_rate_data = 50 - 0.005 * time_data + np.random.normal(0, 0.05, n_points)
        
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
        
        # Выполняем вычисления
        X, Y = compute_dimensionless_parameters(
            well_data, 
            time_data, 
            pressure_data, 
            flow_rate_data
        )
        
        # Удаляем переменные
        del time_data, pressure_data, flow_rate_data, well_data, X, Y
        
        # Принудительная очистка памяти
        gc.collect()
        
        # Получаем финальное использование памяти
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Проверяем, что память была освобождена
        assert memory_increase < 100, f"Увеличение памяти после очистки: {memory_increase:.1f} MB"
        
        print(f"✅ Эффективность памяти: {memory_increase:.1f} MB после очистки")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
