import numpy as np
import pandas as pd
from typing import Tuple, Optional, List
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, r2_score
from scipy import signal
from scipy.interpolate import interp1d, UnivariateSpline
import warnings

warnings.filterwarnings('ignore')


class MLInterpolator:
    """ML-интерполятор для временных рядов"""
    
    def __init__(self, method: str = 'random_forest'):
        self.method = method
        self.model = None
        self.is_fitted = False
        
    def fit(self, time: pd.Series, values: pd.Series) -> 'MLInterpolator':
        """Обучение модели на доступных данных"""
        # Очищаем данные от NaN
        valid_mask = ~(pd.isna(time) | pd.isna(values))
        time_clean = time[valid_mask]
        values_clean = values[valid_mask]
        
        if len(time_clean) < 3:
            raise ValueError("Недостаточно данных для обучения")
        
        # Подготавливаем признаки
        X = self._prepare_features(time_clean)
        y = values_clean.values
        
        # Выбираем модель
        if self.method == 'random_forest':
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        elif self.method == 'polynomial':
            self.model = Pipeline([
                ('poly', PolynomialFeatures(degree=3)),
                ('linear', LinearRegression())
            ])
        elif self.method == 'ridge':
            self.model = Ridge(alpha=1.0)
        else:
            raise ValueError(f"Неизвестный метод: {self.method}")
        
        # Обучаем модель
        self.model.fit(X, y)
        self.is_fitted = True
        return self
    
    def _prepare_features(self, time: pd.Series) -> np.ndarray:
        """Подготовка признаков для ML модели"""
        time_norm = (time - time.min()) / (time.max() - time.min())
        
        features = np.column_stack([
            time_norm.values,
            np.sin(2 * np.pi * time_norm),  # Периодические признаки
            np.cos(2 * np.pi * time_norm),
            time_norm.values ** 2,  # Полиномиальные признаки
            time_norm.values ** 3
        ])
        return features
    
    def predict(self, time: pd.Series) -> pd.Series:
        """Предсказание значений для новых временных точек"""
        if not self.is_fitted:
            raise ValueError("Модель не обучена")
        
        X = self._prepare_features(time)
        predictions = self.model.predict(X)
        return pd.Series(predictions, index=time.index, name=f'ML_{self.method}_interpolated')


class MLFilter:
    """ML-фильтр для удаления шума из временных рядов"""
    
    def __init__(self, method: str = 'savitzky_golay'):
        self.method = method
        
    def filter(self, values: pd.Series, **kwargs) -> pd.Series:
        """Применение фильтра к данным"""
        if self.method == 'savitzky_golay':
            window_length = kwargs.get('window_length', 5)
            polyorder = kwargs.get('polyorder', 2)
            return self._savitzky_golay_filter(values, window_length, polyorder)
        
        elif self.method == 'gaussian':
            sigma = kwargs.get('sigma', 1.0)
            return self._gaussian_filter(values, sigma)
        
        elif self.method == 'median':
            kernel_size = kwargs.get('kernel_size', 5)
            return self._median_filter(values, kernel_size)
        
        elif self.method == 'kalman':
            return self._kalman_filter(values)
        
        else:
            raise ValueError(f"Неизвестный метод фильтрации: {self.method}")
    
    def _savitzky_golay_filter(self, values: pd.Series, window_length: int, polyorder: int) -> pd.Series:
        """Фильтр Савицкого-Голея"""
        try:
            filtered = signal.savgol_filter(values.values, window_length, polyorder)
            return pd.Series(filtered, index=values.index, name=f'filtered_{self.method}')
        except ValueError:
            # Если параметры некорректны, возвращаем исходные данные
            return values
    
    def _gaussian_filter(self, values: pd.Series, sigma: float) -> pd.Series:
        """Гауссовский фильтр"""
        from scipy.ndimage import gaussian_filter1d
        filtered = gaussian_filter1d(values.values, sigma=sigma)
        return pd.Series(filtered, index=values.index, name=f'filtered_{self.method}')
    
    def _median_filter(self, values: pd.Series, kernel_size: int) -> pd.Series:
        """Медианный фильтр"""
        from scipy.ndimage import median_filter
        filtered = median_filter(values.values, size=kernel_size)
        return pd.Series(filtered, index=values.index, name=f'filtered_{self.method}')
    
    def _kalman_filter(self, values: pd.Series) -> pd.Series:
        """Упрощенный фильтр Калмана"""
        # Простая реализация одномерного фильтра Калмана
        n = len(values)
        if n < 2:
            return values
        
        # Параметры фильтра
        Q = 0.1  # Процессный шум
        R = 0.1  # Шум измерений
        
        # Инициализация
        x = values.iloc[0]  # Состояние
        P = 1.0  # Ковариация
        
        filtered_values = [x]
        
        for i in range(1, n):
            # Предсказание
            x_pred = x
            P_pred = P + Q
            
            # Обновление
            K = P_pred / (P_pred + R)  # Коэффициент Калмана
            x = x_pred + K * (values.iloc[i] - x_pred)
            P = (1 - K) * P_pred
            
            filtered_values.append(x)
        
        return pd.Series(filtered_values, index=values.index, name=f'filtered_{self.method}')


class AdvancedInterpolator:
    """Продвинутый интерполятор с различными методами"""
    
    @staticmethod
    def spline_interpolation(time: pd.Series, values: pd.Series, 
                           new_time: pd.Series, method: str = 'cubic') -> pd.Series:
        """Сплайн-интерполяция"""
        # Очищаем данные
        valid_mask = ~(pd.isna(time) | pd.isna(values))
        time_clean = time[valid_mask]
        values_clean = values[valid_mask]
        
        if len(time_clean) < 2:
            return pd.Series(index=new_time.index, dtype=float)
        
        try:
            if method == 'cubic':
                spline = UnivariateSpline(time_clean, values_clean, s=0)
            else:
                spline = interp1d(time_clean, values_clean, kind=method, 
                                bounds_error=False, fill_value='extrapolate')
            
            interpolated = spline(new_time)
            return pd.Series(interpolated, index=new_time.index, name=f'spline_{method}')
        except Exception:
            # Fallback к линейной интерполяции
            return pd.Series(np.interp(new_time, time_clean, values_clean), 
                           index=new_time.index, name='linear_fallback')
    
    @staticmethod
    def fourier_interpolation(time: pd.Series, values: pd.Series, 
                            new_time: pd.Series, n_harmonics: int = 10) -> pd.Series:
        """Интерполяция на основе преобразования Фурье"""
        valid_mask = ~(pd.isna(time) | pd.isna(values))
        time_clean = time[valid_mask]
        values_clean = values[valid_mask]
        
        if len(time_clean) < 4:
            return pd.Series(index=new_time.index, dtype=float)
        
        try:
            # Вычисляем FFT
            fft = np.fft.fft(values_clean)
            freqs = np.fft.fftfreq(len(values_clean))
            
            # Оставляем только низкочастотные компоненты
            fft[n_harmonics:] = 0
            fft[-n_harmonics:] = 0
            
            # Обратное преобразование
            reconstructed = np.fft.ifft(fft).real
            
            # Интерполируем на новые временные точки
            interpolated = np.interp(new_time, time_clean, reconstructed)
            return pd.Series(interpolated, index=new_time.index, name='fourier_interp')
        except Exception:
            return pd.Series(index=new_time.index, dtype=float)


def apply_ml_interpolation(time: pd.Series, values: pd.Series, 
                          method: str = 'random_forest') -> pd.Series:
    """Применение ML-интерполяции к данным"""
    interpolator = MLInterpolator(method=method)
    try:
        interpolator.fit(time, values)
        return interpolator.predict(time)
    except Exception as e:
        print(f"Ошибка ML-интерполяции: {e}")
        return values


def apply_ml_filter(values: pd.Series, method: str = 'savitzky_golay', **kwargs) -> pd.Series:
    """Применение ML-фильтрации к данным"""
    filter_obj = MLFilter(method=method)
    try:
        return filter_obj.filter(values, **kwargs)
    except Exception as e:
        print(f"Ошибка ML-фильтрации: {e}")
        return values


def detect_outliers(values: pd.Series, method: str = 'iqr', threshold: float = 1.5) -> pd.Series:
    """Обнаружение выбросов в данных"""
    if method == 'iqr':
        Q1 = values.quantile(0.25)
        Q3 = values.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        outliers = (values < lower_bound) | (values > upper_bound)
    
    elif method == 'zscore':
        z_scores = np.abs((values - values.mean()) / values.std())
        outliers = z_scores > threshold
    
    elif method == 'modified_zscore':
        median = values.median()
        mad = np.median(np.abs(values - median))
        modified_z_scores = 0.6745 * (values - median) / mad
        outliers = np.abs(modified_z_scores) > threshold
    
    else:
        raise ValueError(f"Неизвестный метод обнаружения выбросов: {method}")
    
    # Убеждаемся, что возвращаем pandas Series
    if isinstance(outliers, np.ndarray):
        return pd.Series(outliers, index=values.index)
    return outliers


def clean_data(time: pd.Series, values: pd.Series, 
               outlier_method: str = 'iqr', filter_method: str = 'savitzky_golay') -> Tuple[pd.Series, pd.Series]:
    """Комплексная очистка данных от выбросов и шума"""
    # Обнаруживаем выбросы
    outliers = detect_outliers(values, method=outlier_method)
    
    # Удаляем выбросы
    clean_time = time[~outliers]
    clean_values = values[~outliers]
    
    # Применяем фильтрацию
    filtered_values = apply_ml_filter(clean_values, method=filter_method)
    
    return clean_time, filtered_values
