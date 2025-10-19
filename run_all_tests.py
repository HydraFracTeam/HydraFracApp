#!/usr/bin/env python3
"""
Скрипт для запуска всех тестов проекта
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def run_command(command, description):
    """Запускает команду и выводит результат"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Команда: {command}")
    print("-" * 60)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"⏱️  Время выполнения: {execution_time:.2f} секунд")
        print(f"📊 Код возврата: {result.returncode}")
        
        if result.stdout:
            print("\n📤 ВЫВОД:")
            print(result.stdout)
        
        if result.stderr:
            print("\n⚠️  ОШИБКИ:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ УСПЕШНО")
        else:
            print("❌ ОШИБКА")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ ИСКЛЮЧЕНИЕ: {e}")
        return False

def main():
    """Главная функция"""
    print("🚀 ЗАПУСК ВСЕХ ТЕСТОВ ПРОЕКТА")
    print("=" * 60)
    
    # Список тестов для запуска
    tests = [
        {
            "command": "python test_requirements.py",
            "description": "Тест требований (безразмерные параметры, логарифмические графики, инверсия Y)"
        },
        {
            "command": "python test_coverage_analysis.py",
            "description": "Анализ покрытия кода тестами"
        },
        {
            "command": "python -m pytest tests/test_main_functions.py -v",
            "description": "Unit-тесты функций main.py"
        },
        {
            "command": "python -m pytest tests/test_helpers_and_physics.py -v",
            "description": "Тесты helpers и physics"
        },
        {
            "command": "python -m pytest tests/test_ml_methods.py -v",
            "description": "Тесты ML-методов"
        },
        {
            "command": "python -m pytest tests/test_well_analysis.py -v",
            "description": "Тесты анализа скважин"
        },
        {
            "command": "python -m pytest tests/test_gui_integration.py -v",
            "description": "Интеграционные тесты GUI"
        },
        {
            "command": "python -m pytest tests/test_performance.py -v -s",
            "description": "Тесты производительности"
        },
        {
            "command": "python -m pytest tests/ -v --tb=short",
            "description": "Все тесты проекта"
        }
    ]
    
    # Результаты тестов
    results = []
    
    # Запускаем каждый тест
    for test in tests:
        success = run_command(test["command"], test["description"])
        results.append({
            "description": test["description"],
            "success": success
        })
    
    # Выводим итоговый отчет
    print(f"\n{'='*60}")
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print(f"{'='*60}")
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - successful_tests
    
    print(f"📈 Всего тестов: {total_tests}")
    print(f"✅ Успешных: {successful_tests}")
    print(f"❌ Неудачных: {failed_tests}")
    print(f"📊 Процент успеха: {(successful_tests/total_tests)*100:.1f}%")
    
    print(f"\n📋 ДЕТАЛИ:")
    print("-" * 60)
    
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['description']}")
    
    # Рекомендации
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    print("-" * 60)
    
    if failed_tests > 0:
        print("⚠️  Есть неудачные тесты - рекомендуется исправить ошибки")
    
    if successful_tests == total_tests:
        print("🎉 Все тесты прошли успешно!")
        print("✅ Проект готов к использованию")
    
    # Проверяем покрытие
    coverage_ok = any(r["success"] and "покрытия" in r["description"] for r in results)
    if not coverage_ok:
        print("⚠️  Не удалось проанализировать покрытие кода")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
