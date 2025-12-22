#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генерация обратных данных ошибок для сравнения:
- Рост ошибки с увеличением объёма данных
- Другие распределения точек
- Противоположные тренды
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from helpers.math_error_logger import MathErrorLogger


def generate_reverse_error_data():
    """Генерирует данные с обратными трендами ошибок"""
    
    # Создаём отдельный логгер для обратных данных
    logger = MathErrorLogger(log_dir="logs", log_file="math_errors_reverse.jsonl")
    
    print("=" * 80)
    print("ГЕНЕРАЦИЯ ОБРАТНЫХ ДАННЫХ ОШИБОК")
    print("=" * 80)
    print()
    
    np.random.seed(123)  # Другой seed для других распределений
    
    # 1. Данные с ростом ошибки от объёма (обратный тренд)
    print("Генерация данных с ростом ошибки от объёма...")
    for i in range(40):
        volume = int(10 ** np.random.uniform(1, 4))  # 10-10000 точек
        
        # Обратный тренд: ошибка РАСТЁТ с объёмом (из-за переобучения, шума и т.д.)
        # Используем положительную зависимость вместо отрицательной
        base_error = 0.05 * (volume ** 0.3)  # Рост вместо падения
        quality = np.random.uniform(0.4, 0.9)
        
        # Чем больше объём, тем больше ошибка (переобучение)
        # Чем хуже качество, тем больше ошибка
        error = base_error * (2.5 - quality) + np.random.normal(0, 0.02)
        
        logger.log_error(
            subsystem=f"subsystem_{i % 3}",
            method=f"method_{i % 4}",
            error_type="rmse",
            error_value=max(0.01, error),
            error_message=f"Reverse trend error {i} - рост с объёмом",
            data_volume=volume,
            data_quality=quality,
            metadata={"trend": "increasing", "data_type": "reverse"}
        )
    
    # 2. Данные с нелинейной зависимостью от качества (U-образная кривая)
    print("Генерация данных с U-образной зависимостью от качества...")
    for i in range(30):
        volume = int(10 ** np.random.uniform(1.5, 3.5))
        quality = np.random.uniform(0.2, 1.0)
        
        # U-образная зависимость: ошибка минимальна при среднем качестве
        # (слишком хорошие данные могут быть переобучены, слишком плохие - недообучены)
        optimal_quality = 0.6
        quality_deviation = abs(quality - optimal_quality)
        error = 0.1 * quality_deviation + 0.05 * (volume ** -0.2) + np.random.normal(0, 0.015)
        
        logger.log_error(
            subsystem=f"subsystem_{i % 3}",
            method=f"method_{i % 4}",
            error_type="mae",
            error_value=max(0.01, error),
            error_message=f"U-shaped quality dependency {i}",
            data_volume=volume,
            data_quality=quality,
            metadata={"trend": "u_shaped", "data_type": "reverse"}
        )
    
    # 3. Данные с экспоненциальным ростом ошибки
    print("Генерация данных с экспоненциальным ростом...")
    for i in range(25):
        volume = int(10 ** np.random.uniform(1, 4))
        quality = np.random.uniform(0.3, 0.95)
        
        # Экспоненциальный рост ошибки с объёмом (проблемы масштабирования)
        error = 0.01 * np.exp(volume / 1000) * (2 - quality) + np.random.normal(0, 0.01)
        
        logger.log_error(
            subsystem=f"subsystem_{i % 3}",
            method=f"method_{i % 4}",
            error_type="max_error",
            error_value=max(0.01, min(error, 10.0)),  # Ограничиваем сверху
            error_message=f"Exponential growth error {i}",
            data_volume=volume,
            data_quality=quality,
            metadata={"trend": "exponential", "data_type": "reverse"}
        )
    
    # 4. Данные с хаотичным распределением (без явного тренда)
    print("Генерация данных с хаотичным распределением...")
    for i in range(35):
        volume = int(10 ** np.random.uniform(1, 4))
        quality = np.random.uniform(0.2, 1.0)
        
        # Случайная ошибка без явной зависимости
        error = np.random.uniform(0.01, 0.5) + np.random.normal(0, 0.1)
        
        logger.log_error(
            subsystem=f"subsystem_{i % 3}",
            method=f"method_{i % 4}",
            error_type="mape",
            error_value=max(0.01, abs(error)),
            error_message=f"Random distribution error {i}",
            data_volume=volume,
            data_quality=quality,
            metadata={"trend": "random", "data_type": "reverse"}
        )
    
    # 5. Данные с пороговым эффектом (резкий скачок ошибки)
    print("Генерация данных с пороговым эффектом...")
    for i in range(30):
        volume = int(10 ** np.random.uniform(1, 4))
        quality = np.random.uniform(0.3, 1.0)
        
        # Пороговый эффект: при объёме > 1000 ошибка резко растёт
        if volume > 1000:
            error = 0.2 + 0.1 * (volume / 1000) + np.random.normal(0, 0.05)
        else:
            error = 0.05 * (volume ** -0.3) + np.random.normal(0, 0.01)
        
        logger.log_error(
            subsystem=f"subsystem_{i % 3}",
            method=f"method_{i % 4}",
            error_type="rmse",
            error_value=max(0.01, error),
            error_message=f"Threshold effect error {i}",
            data_volume=volume,
            data_quality=quality,
            metadata={"trend": "threshold", "data_type": "reverse", "threshold_volume": 1000}
        )
    
    # Загружаем и показываем статистику
    df = logger.load_errors()
    
    print()
    print("=" * 80)
    print("ОБРАТНЫЕ ДАННЫЕ СОЗДАНЫ")
    print("=" * 80)
    print()
    print(f"Всего записей: {len(df)}")
    print(f"Типы ошибок: {df['error_type'].unique().tolist()}")
    print(f"Подсистемы: {df['subsystem'].unique().tolist()}")
    print()
    
    if 'metadata' in df.columns:
        trends = df['metadata'].apply(lambda x: x.get('trend', 'unknown') if isinstance(x, dict) else 'unknown')
        print("Распределение по трендам:")
        print(trends.value_counts().to_dict())
    
    print()
    print(f"Файл сохранён: logs/math_errors_reverse.jsonl")
    print()


if __name__ == "__main__":
    generate_reverse_error_data()

