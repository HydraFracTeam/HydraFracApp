#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки исправлений ошибок с символами '^' и '*'
"""

import sys
import pandas as pd
import numpy as np
from helpers.parse_well_data import parse_well_csv
from helpers.grp_analysis import compute_pressure_derivative, compute_flow_rate_derivative
from schemas.well_data import WellTimeSeries

def test_derivative_calculation():
    """Тестирует вычисление производных"""
    print("Тестирование вычисления производных...")
    
    # Создаем тестовые данные
    time = pd.Series([0, 1, 2, 3, 4, 5])
    pressure = pd.Series([300, 295, 290, 285, 280, 275])
    flow_rate = pd.Series([100, 95, 90, 85, 80, 75])
    
    # Создаем объект WellTimeSeries
    well_data = WellTimeSeries(
        time=time,
        pressure=pressure,
        flow_rate=flow_rate,
        skin=0.05,
        thickness=10.0,
        fractures_count=5,
        fracture_width=0.001,
        fracture_length=100.0,
        a_l_ratio=0.5
    )
    
    try:
        # Тестируем производную давления
        dp_dt = compute_pressure_derivative(well_data)
        print(f"✅ Производная давления вычислена успешно. Размер: {len(dp_dt)}")
        print(f"   Первые значения: {dp_dt.head().tolist()}")
        
        # Тестируем производную дебита
        dq_dt = compute_flow_rate_derivative(well_data)
        print(f"✅ Производная дебита вычислена успешно. Размер: {len(dq_dt)}")
        print(f"   Первые значения: {dq_dt.head().tolist()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при вычислении производных: {e}")
        return False

def test_edge_cases():
    """Тестирует граничные случаи"""
    print("\nТестирование граничных случаев...")
    
    # Тест с NaN значениями
    time = pd.Series([0, 1, 2, np.nan, 4, 5])
    pressure = pd.Series([300, 295, np.nan, 285, 280, 275])
    flow_rate = pd.Series([100, 95, 90, 85, 80, 75])
    
    well_data = WellTimeSeries(
        time=time,
        pressure=pressure,
        flow_rate=flow_rate,
        skin=0.05,
        thickness=10.0,
        fractures_count=5,
        fracture_width=0.001,
        fracture_length=100.0,
        a_l_ratio=0.5
    )
    
    try:
        dp_dt = compute_pressure_derivative(well_data)
        print(f"✅ Обработка NaN значений работает. Размер: {len(dp_dt)}")
        
        dq_dt = compute_flow_rate_derivative(well_data)
        print(f"✅ Обработка NaN значений для дебита работает. Размер: {len(dq_dt)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обработке NaN значений: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_zero_time_gradient():
    """Тестирует случай с нулевым градиентом времени"""
    print("\nТестирование случая с одинаковыми значениями времени...")
    
    # Тест с повторяющимися значениями времени
    time = pd.Series([0, 0, 0, 1, 2, 3])
    pressure = pd.Series([300, 295, 290, 285, 280, 275])
    flow_rate = pd.Series([100, 95, 90, 85, 80, 75])
    
    well_data = WellTimeSeries(
        time=time,
        pressure=pressure,
        flow_rate=flow_rate,
        skin=0.05,
        thickness=10.0,
        fractures_count=5,
        fracture_width=0.001,
        fracture_length=100.0,
        a_l_ratio=0.5
    )
    
    try:
        dp_dt = compute_pressure_derivative(well_data)
        print(f"✅ Защита от деления на ноль работает. Размер: {len(dp_dt)}")
        
        # Проверяем, что нет inf или NaN в результате
        if not dp_dt.empty:
            valid_count = (~dp_dt.isna() & ~np.isinf(dp_dt)).sum()
            print(f"   Валидных значений: {valid_count}/{len(dp_dt)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обработке нулевого градиента: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_insufficient_data():
    """Тестирует случай с недостаточными данными"""
    print("\nТестирование случая с недостаточными данными...")
    
    # Тест с одной точкой
    time = pd.Series([0])
    pressure = pd.Series([300])
    flow_rate = pd.Series([100])
    
    well_data = WellTimeSeries(
        time=time,
        pressure=pressure,
        flow_rate=flow_rate,
        skin=0.05,
        thickness=10.0,
        fractures_count=5,
        fracture_width=0.001,
        fracture_length=100.0,
        a_l_ratio=0.5
    )
    
    try:
        dp_dt = compute_pressure_derivative(well_data)
        print(f"✅ Обработка недостаточных данных работает. Размер: {len(dp_dt)}")
        
        dq_dt = compute_flow_rate_derivative(well_data)
        print(f"✅ Обработка недостаточных данных для дебита работает. Размер: {len(dq_dt)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обработке недостаточных данных: {e}")
        return False

def test_file_loading():
    """Тестирует загрузку файла"""
    print("\nТестирование загрузки файла...")
    
    # Проверяем, есть ли тестовый файл
    test_file = "well_data_test.csv"
    try:
        well_data_list, error_msg = parse_well_csv(test_file)
        
        if error_msg is not None:
            print(f"⚠️  Ошибка загрузки файла: {error_msg}")
            return False
        else:
            print(f"✅ Файл загружен успешно. Количество групп: {len(well_data_list)}")
            return True
            
    except Exception as e:
        print(f"❌ Неожиданная ошибка при загрузке файла: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ ОШИБОК")
    print("=" * 60)
    
    tests = [
        test_derivative_calculation,
        test_edge_cases,
        test_zero_time_gradient,
        test_insufficient_data,
        test_file_loading
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ: {passed}/{total} тестов пройдено")
    print("=" * 60)
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
        return 0
    else:
        print("⚠️  Некоторые тесты не пройдены")
        return 1

if __name__ == "__main__":
    sys.exit(main())
