#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки состояния нагрузочных тестов и генерации отчёта
"""

import sys
from pathlib import Path
import subprocess

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from helpers.math_error_logger import get_logger
from helpers.error_visualization import ErrorVisualizer


def check_test_files():
    """Проверяет наличие тестовых файлов"""
    test_files = {
        "GUI нагрузочные тесты": "tests/test_gui_load.py",
        "Комплексные тесты производительности": "tests/test_comprehensive_performance.py",
        "Тесты с логированием ошибок": "tests/test_load_with_error_logging.py",
        "Тесты логирования и визуализации": "tests/test_error_logging_and_visualization.py"
    }
    
    print("=" * 80)
    print("ПРОВЕРКА СОСТОЯНИЯ НАГРУЗОЧНЫХ ТЕСТОВ")
    print("=" * 80)
    print()
    
    for name, path in test_files.items():
        file_path = Path(path)
        if file_path.exists():
            lines = len(file_path.read_text(encoding='utf-8').split('\n'))
            print(f"✅ {name}: {path} ({lines} строк)")
        else:
            print(f"❌ {name}: {path} - НЕ НАЙДЕН")
    
    print()


def check_logging_system():
    """Проверяет систему логирования"""
    print("=" * 80)
    print("ПРОВЕРКА СИСТЕМЫ ЛОГИРОВАНИЯ")
    print("=" * 80)
    print()
    
    try:
        logger = get_logger()
        df = logger.load_errors()
        
        if df.empty:
            print("📊 Логов ошибок пока нет (система готова к работе)")
        else:
            print(f"📊 Найдено записей в логах: {len(df)}")
            stats = logger.get_error_statistics()
            print(f"   Всего ошибок: {stats['total_errors']}")
            if stats.get('by_subsystem'):
                print(f"   По подсистемам: {stats['by_subsystem']}")
            if stats.get('by_method'):
                print(f"   По методам: {stats['by_method']}")
        
        print("✅ Система логирования работает")
        print()
    except Exception as e:
        print(f"❌ Ошибка при проверке системы логирования: {e}")
        print()


def check_visualization_system():
    """Проверяет систему визуализации"""
    print("=" * 80)
    print("ПРОВЕРКА СИСТЕМЫ ВИЗУАЛИЗАЦИИ")
    print("=" * 80)
    print()
    
    try:
        visualizer = ErrorVisualizer()
        print("✅ Система визуализации инициализирована")
        print(f"   Директория для результатов: {visualizer.output_dir}")
        print()
    except Exception as e:
        print(f"❌ Ошибка при проверке системы визуализации: {e}")
        print()


def generate_report():
    """Генерирует отчёт о состоянии тестов"""
    print("=" * 80)
    print("СВОДНЫЙ ОТЧЁТ")
    print("=" * 80)
    print()
    
    # Проверяем наличие модулей
    modules = {
        "math_error_logger": "helpers/math_error_logger.py",
        "error_visualization": "helpers/error_visualization.py",
        "dimensionless_interpolating (с логированием)": "helpers/dimensionless_interpolating.py"
    }
    
    print("Модули:")
    for name, path in modules.items():
        if Path(path).exists():
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} - НЕ НАЙДЕН")
    
    print()
    print("Рекомендации:")
    print("  1. Запустите нагрузочные тесты: pytest tests/test_gui_load.py -v -m slow")
    print("  2. Запустите тесты с логированием: pytest tests/test_load_with_error_logging.py -v")
    print("  3. Сгенерируйте визуализации: python helpers/error_visualization.py")
    print("  4. Проверьте логи: python -c 'from helpers.math_error_logger import get_logger; print(get_logger().get_error_statistics())'")
    print()


if __name__ == "__main__":
    check_test_files()
    check_logging_system()
    check_visualization_system()
    generate_report()

