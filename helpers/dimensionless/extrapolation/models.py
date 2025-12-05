"""
Модели для экстраполяции временных рядов.
Включает экспоненциальную, логарифмическую и ARIMA модели.
"""

import numpy as np
from typing import Optional, Dict, Any, Tuple
from sklearn.base import BaseEstimator
from scipy.optimize import curve_fit
from scipy.stats import linregress
import warnings

warnings.filterwarnings('ignore')

# Попытка импортировать ARIMA
try:
    from statsmodels.tsa.arima.model import ARIMA
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False


class ExponentialTrendModel(BaseEstimator):
    """
    Модель экспоненциального тренда: y(t) = a * exp(-b * t) + c
    Подходит для давления и дебита (экспоненциальное затухание).
    """
    
    def __init__(self):
        self.a_ = None
        self.b_ = None
        self.c_ = None
        self.fitted = False
    
    def fit(self, t: np.ndarray, y: np.ndarray):
        """
        Обучает модель на данных.
        
        Args:
            t: Временные метки (должны быть положительными)
            y: Значения для обучения (должны быть положительными)
        """
        t = np.asarray(t).flatten()
        y = np.asarray(y).flatten()
        
        # Убираем NaN и Inf
        mask = np.isfinite(t) & np.isfinite(y) & (y > 0) & (t >= 0)
        if np.sum(mask) < 3:
            raise ValueError("Недостаточно валидных данных для экспоненциальной модели")
        
        t_clean = t[mask]
        y_clean = y[mask]
        
        # Нормализуем время для числовой устойчивости
        t_min = np.min(t_clean)
        t_shifted = t_clean - t_min
        
        # Начальные приближения
        y_max = np.max(y_clean)
        y_min = np.min(y_clean)
        c_init = y_min * 0.9  # Асимптота снизу
        a_init = (y_max - c_init)
        b_init = 1.0 / (np.max(t_shifted) + 1e-10)
        
        # Функция для подгонки
        def exp_func(t_val, a, b, c):
            return a * np.exp(-b * t_val) + c
        
        try:
            # Подгонка экспоненты
            popt, _ = curve_fit(
                exp_func,
                t_shifted,
                y_clean,
                p0=[a_init, b_init, c_init],
                bounds=([0, 0, 0], [np.inf, np.inf, y_max]),
                maxfev=5000
            )
            
            self.a_ = popt[0]
            self.b_ = popt[1]
            self.c_ = popt[2]
            self.t_min_ = t_min
            self.fitted = True
            
        except Exception as e:
            # Fallback: линейная регрессия в логарифмическом пространстве
            y_log = np.log(np.maximum(y_clean, 1e-10))
            slope, intercept = linregress(t_shifted, y_log)[:2]
            
            self.a_ = np.exp(intercept)
            self.b_ = -slope
            self.c_ = 0.0
            self.t_min_ = t_min
            self.fitted = True
        
        return self
    
    def predict(self, t: np.ndarray) -> np.ndarray:
        """Предсказывает значения для новых временных точек."""
        if not self.fitted:
            raise ValueError("Модель не обучена")
        
        t = np.asarray(t).flatten()
        t_shifted = t - self.t_min_
        
        # Предсказание
        y_pred = self.a_ * np.exp(-self.b_ * np.maximum(t_shifted, 0)) + self.c_
        
        # Защита от отрицательных значений
        y_pred = np.maximum(y_pred, 0.0)
        
        return y_pred


class LogarithmicTrendModel(BaseEstimator):
    """
    Модель логарифмического тренда: y(t) = a * log(t + 1) + b
    Подходит для медленно меняющихся процессов.
    """
    
    def __init__(self):
        self.a_ = None
        self.b_ = None
        self.fitted = False
    
    def fit(self, t: np.ndarray, y: np.ndarray):
        """
        Обучает модель на данных.
        
        Args:
            t: Временные метки (должны быть положительными)
            y: Значения для обучения
        """
        t = np.asarray(t).flatten()
        y = np.asarray(y).flatten()
        
        # Убираем NaN и Inf
        mask = np.isfinite(t) & np.isfinite(y) & (t > 0)
        if np.sum(mask) < 2:
            raise ValueError("Недостаточно валидных данных для логарифмической модели")
        
        t_clean = t[mask]
        y_clean = y[mask]
        
        # Линейная регрессия в логарифмическом пространстве
        log_t = np.log(t_clean + 1)
        
        try:
            slope, intercept = linregress(log_t, y_clean)[:2]
            self.a_ = slope
            self.b_ = intercept
            self.fitted = True
        except Exception:
            # Fallback: среднее значение
            self.a_ = 0.0
            self.b_ = np.mean(y_clean)
            self.fitted = True
        
        return self
    
    def predict(self, t: np.ndarray) -> np.ndarray:
        """Предсказывает значения для новых временных точек."""
        if not self.fitted:
            raise ValueError("Модель не обучена")
        
        t = np.asarray(t).flatten()
        log_t = np.log(np.maximum(t + 1, 1))
        
        y_pred = self.a_ * log_t + self.b_
        
        # Защита от отрицательных значений (если применимо)
        y_pred = np.maximum(y_pred, 0.0)
        
        return y_pred


class ARIMAModel(BaseEstimator):
    """
    ARIMA модель для временных рядов.
    Используется только если statsmodels доступен.
    """
    
    def __init__(self, order: Tuple[int, int, int] = (1, 1, 1)):
        """
        Args:
            order: Порядок ARIMA (p, d, q)
        """
        if not ARIMA_AVAILABLE:
            raise ImportError("statsmodels не установлен. Установите: pip install statsmodels")
        
        self.order = order
        self.model_ = None
        self.fitted = False
    
    def fit(self, y: np.ndarray):
        """
        Обучает ARIMA модель.
        
        Args:
            y: Временной ряд для обучения (одномерный массив)
        """
        y = np.asarray(y).flatten()
        
        # Убираем NaN
        mask = np.isfinite(y)
        if np.sum(mask) < 5:
            raise ValueError("Недостаточно данных для ARIMA модели")
        
        y_clean = y[mask]
        
        try:
            self.model_ = ARIMA(y_clean, order=self.order)
            self.model_fit_ = self.model_.fit()
            self.fitted = True
        except Exception as e:
            # Fallback: простая модель
            try:
                self.model_ = ARIMA(y_clean, order=(1, 0, 0))
                self.model_fit_ = self.model_.fit()
                self.fitted = True
            except Exception:
                raise ValueError(f"Не удалось обучить ARIMA модель: {e}")
        
        return self
    
    def predict(self, n_periods: int) -> np.ndarray:
        """
        Предсказывает n_periods шагов вперёд.
        
        Args:
            n_periods: Количество шагов для предсказания
        
        Returns:
            Предсказанные значения
        """
        if not self.fitted:
            raise ValueError("Модель не обучена")
        
        try:
            forecast = self.model_fit_.forecast(steps=n_periods)
            y_pred = np.asarray(forecast)
            
            # Защита от отрицательных значений
            y_pred = np.maximum(y_pred, 0.0)
            
            return y_pred
        except Exception as e:
            # Fallback: последнее значение
            last_value = self.model_fit_.fittedvalues.iloc[-1] if hasattr(self.model_fit_, 'fittedvalues') else 0.0
            return np.full(n_periods, last_value)


def compare_models(
    t_train: np.ndarray,
    y_train: np.ndarray,
    t_test: Optional[np.ndarray] = None,
    y_test: Optional[np.ndarray] = None,
    use_arima: bool = ARIMA_AVAILABLE
) -> Dict[str, Any]:
    """
    Сравнивает экспоненциальную, логарифмическую и ARIMA модели.
    
    Args:
        t_train: Временные метки для обучения
        y_train: Значения для обучения
        t_test: Временные метки для тестирования (опционально)
        y_test: Значения для тестирования (опционально)
        use_arima: Использовать ли ARIMA модель
    
    Returns:
        Словарь с результатами сравнения:
        {
            'best_model': название лучшей модели,
            'best_model_obj': объект лучшей модели,
            'scores': {model_name: score},
            'predictions': {model_name: predictions}
        }
    """
    results = {
        'scores': {},
        'predictions': {},
        'models': {}
    }
    
    # Экспоненциальная модель
    try:
        exp_model = ExponentialTrendModel()
        exp_model.fit(t_train, y_train)
        
        if t_test is not None:
            exp_pred = exp_model.predict(t_test)
            if y_test is not None:
                # RMSE на тестовых данных
                rmse = np.sqrt(np.mean((y_test - exp_pred) ** 2))
                results['scores']['exponential'] = rmse
            results['predictions']['exponential'] = exp_pred
        else:
            # R² на обучающих данных
            train_pred = exp_model.predict(t_train)
            ss_res = np.sum((y_train - train_pred) ** 2)
            ss_tot = np.sum((y_train - np.mean(y_train)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            results['scores']['exponential'] = -r2  # Отрицательный для минимизации
        
        results['models']['exponential'] = exp_model
    except Exception as e:
        results['scores']['exponential'] = np.inf
        results['predictions']['exponential'] = None
    
    # Логарифмическая модель
    try:
        log_model = LogarithmicTrendModel()
        log_model.fit(t_train, y_train)
        
        if t_test is not None:
            log_pred = log_model.predict(t_test)
            if y_test is not None:
                rmse = np.sqrt(np.mean((y_test - log_pred) ** 2))
                results['scores']['logarithmic'] = rmse
            results['predictions']['logarithmic'] = log_pred
        else:
            train_pred = log_model.predict(t_train)
            ss_res = np.sum((y_train - train_pred) ** 2)
            ss_tot = np.sum((y_train - np.mean(y_train)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            results['scores']['logarithmic'] = -r2
        
        results['models']['logarithmic'] = log_model
    except Exception as e:
        results['scores']['logarithmic'] = np.inf
        results['predictions']['logarithmic'] = None
    
    # ARIMA модель
    if use_arima:
        try:
            arima_model = ARIMAModel(order=(1, 1, 1))
            arima_model.fit(y_train)
            
            if t_test is not None:
                n_periods = len(t_test)
                arima_pred = arima_model.predict(n_periods)
                if y_test is not None:
                    rmse = np.sqrt(np.mean((y_test - arima_pred) ** 2))
                    results['scores']['arima'] = rmse
                results['predictions']['arima'] = arima_pred
            else:
                # Используем последнее значение как оценку
                results['scores']['arima'] = np.inf
            
            results['models']['arima'] = arima_model
        except Exception as e:
            results['scores']['arima'] = np.inf
            results['predictions']['arima'] = None
    
    # Выбираем лучшую модель
    if results['scores']:
        best_model_name = min(results['scores'], key=results['scores'].get)
        results['best_model'] = best_model_name
        results['best_model_obj'] = results['models'].get(best_model_name)
    else:
        results['best_model'] = 'exponential'
        results['best_model_obj'] = results['models'].get('exponential')
    
    return results

