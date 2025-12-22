#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для генерации визуализаций ошибок из логов
"""

import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from helpers.math_error_logger import get_logger, MathErrorLogger
from helpers.error_visualization import ErrorVisualizer


def main():
    """Генерирует все визуализации ошибок"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Генерация визуализаций ошибок')
    parser.add_argument('--source', choices=['normal', 'reverse', 'both'], default='normal',
                       help='Источник данных: normal (обычные), reverse (обратные), both (оба)')
    args = parser.parse_args()
    
    print("=" * 80)
    print("ГЕНЕРАЦИЯ ВИЗУАЛИЗАЦИЙ ОШИБОК")
    print("=" * 80)
    print()
    
    sources_to_process = []
    
    if args.source in ['normal', 'both']:
        sources_to_process.append(('math_errors_new.jsonl', '', 'обычные'))
    
    if args.source in ['reverse', 'both']:
        # Проверяем наличие обратных данных
        reverse_log = Path("logs/math_errors_reverse.jsonl")
        if not reverse_log.exists():
            print("⚠️ Обратные данные не найдены.")
            print("   Запустите: python generate_reverse_error_data.py")
            print()
            if args.source == 'reverse':
                return
        else:
            sources_to_process.append(('math_errors_reverse.jsonl', '_reverse', 'обратные'))
    
    if not sources_to_process:
        print("⚠️ Нет данных для визуализации.")
        print()
        print("Для генерации тестовых данных запустите:")
        print("  python -m pytest tests/test_error_logging_and_visualization.py::TestErrorVisualizationGeneration::test_generate_error_visualizations -v -s")
        print("  python generate_reverse_error_data.py")
        print()
        return
    
    all_result_files = []
    
    for log_file, suffix, description in sources_to_process:
        print(f"\n{'=' * 80}")
        print(f"Обработка {description} данных: {log_file}")
        print(f"{'=' * 80}")
        print()
        
        # Проверяем наличие логов
        logger = MathErrorLogger(log_dir="logs", log_file=log_file)
        df = logger.load_errors()
        
        if df.empty:
            print(f"⚠️ Логов ошибок не найдено в {log_file}.")
            continue
        
        print(f"📊 Найдено записей в логах: {len(df)}")
        print(f"   Типы ошибок: {df['error_type'].unique().tolist()}")
        print(f"   Подсистемы: {df['subsystem'].unique().tolist()}")
        print()
        
        # Генерируем визуализации
        print(f"Генерация визуализаций для {description} данных...")
        print()
        
        visualizer = ErrorVisualizer(output_dir="test_results", log_file=log_file)
        visualizer.generate_all_visualizations(suffix=suffix)
        
        # Собираем созданные файлы
        result_files = sorted(Path("test_results").glob(f"error_*{suffix}.png"))
        all_result_files.extend(result_files)
    
    # Показываем все созданные файлы
    print()
    print("=" * 80)
    print("ВИЗУАЛИЗАЦИИ СОЗДАНЫ")
    print("=" * 80)
    print()
    print(f"Всего создано файлов: {len(all_result_files)}")
    print()
    print("Созданные файлы:")
    for f in sorted(all_result_files):
        print(f"  📊 {f.name}")
    print()
    print("Файлы находятся в директории: test_results/")
    print()
    print("Для просмотра откройте файлы в любом просмотрщике изображений.")
    print()
    print("Сравнение:")
    print("  - Файлы без суффикса: обычные данные (ошибка падает с объёмом)")
    print("  - Файлы с _reverse: обратные данные (ошибка растёт с объёмом)")
    print()


if __name__ == "__main__":
    main()

