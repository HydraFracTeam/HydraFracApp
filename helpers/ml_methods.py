import numpy as np
import pandas as pd
from typing import Tuple, Optional, List, Dict, Union
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, Matern
from scipy import signal
from scipy.interpolate import interp1d, UnivariateSpline, RBFInterpolator, griddata
from scipy.spatial.distance import pdist, squareform
from scipy.optimize import minimize
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


class KrigingInterpolator:
    """Кригинг-интерполяция для пространственных данных"""
    
    def __init__(self, variogram_model: str = 'spherical', nugget: float = 0.0):
        self.variogram_model = variogram_model
        self.nugget = nugget
        self.fitted = False
        self.range_param = None
        self.sill = None
        
    def fit(self, time: pd.Series, values: pd.Series) -> 'KrigingInterpolator':
        """Обучение модели вариограммы"""
        valid_mask = ~(pd.isna(time) | pd.isna(values))
        time_clean = time[valid_mask].values
        values_clean = values[valid_mask].values
        
        if len(time_clean) < 3:
            raise ValueError("Недостаточно данных для кригинга")
        
        # Вычисляем эмпирическую вариограмму
        distances, variogram = self._compute_empirical_variogram(time_clean, values_clean)
        
        # Подгоняем теоретическую модель
        self._fit_variogram_model(distances, variogram)
        self.fitted = True
        return self
    
    def _compute_empirical_variogram(self, time: np.ndarray, values: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Вычисление эмпирической вариограммы"""
        n = len(time)
        distances = []
        variogram_values = []
        
        for i in range(n):
            for j in range(i + 1, n):
                dist = abs(time[i] - time[j])
                var_val = 0.5 * (values[i] - values[j]) ** 2
                distances.append(dist)
                variogram_values.append(var_val)
        
        return np.array(distances), np.array(variogram_values)
    
    def _fit_variogram_model(self, distances: np.ndarray, variogram: np.ndarray) -> None:
        """Подгонка теоретической модели вариограммы"""
        # Простая подгонка сферической модели
        max_dist = np.max(distances)
        max_var = np.max(variogram)
        
        self.range_param = max_dist * 0.6  # Примерная оценка
        self.sill = max_var * 0.8
        
    def _theoretical_variogram(self, h: np.ndarray) -> np.ndarray:
        """Теоретическая вариограмма"""
        if self.variogram_model == 'spherical':
            gamma = np.where(h <= self.range_param,
                           self.sill * (1.5 * h / self.range_param - 0.5 * (h / self.range_param) ** 3),
                           self.sill)
        elif self.variogram_model == 'exponential':
            gamma = self.sill * (1 - np.exp(-3 * h / self.range_param))
        else:  # linear
            gamma = self.sill * np.minimum(h / self.range_param, 1)
        
        return gamma + self.nugget
    
    def predict(self, time: pd.Series) -> pd.Series:
        """Предсказание с помощью кригинга"""
        if not self.fitted:
            raise ValueError("Модель не обучена")
        
        # Упрощенная реализация обычного кригинга
        time_values = time.values
        predictions = []
        
        for t in time_values:
            # Находим ближайшие точки
            distances = np.abs(time_values - t)
            weights = 1.0 / (distances + 1e-10)  # Простые веса
            weights = weights / np.sum(weights)
            
            # Взвешенное среднее
            pred = np.sum(weights * time_values)
            predictions.append(pred)
        
        return pd.Series(predictions, index=time.index, name='kriging_interpolated')


class RBFInterpolator:
    """Радиальные базисные функции для интерполяции"""
    
    def __init__(self, function: str = 'multiquadric', smoothing: float = 0.0):
        self.function = function
        self.smoothing = smoothing
        self.fitted = False
        self.rbf = None
        
    def fit(self, time: pd.Series, values: pd.Series) -> 'RBFInterpolator':
        """Обучение RBF модели"""
        valid_mask = ~(pd.isna(time) | pd.isna(values))
        time_clean = time[valid_mask].values
        values_clean = values[valid_mask].values
        
        if len(time_clean) < 2:
            raise ValueError("Недостаточно данных для RBF")
        
        # Создаем RBF интерполятор
        self.rbf = RBFInterpolator(time_clean.reshape(-1, 1), values_clean, 
                                 function=self.function, smoothing=self.smoothing)
        self.fitted = True
        return self
    
    def predict(self, time: pd.Series) -> pd.Series:
        """Предсказание с помощью RBF"""
        if not self.fitted:
            raise ValueError("Модель не обучена")
        
        time_values = time.values.reshape(-1, 1)
        predictions = self.rbf(time_values)
        return pd.Series(predictions, index=time.index, name='rbf_interpolated')


class GaussianProcessInterpolator:
    """Гауссовские процессы для интерполяции с оценкой неопределенности"""
    
    def __init__(self, kernel: str = 'rbf', alpha: float = 1e-10):
        self.kernel_type = kernel
        self.alpha = alpha
        self.fitted = False
        self.gp = None
        
    def fit(self, time: pd.Series, values: pd.Series) -> 'GaussianProcessInterpolator':
        """Обучение GP модели"""
        valid_mask = ~(pd.isna(time) | pd.isna(values))
        time_clean = time[valid_mask].values
        values_clean = values[valid_mask].values
        
        if len(time_clean) < 2:
            raise ValueError("Недостаточно данных для GP")
        
        # Выбираем ядро
        if self.kernel_type == 'rbf':
            kernel = RBF(length_scale=1.0) + WhiteKernel(noise_level=self.alpha)
        elif self.kernel_type == 'matern':
            kernel = Matern(length_scale=1.0, nu=1.5) + WhiteKernel(noise_level=self.alpha)
        else:
            kernel = RBF(length_scale=1.0) + WhiteKernel(noise_level=self.alpha)
        
        # Создаем GP регрессор
        self.gp = GaussianProcessRegressor(kernel=kernel, alpha=self.alpha, 
                                         random_state=42)
        
        # Обучаем
        X = time_clean.reshape(-1, 1)
        self.gp.fit(X, values_clean)
        self.fitted = True
        return self
    
    def predict(self, time: pd.Series, return_std: bool = True) -> Union[pd.Series, Tuple[pd.Series, pd.Series]]:
        """Предсказание с помощью GP"""
        if not self.fitted:
            raise ValueError("Модель не обучена")
        
        X = time.values.reshape(-1, 1)
        
        if return_std:
            mean, std = self.gp.predict(X, return_std=True)
            mean_series = pd.Series(mean, index=time.index, name='gp_interpolated')
            std_series = pd.Series(std, index=time.index, name='gp_std')
            return mean_series, std_series
        else:
            mean = self.gp.predict(X)
            return pd.Series(mean, index=time.index, name='gp_interpolated')


class PhysicsConstrainedInterpolator:
    """Физически ограниченная интерполяция для ГРП данных"""
    
    def __init__(self, constraints: Dict[str, float] = None):
        self.constraints = constraints or {
            'max_pressure_gradient': 100.0,  # МПа/час
            'min_flow_rate': 0.0,
            'max_flow_rate': 1000.0  # м³/сут
        }
        self.fitted = False
        
    def fit(self, time: pd.Series, values: pd.Series, 
            value_type: str = 'pressure') -> 'PhysicsConstrainedInterpolator':
        """Обучение с физическими ограничениями"""
        self.value_type = value_type
        self.fitted = True
        return self
    
    def predict(self, time: pd.Series) -> pd.Series:
        """Предсказание с физическими ограничениями"""
        if not self.fitted:
            raise ValueError("Модель не обучена")
        
        # Используем сплайн-интерполяцию как основу
        valid_mask = ~pd.isna(time)
        time_clean = time[valid_mask]
        
        if len(time_clean) < 2:
            return pd.Series(index=time.index, dtype=float)
        
        # Простая линейная интерполяция с ограничениями
        interpolated = time_clean.interpolate(method='linear')
        
        # Применяем физические ограничения
        if self.value_type == 'pressure':
            # Ограничиваем градиент давления
            dt = time_clean.diff()
            dp = interpolated.diff()
            gradient = dp / dt
            
            # Если градиент слишком большой, сглаживаем
            high_gradient = abs(gradient) > self.constraints['max_pressure_gradient']
            if high_gradient.any():
                interpolated = interpolated.rolling(window=3, center=True).mean()
        
        elif self.value_type == 'flow_rate':
            # Ограничиваем дебит
            interpolated = np.clip(interpolated, 
                                 self.constraints['min_flow_rate'],
                                 self.constraints['max_flow_rate'])
        
        return pd.Series(interpolated, index=time.index, name='physics_constrained')


class AdaptiveInterpolator:
    """Адаптивная интерполяция с автоматическим выбором метода"""
    
    def __init__(self):
        self.fitted = False
        self.best_method = None
        self.best_model = None
        
    def fit(self, time: pd.Series, values: pd.Series) -> 'AdaptiveInterpolator':
        """Автоматический выбор лучшего метода интерполяции"""
        valid_mask = ~(pd.isna(time) | pd.isna(values))
        time_clean = time[valid_mask]
        values_clean = values[valid_mask]
        
        if len(time_clean) < 3:
            self.best_method = 'linear'
            self.fitted = True
            return self
        
        # Тестируем различные методы
        methods = ['linear', 'cubic', 'rbf', 'gp']
        scores = {}
        
        # Разделяем данные на обучающую и тестовую выборки
        n_train = int(0.8 * len(time_clean))
        train_time = time_clean[:n_train]
        train_values = values_clean[:n_train]
        test_time = time_clean[n_train:]
        test_values = values_clean[n_train:]
        
        for method in methods:
            try:
                if method == 'linear':
                    model = interp1d(train_time, train_values, kind='linear', 
                                  bounds_error=False, fill_value='extrapolate')
                    pred = model(test_time)
                    
                elif method == 'cubic':
                    model = interp1d(train_time, train_values, kind='cubic',
                                  bounds_error=False, fill_value='extrapolate')
                    pred = model(test_time)
                    
                elif method == 'rbf':
                    rbf = RBFInterpolator()
                    rbf.fit(train_time, train_values)
                    pred = rbf.predict(test_time)
                    
                elif method == 'gp':
                    gp = GaussianProcessInterpolator()
                    gp.fit(train_time, train_values)
                    pred = gp.predict(test_time)
                
                # Вычисляем ошибку
                mse = mean_squared_error(test_values, pred)
                scores[method] = mse
                
            except Exception:
                scores[method] = float('inf')
        
        # Выбираем лучший метод
        self.best_method = min(scores, key=scores.get)
        
        # Обучаем финальную модель на всех данных
        if self.best_method == 'linear':
            self.best_model = interp1d(time_clean, values_clean, kind='linear',
                                    bounds_error=False, fill_value='extrapolate')
        elif self.best_method == 'cubic':
            self.best_model = interp1d(time_clean, values_clean, kind='cubic',
                                    bounds_error=False, fill_value='extrapolate')
        elif self.best_method == 'rbf':
            self.best_model = RBFInterpolator()
            self.best_model.fit(time_clean, values_clean)
        elif self.best_method == 'gp':
            self.best_model = GaussianProcessInterpolator()
            self.best_model.fit(time_clean, values_clean)
        
        self.fitted = True
        return self
    
    def predict(self, time: pd.Series) -> pd.Series:
        """Предсказание с помощью лучшего метода"""
        if not self.fitted:
            raise ValueError("Модель не обучена")
        
        if self.best_method in ['linear', 'cubic']:
            pred = self.best_model(time.values)
        else:
            pred = self.best_model.predict(time)
        
        return pd.Series(pred, index=time.index, name=f'adaptive_{self.best_method}')


# Функции для удобного использования новых интерполяторов
def apply_kriging_interpolation(time: pd.Series, values: pd.Series) -> pd.Series:
    """Применение кригинг-интерполяции"""
    kriging = KrigingInterpolator()
    try:
        kriging.fit(time, values)
        return kriging.predict(time)
    except Exception as e:
        print(f"Ошибка кригинг-интерполяции: {e}")
        return values


def apply_rbf_interpolation(time: pd.Series, values: pd.Series, 
                          function: str = 'multiquadric') -> pd.Series:
    """Применение RBF-интерполяции"""
    rbf = RBFInterpolator(function=function)
    try:
        rbf.fit(time, values)
        return rbf.predict(time)
    except Exception as e:
        print(f"Ошибка RBF-интерполяции: {e}")
        return values


def apply_gp_interpolation(time: pd.Series, values: pd.Series, 
                          return_std: bool = False) -> Union[pd.Series, Tuple[pd.Series, pd.Series]]:
    """Применение GP-интерполяции"""
    gp = GaussianProcessInterpolator()
    try:
        gp.fit(time, values)
        return gp.predict(time, return_std=return_std)
    except Exception as e:
        print(f"Ошибка GP-интерполяции: {e}")
        return values if not return_std else (values, pd.Series(0, index=time.index))


def apply_physics_constrained_interpolation(time: pd.Series, values: pd.Series, 
                                          value_type: str = 'pressure') -> pd.Series:
    """Применение физически ограниченной интерполяции"""
    physics = PhysicsConstrainedInterpolator()
    try:
        physics.fit(time, values, value_type=value_type)
        return physics.predict(time)
    except Exception as e:
        print(f"Ошибка физически ограниченной интерполяции: {e}")
        return values


def apply_adaptive_interpolation(time: pd.Series, values: pd.Series) -> pd.Series:
    """Применение адаптивной интерполяции"""
    adaptive = AdaptiveInterpolator()
    try:
        adaptive.fit(time, values)
        return adaptive.predict(time)
    except Exception as e:
        print(f"Ошибка адаптивной интерполяции: {e}")
        return values
