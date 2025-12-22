#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Просмотр сохранённых данных ошибок
"""

import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from helpers.math_error_logger import MathErrorLogger


def view_data(log_file: str = "math_errors.jsonl"):
    """Просматривает сохранённые данные"""
    logger = MathErrorLogger(log_dir="logs", log_file=log_file)
    df = logger.load_errors()
    
    print("=" * 80)
    print(f"ПРОСМОТР ДАННЫХ: {log_file}")
    print("=" * 80)
    print()
    
    if df.empty:
        print("⚠️ Данных не найдено")
        return
    
    print(f"📊 Всего записей: {len(df)}")
    print()
    
    # Основная статистика
    print("Статистика по типам ошибок:")
    if 'error_type' in df.columns:
        print(df['error_type'].value_counts().to_string())
    print()
    
    print("Статистика по подсистемам:")
    if 'subsystem' in df.columns:
        print(df['subsystem'].value_counts().to_string())
    print()
    
    print("Статистика по методам:")
    if 'method' in df.columns:
        print(df['method'].value_counts().to_string())
    print()
    
    # Статистика по значениям ошибок
    numeric_errors = df[df['error_value'].notna() & (df['error_type'] != 'exception')]
    if not numeric_errors.empty:
        print("Статистика значений ошибок:")
        print(f"  Среднее: {numeric_errors['error_value'].mean():.6f}")
        print(f"  Медиана: {numeric_errors['error_value'].median():.6f}")
        print(f"  Мин: {numeric_errors['error_value'].min():.6f}")
        print(f"  Макс: {numeric_errors['error_value'].max():.6f}")
        print(f"  Стд. отклонение: {numeric_errors['error_value'].std():.6f}")
        print()
    
    # Статистика по объёму данных
    if 'data_volume' in df.columns:
        volume_data = df[df['data_volume'].notna()]
        if not volume_data.empty:
            print("Статистика по объёму данных:")
            print(f"  Мин: {volume_data['data_volume'].min()}")
            print(f"  Макс: {volume_data['data_volume'].max()}")
            print(f"  Среднее: {volume_data['data_volume'].mean():.1f}")
            print(f"  Медиана: {volume_data['data_volume'].median():.1f}")
            print()
    
    # Статистика по качеству данных
    if 'data_quality' in df.columns:
        quality_data = df[df['data_quality'].notna()]
        if not quality_data.empty:
            print("Статистика по качеству данных:")
            print(f"  Мин: {quality_data['data_quality'].min():.3f}")
            print(f"  Макс: {quality_data['data_quality'].max():.3f}")
            print(f"  Среднее: {quality_data['data_quality'].mean():.3f}")
            print(f"  Медиана: {quality_data['data_quality'].median():.3f}")
            print()
    
    # Корреляция ошибки с объёмом (если есть данные)
    if 'data_volume' in df.columns and 'error_value' in df.columns:
        volume_errors = df[df['data_volume'].notna() & df['error_value'].notna() & (df['error_type'] != 'exception')]
        if len(volume_errors) > 1:
            correlation = volume_errors['data_volume'].corr(volume_errors['error_value'])
            print(f"Корреляция ошибки с объёмом данных: {correlation:.4f}")
            if correlation < 0:
                print("  → Отрицательная корреляция: ошибка ПАДАЕТ с ростом объёма (нормальное поведение)")
            elif correlation > 0:
                print("  → Положительная корреляция: ошибка РАСТЁТ с ростом объёма (проблема!)")
            else:
                print("  → Нет корреляции")
            print()
    
    # Показываем первые несколько записей
    print("Первые 5 записей:")
    print(df.head().to_string())
    print()


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Просмотр сохранённых данных ошибок')
    parser.add_argument('--file', default='math_errors.jsonl',
                       help='Имя файла лога (по умолчанию: math_errors.jsonl)')
    parser.add_argument('--all', action='store_true',
                       help='Показать все доступные файлы')
    
    args = parser.parse_args()
    
    if args.all:
        # Показываем все доступные файлы
        log_dir = Path("logs")
        if log_dir.exists():
            jsonl_files = list(log_dir.glob("*.jsonl"))
            print("=" * 80)
            print("ДОСТУПНЫЕ ФАЙЛЫ ЛОГОВ")
            print("=" * 80)
            print()
            for f in jsonl_files:
                logger = MathErrorLogger(log_dir="logs", log_file=f.name)
                df = logger.load_errors()
                print(f"📄 {f.name}: {len(df)} записей")
            print()
            
            # Показываем данные для каждого файла
            for f in jsonl_files:
                print("\n" + "=" * 80)
                view_data(f.name)
        else:
            print("Директория logs/ не найдена")
    else:
        view_data(args.file)


if __name__ == "__main__":
    main()

