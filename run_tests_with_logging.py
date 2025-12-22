#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для запуска нагрузочных тестов с логированием ошибок
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Запускает тесты с логированием"""
    print("=" * 80)
    print("ЗАПУСК НАГРУЗОЧНЫХ ТЕСТОВ С ЛОГИРОВАНИЕМ ОШИБОК")
    print("=" * 80)
    print()
    
    # Создаём директории для логов и результатов
    Path("logs").mkdir(exist_ok=True)
    Path("test_results").mkdir(exist_ok=True)
    Path("test_logs").mkdir(exist_ok=True)
    
    tests_to_run = [
        {
            "name": "Тесты логирования и визуализации (быстрые)",
            "file": "tests/test_error_logging_and_visualization.py",
            "markers": None
        },
        {
            "name": "Нагрузочные тесты GUI (с логированием)",
            "file": "tests/test_load_with_error_logging.py",
            "markers": "load"
        },
        {
            "name": "Нагрузочные тесты GUI (базовые)",
            "file": "tests/test_gui_load.py",
            "markers": "slow"
        },
        {
            "name": "Комплексные тесты производительности",
            "file": "tests/test_comprehensive_performance.py",
            "markers": "performance"
        }
    ]
    
    print("Доступные тесты:")
    for i, test in enumerate(tests_to_run, 1):
        print(f"  {i}. {test['name']}")
    print()
    
    # Запрашиваем выбор
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("Выберите тесты для запуска (1-4, 'all' для всех, Enter для быстрых): ").strip()
    
    if not choice:
        choice = "1"  # По умолчанию быстрые тесты
    
    if choice.lower() == "all":
        selected_tests = tests_to_run
    else:
        try:
            indices = [int(x.strip()) for x in choice.split(",")]
            selected_tests = [tests_to_run[i-1] for i in indices if 1 <= i <= len(tests_to_run)]
        except (ValueError, IndexError):
            print("❌ Неверный выбор. Запускаю быстрые тесты.")
            selected_tests = [tests_to_run[0]]
    
    # Запускаем выбранные тесты
    for test in selected_tests:
        print()
        print("=" * 80)
        print(f"Запуск: {test['name']}")
        print("=" * 80)
        
        cmd = [
            sys.executable, "-m", "pytest",
            test["file"],
            "-v",
            "-s"
        ]
        
        if test["markers"]:
            cmd.extend(["-m", test["markers"]])
        
        try:
            result = subprocess.run(cmd, cwd=Path(__file__).parent)
            if result.returncode == 0:
                print(f"✅ {test['name']} - УСПЕШНО")
            else:
                print(f"⚠️ {test['name']} - ЕСТЬ ОШИБКИ (код возврата: {result.returncode})")
        except Exception as e:
            print(f"❌ Ошибка при запуске {test['name']}: {e}")
    
    print()
    print("=" * 80)
    print("ТЕСТЫ ЗАВЕРШЕНЫ")
    print("=" * 80)
    print()
    print("Следующие шаги:")
    print("  1. Запустите генерацию визуализаций: python generate_visualizations.py")
    print("  2. Проверьте логи: python check_tests_status.py")
    print()


if __name__ == "__main__":
    main()

