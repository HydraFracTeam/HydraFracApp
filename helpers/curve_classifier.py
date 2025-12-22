"""
Модуль для классификации безразмерных X-Y кривых по степени пологости/крутости.
Реализует контракт: разделение кривых на пологие (класс 0) и крутые (класс 1).
"""

import numpy as np
from typing import Tuple, Dict, Any, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')


class CurveClassifier:
    """
    Классификатор безразмерных X-Y кривых по степени пологости/крутости.
    
    Классифицирует кривые на:
    - Класс 0: расчётная круче эталонной (нужно ужимать)
    - Класс 1: расчётная положе эталонной (нужно растягивать)
    """
    
    def __init__(self, classifier_type: str = 'logistic', use_scaling: bool = True):
        """
        :param classifier_type: Тип классификатора ('logistic', 'tree', 'forest')
        :param use_scaling: Использовать ли стандартизацию признаков (всегда True для нормализации)
        """
        self.classifier_type = classifier_type
        self.use_scaling = True  # Всегда используем нормализацию для классификатора
        self.classifier = None
        self.scaler = StandardScaler()  # Всегда создаём scaler для нормализации признаков
        self.median_steepness = None
        self.is_fitted = False
        
    def extract_pq_features(self, P: np.ndarray, Q: np.ndarray, 
                           h: Optional[float] = None, L: Optional[float] = None, 
                           W: Optional[float] = None) -> np.ndarray:
        """
        Извлекает статистические признаки из временных рядов P и Q, а также параметры скважины.
        
        Признаки:
        1-12. Статистики P и Q (см. ниже)
        13. h (толщина пласта) - полный вес (1.0)
        14. L (длина трещины) - сниженный вес (0.7)
        15. W (ширина трещины) - сниженный вес (0.7)
        
        Статистики P и Q:
        1. Среднее P
        2. Медиана P
        3. Стандартное отклонение P
        4. Диапазон P (max - min)
        5. Наклон P (линейный тренд)
        6. Среднее Q
        7. Медиана Q
        8. Стандартное отклонение Q
        9. Диапазон Q (max - min)
        10. Наклон Q (линейный тренд)
        11. Корреляция P и Q
        12. Отношение средних P/Q
        
        :param P: Давление (временной ряд)
        :param Q: Дебит (временной ряд)
        :param h: Толщина пласта (опционально, один для всей скважины)
        :param L: Длина трещины (опционально)
        :param W: Ширина трещины (опционально)
        :return: Массив признаков (15 элементов, если h, L, W предоставлены, иначе 12)
        """
        P = np.asarray(P).flatten()
        Q = np.asarray(Q).flatten()
        
        # Убираем NaN и Inf
        valid_mask = np.isfinite(P) & np.isfinite(Q) & (P > 0) & (Q > 0)
        
        if np.sum(valid_mask) < 3:
            return np.zeros(12)
        
        P_valid = P[valid_mask]
        Q_valid = Q[valid_mask]
        
        # Признаки для P
        P_mean = np.mean(P_valid)
        P_median = np.median(P_valid)
        P_std = np.std(P_valid) if len(P_valid) > 1 else 0.0
        P_range = np.max(P_valid) - np.min(P_valid)
        
        # Линейный тренд для P
        if len(P_valid) > 1:
            x_p = np.arange(len(P_valid))
            P_slope = np.polyfit(x_p, P_valid, 1)[0] if len(P_valid) > 1 else 0.0
        else:
            P_slope = 0.0
        
        # Признаки для Q
        Q_mean = np.mean(Q_valid)
        Q_median = np.median(Q_valid)
        Q_std = np.std(Q_valid) if len(Q_valid) > 1 else 0.0
        Q_range = np.max(Q_valid) - np.min(Q_valid)
        
        # Линейный тренд для Q
        if len(Q_valid) > 1:
            x_q = np.arange(len(Q_valid))
            Q_slope = np.polyfit(x_q, Q_valid, 1)[0] if len(Q_valid) > 1 else 0.0
        else:
            Q_slope = 0.0
        
        # Корреляция P и Q
        if len(P_valid) > 1 and len(Q_valid) > 1 and len(P_valid) == len(Q_valid):
            try:
                P_Q_corr = np.corrcoef(P_valid, Q_valid)[0, 1]
                if not np.isfinite(P_Q_corr):
                    P_Q_corr = 0.0
            except Exception:
                P_Q_corr = 0.0
        else:
            P_Q_corr = 0.0
        
        # Отношение средних
        P_Q_ratio = P_mean / (Q_mean + 1e-10)
        
        # Базовые признаки из P и Q
        features = [
            P_mean, P_median, P_std, P_range, P_slope,
            Q_mean, Q_median, Q_std, Q_range, Q_slope,
            P_Q_corr, P_Q_ratio
        ]
        
        # Добавляем параметры скважины с разными весами
        # h - полный вес (1.0), L и W - сниженный вес (0.7)
        # Преобразуем в скаляры, если это массивы
        
        if h is not None:
            h_scalar = float(h) if not isinstance(h, (int, float)) else h
            if np.isfinite(h_scalar) and h_scalar > 0:
                features.append(h_scalar * 1.0)  # Полный вес для h
            else:
                features.append(0.0)
        else:
            features.append(0.0)
        
        if L is not None:
            L_scalar = float(L) if not isinstance(L, (int, float)) else L
            if np.isfinite(L_scalar) and L_scalar > 0:
                features.append(L_scalar * 0.7)  # Сниженный вес для L
            else:
                features.append(0.0)
        else:
            features.append(0.0)
        
        if W is not None:
            W_scalar = float(W) if not isinstance(W, (int, float)) else W
            if np.isfinite(W_scalar) and W_scalar > 0:
                features.append(W_scalar * 0.7)  # Сниженный вес для W
            else:
                features.append(0.0)
        else:
            features.append(0.0)
        
        return np.array(features)
    
    def compute_curve_classification_metric(self, X_calc: np.ndarray, Y_calc: np.ndarray,
                                           X_data: np.ndarray, Y_data: np.ndarray) -> float:
        """
        Вычисляет метрику для классификации кривой на основе формы.
        
        Проверяет:
        - Крутая кривая: расчётная постоянно больше эталона (или с 5-10 точки) и растёт быстрее
        - Полая кривая: расчётная постоянно меньше эталона и растёт медленнее
        
        Положительное значение = расчётная круче (класс 0 - нужно ужимать)
        Отрицательное значение = расчётная положе (класс 1 - нужно растягивать)
        
        :param X_calc: Расчётные значения X
        :param Y_calc: Расчётные значения Y
        :param X_data: Эталонные значения X
        :param Y_data: Эталонные значения Y
        :return: Метрика классификации
        """
        X_calc = np.asarray(X_calc).flatten()
        Y_calc = np.asarray(Y_calc).flatten()
        X_data = np.asarray(X_data).flatten()
        Y_data = np.asarray(Y_data).flatten()
        
        # Убираем NaN и Inf
        valid_mask = (np.isfinite(X_calc) & np.isfinite(Y_calc) & 
                     np.isfinite(X_data) & np.isfinite(Y_data) &
                     (X_calc > 0) & (Y_calc > 0) & (X_data > 0) & (Y_data > 0))
        
        if np.sum(valid_mask) < 10:  # Нужно минимум 10 точек для анализа
            return 0.0
        
        X_calc_valid = X_calc[valid_mask]
        Y_calc_valid = Y_calc[valid_mask]
        X_data_valid = X_data[valid_mask]
        Y_data_valid = Y_data[valid_mask]
        
        # Интерполируем обе кривые на общую сетку
        log_X_calc = np.log10(X_calc_valid)
        log_Y_calc = np.log10(Y_calc_valid)
        log_X_data = np.log10(X_data_valid)
        log_Y_data = np.log10(Y_data_valid)
        
        # Сортируем по X
        sort_idx_calc = np.argsort(log_X_calc)
        sort_idx_data = np.argsort(log_X_data)
        
        log_X_calc_sorted = log_X_calc[sort_idx_calc]
        log_Y_calc_sorted = log_Y_calc[sort_idx_calc]
        log_X_data_sorted = log_X_data[sort_idx_data]
        log_Y_data_sorted = log_Y_data[sort_idx_data]
        
        # Находим общий диапазон X
        X_min = max(np.min(log_X_calc_sorted), np.min(log_X_data_sorted))
        X_max = min(np.max(log_X_calc_sorted), np.max(log_X_data_sorted))
        
        if X_max <= X_min:
            return 0.0
        
        # Создаём общую сетку
        n_points = min(100, len(X_calc_valid), len(X_data_valid))
        X_common = np.linspace(X_min, X_max, n_points)
        
        # Интерполируем Y на общую сетку
        from scipy.interpolate import interp1d
        try:
            interp_calc = interp1d(log_X_calc_sorted, log_Y_calc_sorted, 
                                  kind='linear', bounds_error=False, fill_value='extrapolate')
            interp_data = interp1d(log_X_data_sorted, log_Y_data_sorted,
                                  kind='linear', bounds_error=False, fill_value='extrapolate')
            
            Y_calc_interp = interp_calc(X_common)
            Y_data_interp = interp_data(X_common)
            
            # Преобразуем обратно из логарифмического масштаба для сравнения
            Y_calc_abs = 10 ** Y_calc_interp
            Y_data_abs = 10 ** Y_data_interp
            
            # Проверяем форму кривой
            # 1. Проверяем, постоянно ли расчётная больше/меньше эталонной (начиная с 5-10 точки)
            start_idx = min(10, n_points // 10)  # Начинаем с 5-10% точек
            Y_ratio = Y_calc_abs[start_idx:] / (Y_data_abs[start_idx:] + 1e-10)
            
            # Если расчётная постоянно больше (ratio > 1), это крутая кривая
            # Если расчётная постоянно меньше (ratio < 1), это пологая кривая
            mean_ratio = np.mean(Y_ratio)
            ratio_above_one = np.sum(Y_ratio > 1.0) / len(Y_ratio)  # Доля точек, где расчётная больше
            
            # 2. Проверяем скорость роста (наклон)
            dY_calc = np.diff(Y_calc_interp)
            dY_data = np.diff(Y_data_interp)
            dX = np.diff(X_common)
            
            valid_deriv_mask = np.abs(dX) > 1e-10
            if np.any(valid_deriv_mask):
                slopes_calc = dY_calc[valid_deriv_mask] / dX[valid_deriv_mask]
                slopes_data = dY_data[valid_deriv_mask] / dX[valid_deriv_mask]
                
                mean_slope_diff = np.mean(slopes_calc) - np.mean(slopes_data)
            else:
                mean_slope_diff = 0.0
            
            # Комбинированная метрика:
            # - Если расчётная постоянно больше и растёт быстрее → положительное значение (крутая)
            # - Если расчётная постоянно меньше и растёт медленнее → отрицательное значение (пологая)
            # Вес для ratio больше, так как это более надёжный признак
            metric = 0.7 * (mean_ratio - 1.0) + 0.3 * mean_slope_diff
            
            # Дополнительный бонус, если расчётная постоянно больше/меньше
            if ratio_above_one > 0.7:  # Более 70% точек выше эталона
                metric += 0.2
            elif ratio_above_one < 0.3:  # Менее 30% точек выше эталона
                metric -= 0.2
            
            return float(metric)
        except Exception:
            return 0.0
    
    def compute_steepness_ratio(self, X_calc: np.ndarray, Y_calc: np.ndarray,
                                X_data: np.ndarray, Y_data: np.ndarray) -> float:
        """
        Вычисляет метрику отношения крутости расчётной и эталонной кривых.
        
        Положительное значение означает, что расчётная кривая круче эталонной (нужно ужимать).
        Отрицательное значение означает, что расчётная кривая положе эталонной (нужно растягивать).
        
        :param X_calc: Расчётные значения X
        :param Y_calc: Расчётные значения Y
        :param X_data: Эталонные значения X
        :param Y_data: Эталонные значения Y
        :return: Метрика отношения крутости (положительное = расчётная круче, отрицательное = расчётная положе)
        """
        X_calc = np.asarray(X_calc).flatten()
        Y_calc = np.asarray(Y_calc).flatten()
        X_data = np.asarray(X_data).flatten()
        Y_data = np.asarray(Y_data).flatten()
        
        # Убираем NaN и Inf
        valid_mask = (np.isfinite(X_calc) & np.isfinite(Y_calc) & 
                     np.isfinite(X_data) & np.isfinite(Y_data) &
                     (X_calc > 0) & (Y_calc > 0) & (X_data > 0) & (Y_data > 0))
        
        if np.sum(valid_mask) < 3:
            return 0.0
        
        X_calc_valid = X_calc[valid_mask]
        Y_calc_valid = Y_calc[valid_mask]
        X_data_valid = X_data[valid_mask]
        Y_data_valid = Y_data[valid_mask]
        
        # Интерполируем обе кривые на общую сетку для сравнения
        # Используем логарифмическую интерполяцию
        log_X_calc = np.log10(X_calc_valid)
        log_Y_calc = np.log10(Y_calc_valid)
        log_X_data = np.log10(X_data_valid)
        log_Y_data = np.log10(Y_data_valid)
        
        # Сортируем по X
        sort_idx_calc = np.argsort(log_X_calc)
        sort_idx_data = np.argsort(log_X_data)
        
        log_X_calc_sorted = log_X_calc[sort_idx_calc]
        log_Y_calc_sorted = log_Y_calc[sort_idx_calc]
        log_X_data_sorted = log_X_data[sort_idx_data]
        log_Y_data_sorted = log_Y_data[sort_idx_data]
        
        # Находим общий диапазон X
        X_min = max(np.min(log_X_calc_sorted), np.min(log_X_data_sorted))
        X_max = min(np.max(log_X_calc_sorted), np.max(log_X_data_sorted))
        
        if X_max <= X_min:
            return 0.0
        
        # Создаём общую сетку
        n_points = min(50, len(X_calc_valid), len(X_data_valid))
        X_common = np.linspace(X_min, X_max, n_points)
        
        # Интерполируем Y на общую сетку
        from scipy.interpolate import interp1d
        try:
            interp_calc = interp1d(log_X_calc_sorted, log_Y_calc_sorted, 
                                  kind='linear', bounds_error=False, fill_value='extrapolate')
            interp_data = interp1d(log_X_data_sorted, log_Y_data_sorted,
                                  kind='linear', bounds_error=False, fill_value='extrapolate')
            
            Y_calc_interp = interp_calc(X_common)
            Y_data_interp = interp_data(X_common)
            
            # Вычисляем наклоны на общей сетке
            dY_calc = np.diff(Y_calc_interp)
            dY_data = np.diff(Y_data_interp)
            dX = np.diff(X_common)
            
            valid_deriv_mask = np.abs(dX) > 1e-10
            if np.any(valid_deriv_mask):
                slopes_calc = dY_calc[valid_deriv_mask] / dX[valid_deriv_mask]
                slopes_data = dY_data[valid_deriv_mask] / dX[valid_deriv_mask]
                
                # Разница средних наклонов
                mean_slope_calc = np.mean(slopes_calc)
                mean_slope_data = np.mean(slopes_data)
                
                # Положительное значение = расчётная круче (нужно ужимать)
                # Отрицательное значение = расчётная положе (нужно растягивать)
                slope_diff = mean_slope_calc - mean_slope_data
                
                return float(slope_diff)
            else:
                return 0.0
        except Exception:
            return 0.0
    
    def compute_curve_features(self, X_calc: np.ndarray, Y_calc: np.ndarray,
                              X_data: np.ndarray, Y_data: np.ndarray) -> np.ndarray:
        """
        Вычисляет признаки отношения расчётной и эталонной кривых для классификации.
        
        Признаки:
        1. Разница средних наклонов (расчётная - эталонная)
        2. Разница медианных наклонов
        3. Отношение диапазонов Y (расчётная / эталонная)
        4. Среднее относительное отклонение Y
        5. Максимальная разница наклонов
        
        :param X_calc: Расчётные значения X
        :param Y_calc: Расчётные значения Y
        :param X_data: Эталонные значения X
        :param Y_data: Эталонные значения Y
        :return: Массив признаков (5 элементов)
        """
        X_calc = np.asarray(X_calc).flatten()
        Y_calc = np.asarray(Y_calc).flatten()
        X_data = np.asarray(X_data).flatten()
        Y_data = np.asarray(Y_data).flatten()
        
        # Убираем NaN и Inf
        valid_mask = (np.isfinite(X_calc) & np.isfinite(Y_calc) & 
                     np.isfinite(X_data) & np.isfinite(Y_data) &
                     (X_calc > 0) & (Y_calc > 0) & (X_data > 0) & (Y_data > 0))
        
        if np.sum(valid_mask) < 3:
            return np.array([0.0, 0.0, 0.0, 0.0, 0.0])
        
        X_calc_valid = X_calc[valid_mask]
        Y_calc_valid = Y_calc[valid_mask]
        X_data_valid = X_data[valid_mask]
        Y_data_valid = Y_data[valid_mask]
        
        # Логарифмические координаты
        log_X_calc = np.log10(X_calc_valid)
        log_Y_calc = np.log10(Y_calc_valid)
        log_X_data = np.log10(X_data_valid)
        log_Y_data = np.log10(Y_data_valid)
        
        # Сортируем по X
        sort_idx_calc = np.argsort(log_X_calc)
        sort_idx_data = np.argsort(log_X_data)
        
        log_X_calc_sorted = log_X_calc[sort_idx_calc]
        log_Y_calc_sorted = log_Y_calc[sort_idx_calc]
        log_X_data_sorted = log_X_data[sort_idx_data]
        log_Y_data_sorted = log_Y_data[sort_idx_data]
        
        # Вычисляем наклоны
        dY_calc = np.diff(log_Y_calc_sorted)
        dY_data = np.diff(log_Y_data_sorted)
        dX_calc = np.diff(log_X_calc_sorted)
        dX_data = np.diff(log_X_data_sorted)
        
        valid_calc_mask = np.abs(dX_calc) > 1e-10
        valid_data_mask = np.abs(dX_data) > 1e-10
        
        if np.any(valid_calc_mask) and np.any(valid_data_mask):
            slopes_calc = dY_calc[valid_calc_mask] / dX_calc[valid_calc_mask]
            slopes_data = dY_data[valid_data_mask] / dX_data[valid_data_mask]
            
            # Признак 1: Разница средних наклонов
            mean_slope_diff = float(np.mean(slopes_calc) - np.mean(slopes_data))
            
            # Признак 2: Разница медианных наклонов
            median_slope_diff = float(np.median(slopes_calc) - np.median(slopes_data))
            
            # Признак 3: Отношение диапазонов Y
            Y_calc_range = np.max(Y_calc_valid) / np.min(Y_calc_valid)
            Y_data_range = np.max(Y_data_valid) / np.min(Y_data_valid)
            if Y_data_range > 1e-10:
                range_ratio = Y_calc_range / Y_data_range
            else:
                range_ratio = 1.0
            
            # Признак 4: Среднее относительное отклонение Y
            # Интерполируем на общую сетку для сравнения
            from scipy.interpolate import interp1d
            try:
                X_min = max(np.min(log_X_calc_sorted), np.min(log_X_data_sorted))
                X_max = min(np.max(log_X_calc_sorted), np.max(log_X_data_sorted))
                if X_max > X_min:
                    X_common = np.linspace(X_min, X_max, min(30, len(X_calc_valid)))
                    interp_calc = interp1d(log_X_calc_sorted, log_Y_calc_sorted,
                                          kind='linear', bounds_error=False, fill_value='extrapolate')
                    interp_data = interp1d(log_X_data_sorted, log_Y_data_sorted,
                                          kind='linear', bounds_error=False, fill_value='extrapolate')
                    Y_calc_interp = 10 ** interp_calc(X_common)
                    Y_data_interp = 10 ** interp_data(X_common)
                    valid_interp = (Y_calc_interp > 0) & (Y_data_interp > 0)
                    if np.any(valid_interp):
                        rel_diff = np.mean(np.abs(Y_calc_interp[valid_interp] - Y_data_interp[valid_interp]) / 
                                         (Y_data_interp[valid_interp] + 1e-10))
                    else:
                        rel_diff = 0.0
                else:
                    rel_diff = 0.0
            except Exception:
                rel_diff = 0.0
            
            # Признак 5: Максимальная разница наклонов
            max_slope_diff = float(np.max(np.abs(slopes_calc)) - np.max(np.abs(slopes_data)))
        else:
            mean_slope_diff = 0.0
            median_slope_diff = 0.0
            range_ratio = 1.0
            rel_diff = 0.0
            max_slope_diff = 0.0
        
        features = np.array([
            mean_slope_diff,      # Признак 1: разница средних наклонов
            median_slope_diff,   # Признак 2: разница медианных наклонов
            range_ratio,         # Признак 3: отношение диапазонов Y
            rel_diff,            # Признак 4: среднее относительное отклонение
            max_slope_diff       # Признак 5: максимальная разница наклонов
        ])
        
        return features
    
    def fit(self, P_curves: list, Q_curves: list,
            X_calc_curves: list, Y_calc_curves: list,
            X_data_curves: list, Y_data_curves: list,
            h_values: Optional[list] = None,
            L_values: Optional[list] = None,
            W_values: Optional[list] = None,
            labels: Optional[np.ndarray] = None) -> 'CurveClassifier':
        """
        Обучает классификатор на массиве P-Q признаков и метках, определённых из сравнения X-Y кривых.
        
        Если labels не предоставлены, автоматически вычисляет классы на основе метрики отношения крутости.
        Класс 0: расчётная круче эталонной (нужно ужимать)
        Класс 1: расчётная положе эталонной (нужно растягивать)
        
        :param P_curves: Список массивов давления P для каждой кривой
        :param Q_curves: Список массивов дебита Q для каждой кривой
        :param X_calc_curves: Список массивов расчётных X для каждой кривой (для определения меток)
        :param Y_calc_curves: Список массивов расчётных Y для каждой кривой (для определения меток)
        :param X_data_curves: Список массивов эталонных X для каждой кривой (для определения меток)
        :param Y_data_curves: Список массивов эталонных Y для каждой кривой (для определения меток)
        :param h_values: Опциональный список значений h (толщина пласта) для каждой кривой
        :param L_values: Опциональный список значений L (длина трещины) для каждой кривой
        :param W_values: Опциональный список значений W (ширина трещины) для каждой кривой
        :param labels: Опциональные метки классов (0 или 1). Если None, вычисляются автоматически
        :return: self
        """
        if len(P_curves) != len(Q_curves) or len(P_curves) != len(X_calc_curves):
            raise ValueError(f"Количество кривых не совпадает: P={len(P_curves)}, Q={len(Q_curves)}, "
                           f"X_calc={len(X_calc_curves)}")
        
        # Вычисляем признаки из P и Q для всех кривых
        features_list = []
        steepness_ratio_values = []
        
        # Обрабатываем опциональные параметры скважины
        if h_values is None:
            h_values = [None] * len(P_curves)
        if L_values is None:
            L_values = [None] * len(P_curves)
        if W_values is None:
            W_values = [None] * len(P_curves)
        
        for P, Q, X_calc, Y_calc, X_data, Y_data, h, L, W in zip(
            P_curves, Q_curves, X_calc_curves, Y_calc_curves, X_data_curves, Y_data_curves,
            h_values, L_values, W_values
        ):
            # Извлекаем признаки из P, Q и параметров скважины
            pq_features = self.extract_pq_features(P, Q, h=h, L=L, W=W)
            features_list.append(pq_features)
            
            # Вычисляем метрику для определения метки (сравнение расчётной и эталонной)
            steepness_ratio_values.append(self.compute_curve_classification_metric(X_calc, Y_calc, X_data, Y_data))
        
        X_features = np.array(features_list)
        steepness_ratio_array = np.array(steepness_ratio_values)
        
        # Если метки не предоставлены, вычисляем их на основе среднего арифметического
        # Положительное значение = расчётная круче (класс 0 - нужно ужимать)
        # Отрицательное значение = расчётная положе (класс 1 - нужно растягивать)
        if labels is None:
            # Используем среднее арифметическое вместо медианы
            self.median_steepness = np.mean(steepness_ratio_array)
            # Если метрика > среднего, значит расчётная круче → класс 0 (ужимать)
            # Если метрика < среднего, значит расчётная положе → класс 1 (растягивать)
            labels = (steepness_ratio_array > self.median_steepness).astype(int)
        else:
            labels = np.asarray(labels).flatten()
            # Вычисляем среднее для информации
            self.median_steepness = np.mean(steepness_ratio_array)
        
        if len(labels) != len(P_curves):
            raise ValueError(f"Количество меток ({len(labels)}) не совпадает с количеством кривых ({len(P_curves)})")
        
        # Стандартизация признаков
        if self.use_scaling:
            X_features = self.scaler.fit_transform(X_features)
        
        # Обучение классификатора с регуляризацией
        # Нормализация данных уже применена выше через self.scaler (если use_scaling=True)
        if self.classifier_type == 'logistic':
            # C=1.0 - стандартная регуляризация
            self.classifier = LogisticRegression(C=1.0, random_state=42, max_iter=1000)
        elif self.classifier_type == 'tree':
            # Ограничение глубины для предотвращения переобучения
            self.classifier = DecisionTreeClassifier(random_state=42, max_depth=5)
        elif self.classifier_type == 'forest':
            # Ограничение глубины для предотвращения переобучения
            self.classifier = RandomForestClassifier(random_state=42, n_estimators=50, max_depth=5)
        else:
            raise ValueError(f"Неизвестный тип классификатора: {self.classifier_type}")
        
        self.classifier.fit(X_features, labels)
        self.is_fitted = True
        
        return self
    
    def predict(self, P: np.ndarray, Q: np.ndarray,
                h: Optional[float] = None, L: Optional[float] = None, 
                W: Optional[float] = None) -> int:
        """
        Предсказывает класс коррекции кривой на основе P, Q и параметров скважины.
        
        Класс 0: расчётная круче эталонной (нужно ужимать)
        Класс 1: расчётная положе эталонной (нужно растягивать)
        
        :param P: Давление (временной ряд)
        :param Q: Дебит (временной ряд)
        :param h: Толщина пласта (опционально)
        :param L: Длина трещины (опционально)
        :param W: Ширина трещины (опционально)
        :return: Класс кривой (0 или 1)
        """
        if not self.is_fitted:
            raise RuntimeError("Классификатор не обучен. Вызовите fit() сначала.")
        
        # Извлекаем признаки из P, Q и параметров скважины
        features = self.extract_pq_features(P, Q, h=h, L=L, W=W).reshape(1, -1)
        
        if self.use_scaling:
            features = self.scaler.transform(features)
        
        prediction = self.classifier.predict(features)[0]
        return int(prediction)
    
    def predict_proba(self, P: np.ndarray, Q: np.ndarray,
                     h: Optional[float] = None, L: Optional[float] = None, 
                     W: Optional[float] = None) -> Tuple[float, float]:
        """
        Возвращает вероятности принадлежности к классам на основе P, Q и параметров скважины.
        
        :param P: Давление (временной ряд)
        :param Q: Дебит (временной ряд)
        :param h: Толщина пласта (опционально)
        :param L: Длина трещины (опционально)
        :param W: Ширина трещины (опционально)
        :return: Кортеж (вероятность класса 0, вероятность класса 1)
        """
        if not self.is_fitted:
            raise RuntimeError("Классификатор не обучен. Вызовите fit() сначала.")
        
        # Извлекаем признаки из P, Q и параметров скважины
        features = self.extract_pq_features(P, Q, h=h, L=L, W=W).reshape(1, -1)
        
        if self.use_scaling:
            features = self.scaler.transform(features)
        
        proba = self.classifier.predict_proba(features)[0]
        return float(proba[0]), float(proba[1])
    
    def get_classification_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о классификаторе.
        
        :return: Словарь с информацией
        """
        if not self.is_fitted:
            return {
                "fitted": False,
                "classifier_type": self.classifier_type,
                "median_steepness": None,
                "message": "Классификатор не обучен"
            }
        
        return {
            "fitted": True,
            "classifier_type": self.classifier_type,
            "median_steepness": float(self.median_steepness) if self.median_steepness is not None else None,
            "use_scaling": self.use_scaling,
            "message": f"Классификатор обучен (тип: {self.classifier_type}, среднее отношение крутости: {self.median_steepness:.4f})"
        }
