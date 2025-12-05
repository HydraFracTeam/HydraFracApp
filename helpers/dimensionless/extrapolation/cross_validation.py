"""
Модуль кросс-валидации для оценки качества моделей экстраполяции.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable, Any
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


def time_series_cross_validation(
    t: np.ndarray,
    y: np.ndarray,
    model_factory: Callable,
    n_splits: int = 5,
    test_size: Optional[float] = None,
    min_train_size: int = 10,
    scoring: str = 'rmse'
) -> Dict[str, Any]:
    """
    Выполняет кросс-валидацию для временных рядов с использованием TimeSeriesSplit.
    
    Args:
        t: Временные метки
        y: Значения временного ряда
        model_factory: Функция, которая создает и обучает модель: model = model_factory(t_train, y_train)
        n_splits: Количество разбиений для кросс-валидации
        test_size: Размер тестовой выборки (если None, используется автоматически)
        min_train_size: Минимальный размер обучающей выборки
        scoring: Метрика для оценки ('rmse', 'mae', 'r2')
    
    Returns:
        Словарь с результатами:
        {
            'scores': список оценок для каждого fold,
            'mean_score': средняя оценка,
            'std_score': стандартное отклонение,
            'predictions': предсказания для каждого fold,
            'indices': индексы разбиений
        }
    """
    
    t = np.asarray(t).flatten()
    y = np.asarray(y).flatten()
    
    # Убираем NaN
    mask = np.isfinite(t) & np.isfinite(y)
    if np.sum(mask) < min_train_size + 1:
        return {
            'scores': [],
            'mean_score': np.inf,
            'std_score': np.inf,
            'predictions': [],
            'indices': []
        }
    
    t_clean = t[mask]
    y_clean = y[mask]
    original_indices = np.where(mask)[0]
    
    n_samples = len(t_clean)
    
    # Определяем количество разбиений
    if n_samples < min_train_size * 2:
        n_splits = 2
    else:
        max_splits = (n_samples - min_train_size) // min_train_size
        n_splits = min(n_splits, max_splits)
    
    if n_splits < 2:
        return {
            'scores': [],
            'mean_score': np.inf,
            'std_score': np.inf,
            'predictions': [],
            'indices': []
        }
    
    # Используем TimeSeriesSplit для временных рядов
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    scores = []
    all_predictions = []
    all_indices = []
    
    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(t_clean)):
        if len(train_idx) < min_train_size or len(test_idx) == 0:
            continue
        
        t_train = t_clean[train_idx]
        y_train = y_clean[train_idx]
        t_test = t_clean[test_idx]
        y_test = y_clean[test_idx]
        
        try:
            # Обучаем модель
            model = model_factory(t_train, y_train)
            
            # Предсказываем
            if hasattr(model, 'predict'):
                y_pred = model.predict(t_test)
            else:
                # Если модель не имеет метода predict, пропускаем
                continue
            
            # Вычисляем метрику
            if scoring == 'rmse':
                score = np.sqrt(mean_squared_error(y_test, y_pred))
            elif scoring == 'mae':
                score = mean_absolute_error(y_test, y_pred)
            elif scoring == 'r2':
                score = r2_score(y_test, y_pred)
                score = -score  # Отрицательный для минимизации
            else:
                score = np.sqrt(mean_squared_error(y_test, y_pred))
            
            scores.append(score)
            all_predictions.append({
                'fold': fold_idx,
                't_test': t_test,
                'y_test': y_test,
                'y_pred': y_pred,
                'train_indices': original_indices[train_idx],
                'test_indices': original_indices[test_idx]
            })
            all_indices.append({
                'fold': fold_idx,
                'train_idx': original_indices[train_idx],
                'test_idx': original_indices[test_idx]
            })
            
        except Exception as e:
            # Если модель не смогла обучиться, пропускаем fold
            continue
    
    if len(scores) == 0:
        return {
            'scores': [],
            'mean_score': np.inf,
            'std_score': np.inf,
            'predictions': [],
            'indices': []
        }
    
    scores = np.array(scores)
    
    return {
        'scores': scores.tolist(),
        'mean_score': float(np.mean(scores)),
        'std_score': float(np.std(scores)),
        'min_score': float(np.min(scores)),
        'max_score': float(np.max(scores)),
        'predictions': all_predictions,
        'indices': all_indices,
        'n_splits': len(scores)
    }


def compare_models_cv(
    t: np.ndarray,
    y: np.ndarray,
    models: Dict[str, Callable],
    n_splits: int = 5,
    min_train_size: int = 10,
    scoring: str = 'rmse'
) -> Dict[str, Any]:
    """
    Сравнивает несколько моделей с использованием кросс-валидации.
    
    Args:
        t: Временные метки
        y: Значения временного ряда
        models: Словарь {model_name: model_factory_function}
        n_splits: Количество разбиений для кросс-валидации
        min_train_size: Минимальный размер обучающей выборки
        scoring: Метрика для оценки
    
    Returns:
        Словарь с результатами сравнения:
        {
            'best_model': название лучшей модели,
            'model_results': {model_name: cv_results},
            'comparison': DataFrame с сравнением моделей
        }
    """
    
    model_results = {}
    
    for model_name, model_factory in models.items():
        cv_results = time_series_cross_validation(
            t, y, model_factory, n_splits=n_splits,
            min_train_size=min_train_size, scoring=scoring
        )
        model_results[model_name] = cv_results
    
    # Выбираем лучшую модель (минимальная средняя ошибка)
    best_model = None
    best_score = np.inf
    
    for model_name, results in model_results.items():
        mean_score = results.get('mean_score', np.inf)
        if mean_score < best_score:
            best_score = mean_score
            best_model = model_name
    
    # Создаем DataFrame для сравнения
    comparison_data = []
    for model_name, results in model_results.items():
        comparison_data.append({
            'model': model_name,
            'mean_score': results.get('mean_score', np.inf),
            'std_score': results.get('std_score', np.inf),
            'min_score': results.get('min_score', np.inf),
            'max_score': results.get('max_score', np.inf),
            'n_splits': results.get('n_splits', 0)
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    comparison_df = comparison_df.sort_values('mean_score')
    
    return {
        'best_model': best_model,
        'best_score': best_score,
        'model_results': model_results,
        'comparison': comparison_df
    }

