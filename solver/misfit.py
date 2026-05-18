# solver/misfit.py
import numpy as np
from .derivative import compute_derivative
from .metrics import compute_metric

def sample_misfit(sample, x_fact, y_fact):
    """
    Вычисляет невязку между образцом из библиотеки и фактической кривой.
    sample: словарь с ключом 'dynamic', содержащим 'X' и 'Y' (как массивы или pandas Series)
    x_fact, y_fact: массивы фактических данных
    Возвращает скалярное значение невязки.
    """
    # Извлекаем референсные данные из образца
    sample_dynamic = sample['dynamic']
    # Преобразуем в numpy arrays, если нужно
    if hasattr(sample_dynamic['X'], 'values'):
        sample_x = sample_dynamic['X'].values
        sample_y = sample_dynamic['Y'].values
    else:
        sample_x = np.asarray(sample_dynamic['X'])
        sample_y = np.asarray(sample_dynamic['Y'])
    
    # Вычисляем логарифмические производные для обеих кривых
    _, alpha_sample = compute_derivative(sample_x, sample_y, mode="loglog")
    _, alpha_fact = compute_derivative(x_fact, y_fact, mode="loglog")
    
    # Выравниваем по длине: берем общую часть
    min_len = min(len(alpha_sample), len(alpha_fact))
    if min_len == 0:
        return float('inf')
    alpha_sample = alpha_sample[:min_len]
    alpha_fact = alpha_fact[:min_len]
    
    # Вычисляем интегральную невязку
    misfit = compute_metric(alpha_sample, alpha_fact, metric_type="integral")
    return misfit