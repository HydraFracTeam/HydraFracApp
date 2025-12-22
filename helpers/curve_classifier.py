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
        :param use_scaling: Использовать ли стандартизацию признаков
        """
        self.classifier_type = classifier_type
        self.use_scaling = use_scaling
        self.classifier = None
        self.scaler = StandardScaler() if use_scaling else None
        self.median_steepness = None
        self.is_fitted = False
        
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
    
    def fit(self, X_calc_curves: list, Y_calc_curves: list,
            X_data_curves: list, Y_data_curves: list,
            labels: Optional[np.ndarray] = None) -> 'CurveClassifier':
        """
        Обучает классификатор на массиве расчётных и эталонных кривых.
        
        Если labels не предоставлены, автоматически вычисляет классы на основе медианы метрики отношения крутости.
        Класс 0: расчётная круче эталонной (нужно ужимать)
        Класс 1: расчётная положе эталонной (нужно растягивать)
        
        :param X_calc_curves: Список массивов расчётных X для каждой кривой
        :param Y_calc_curves: Список массивов расчётных Y для каждой кривой
        :param X_data_curves: Список массивов эталонных X для каждой кривой
        :param Y_data_curves: Список массивов эталонных Y для каждой кривой
        :param labels: Опциональные метки классов (0 или 1). Если None, вычисляются автоматически
        :return: self
        """
        if len(X_calc_curves) != len(Y_calc_curves) or len(X_calc_curves) != len(X_data_curves) or len(X_calc_curves) != len(Y_data_curves):
            raise ValueError(f"Количество кривых не совпадает: X_calc={len(X_calc_curves)}, Y_calc={len(Y_calc_curves)}, "
                           f"X_data={len(X_data_curves)}, Y_data={len(Y_data_curves)}")
        
        # Вычисляем признаки для всех кривых (сравнение расчётной и эталонной)
        features_list = []
        steepness_ratio_values = []
        
        for X_calc, Y_calc, X_data, Y_data in zip(X_calc_curves, Y_calc_curves, X_data_curves, Y_data_curves):
            features = self.compute_curve_features(X_calc, Y_calc, X_data, Y_data)
            features_list.append(features)
            # Используем новую метрику классификации на основе формы кривой
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
        
        if len(labels) != len(X_calc_curves):
            raise ValueError(f"Количество меток ({len(labels)}) не совпадает с количеством кривых ({len(X_calc_curves)})")
        
        # Стандартизация признаков
        if self.use_scaling:
            X_features = self.scaler.fit_transform(X_features)
        
        # Обучение классификатора
        if self.classifier_type == 'logistic':
            self.classifier = LogisticRegression(random_state=42, max_iter=1000)
        elif self.classifier_type == 'tree':
            self.classifier = DecisionTreeClassifier(random_state=42, max_depth=5)
        elif self.classifier_type == 'forest':
            self.classifier = RandomForestClassifier(random_state=42, n_estimators=50, max_depth=5)
        else:
            raise ValueError(f"Неизвестный тип классификатора: {self.classifier_type}")
        
        self.classifier.fit(X_features, labels)
        self.is_fitted = True
        
        return self
    
    def predict(self, X_calc: np.ndarray, Y_calc: np.ndarray,
                X_data: np.ndarray, Y_data: np.ndarray) -> int:
        """
        Предсказывает класс коррекции кривой.
        
        Класс 0: расчётная круче эталонной (нужно ужимать)
        Класс 1: расчётная положе эталонной (нужно растягивать)
        
        :param X_calc: Расчётные значения X
        :param Y_calc: Расчётные значения Y
        :param X_data: Эталонные значения X
        :param Y_data: Эталонные значения Y
        :return: Класс кривой (0 или 1)
        """
        if not self.is_fitted:
            raise RuntimeError("Классификатор не обучен. Вызовите fit() сначала.")
        
        features = self.compute_curve_features(X_calc, Y_calc, X_data, Y_data).reshape(1, -1)
        
        if self.use_scaling:
            features = self.scaler.transform(features)
        
        prediction = self.classifier.predict(features)[0]
        return int(prediction)
    
    def predict_proba(self, X_calc: np.ndarray, Y_calc: np.ndarray,
                     X_data: np.ndarray, Y_data: np.ndarray) -> Tuple[float, float]:
        """
        Возвращает вероятности принадлежности к классам.
        
        :param X_calc: Расчётные значения X
        :param Y_calc: Расчётные значения Y
        :param X_data: Эталонные значения X
        :param Y_data: Эталонные значения Y
        :return: Кортеж (вероятность класса 0, вероятность класса 1)
        """
        if not self.is_fitted:
            raise RuntimeError("Классификатор не обучен. Вызовите fit() сначала.")
        
        features = self.compute_curve_features(X_calc, Y_calc, X_data, Y_data).reshape(1, -1)
        
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
