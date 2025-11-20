"""
Главный модуль унифицированного интерполятора для безразмерных кривых.
Объединяет фильтрацию, физические ограничения и интерполяцию.
"""

import numpy as np
from typing import Optional, Dict, Any, Tuple, Union
import warnings

warnings.filterwarnings('ignore')

from .filters import SignalFilters
from .physics import PhysicsConstraints
from .utils import (
    select_filter_method, detect_log_scale, fill_missing_values,
    compute_snr, compute_oscillation_score
)

# Опциональный импорт ML-денойзера
try:
    from .denoise import MLDenoiser, apply_ml_denoising
    ML_DENOISE_AVAILABLE = True
except ImportError:
    ML_DENOISE_AVAILABLE = False


class UnifiedInterpolator:
    """
    Унифицированный интерполятор для безразмерных кривых.
    Объединяет фильтрацию, физические ограничения и интерполяцию в единую модель.
    """
    
    def __init__(
        self,
        filter_method: Optional[str] = None,
        use_ml_denoise: bool = False,
        enforce_physics: bool = True,
        interpolation_method: str = 'gp',
        **kwargs
    ):
        """
        Инициализация унифицированного интерполятора.
        
        Args:
            filter_method: Метод фильтрации (None = автоматический выбор)
            use_ml_denoise: Использовать ли ML-денойзинг
            enforce_physics: Применять ли физические ограничения
            interpolation_method: Метод интерполяции ('gp', 'rbf', 'spline')
            **kwargs: Дополнительные параметры
        """
        self.filter_method = filter_method
        self.use_ml_denoise = use_ml_denoise and ML_DENOISE_AVAILABLE
        self.enforce_physics = enforce_physics
        self.interpolation_method = interpolation_method
        
        # Параметры фильтрации
        self.filter_params = kwargs.get('filter_params', {})
        
        # Параметры физических ограничений
        self.physics_params = kwargs.get('physics_params', {
            'monotonic': True,
            'limit_curvature': True,
            'remove_oscillations': True,
            'asymptotic_fix': True,
            'monotonic_direction': 'non_increasing',
            'max_curvature': 10.0
        })
        
        # Модель интерполяции
        self.model = None
        self.Y_train = None
        self.curve_train = None
        self.is_fitted = False
    
    def fit(
        self,
        Y: np.ndarray,
        curve: np.ndarray,
        params: Optional[Dict[str, Any]] = None
    ) -> 'UnifiedInterpolator':
        """
        Обучение интерполятора на данных.
        
        Args:
            Y: Безразмерная ось (1D)
            curve: Значения pD(Y)
            params: Произвольные физические параметры (skin, N, a/L...)
        
        Returns:
            self
        """
        Y = np.asarray(Y)
        curve = np.asarray(curve)
        
        # Очищаем данные
        valid_mask = np.isfinite(Y) & np.isfinite(curve)
        if not np.any(valid_mask):
            raise ValueError("Нет валидных данных для обучения")
        
        Y_clean = Y[valid_mask]
        curve_clean = curve[valid_mask]
        
        # Сортируем по Y
        sort_idx = np.argsort(Y_clean)
        Y_sorted = Y_clean[sort_idx]
        curve_sorted = curve_clean[sort_idx]
        
        # 1. Заполнение пропусков
        curve_filled = fill_missing_values(curve_sorted, Y_sorted, method='linear')
        
        # 2. ML-денойзинг (опционально)
        if self.use_ml_denoise:
            try:
                curve_filled, success = apply_ml_denoising(
                    Y_sorted, curve_filled, use_ml=True
                )
                if not success:
                    self.use_ml_denoise = False
            except Exception:
                self.use_ml_denoise = False
        
        # 3. Фильтрация
        filter_method = self.filter_method
        if filter_method is None:
            filter_method = select_filter_method(curve_filled, Y_sorted)
        
        curve_filtered = SignalFilters.denoise(
            curve_filled,
            method=filter_method,
            x=Y_sorted,
            **self.filter_params
        )
        
        # 4. Физические ограничения
        if self.enforce_physics:
            curve_filtered = PhysicsConstraints.enforce_all(
                curve_filtered,
                x=Y_sorted,
                **self.physics_params
            )
        
        # 5. Построение модели интерполяции
        self._build_interpolation_model(Y_sorted, curve_filtered)
        
        # Сохраняем обучающие данные
        self.Y_train = Y_sorted
        self.curve_train = curve_filtered
        self.is_fitted = True
        
        return self
    
    def _build_interpolation_model(self, Y: np.ndarray, curve: np.ndarray):
        """Строит модель интерполяции."""
        if self.interpolation_method == 'gp':
            from sklearn.gaussian_process import GaussianProcessRegressor
            from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
            
            # Physics-informed GP kernel
            kernel = ConstantKernel() * RBF() + WhiteKernel(noise_level=1e-5)
            self.model = GaussianProcessRegressor(
                kernel=kernel,
                alpha=1e-6,
                random_state=42
            )
            self.model.fit(Y.reshape(-1, 1), curve)
        
        elif self.interpolation_method == 'rbf':
            from scipy.interpolate import RBFInterpolator
            self.model = RBFInterpolator(
                Y.reshape(-1, 1),
                curve,
                kernel='thin_plate_spline',
                smoothing=0.0
            )
        
        elif self.interpolation_method == 'spline':
            from scipy.interpolate import UnivariateSpline
            self.model = UnivariateSpline(Y, curve, s=0.0)
        
        else:
            raise ValueError(f"Неизвестный метод интерполяции: {self.interpolation_method}")
    
    def predict(self, Y_new: np.ndarray) -> np.ndarray:
        """
        Предсказание значений для новых точек Y.
        
        Args:
            Y_new: Новые значения безразмерной оси
        
        Returns:
            Предсказанные значения pD
        """
        if not self.is_fitted:
            raise RuntimeError("Интерполятор не обучен. Вызовите fit() сначала.")
        
        Y_new = np.asarray(Y_new)
        valid_mask = np.isfinite(Y_new)
        
        if not np.any(valid_mask):
            return np.full_like(Y_new, np.nan)
        
        Y_new_clean = Y_new[valid_mask]
        
        # Предсказание
        if self.interpolation_method == 'gp':
            pred, _ = self.model.predict(Y_new_clean.reshape(-1, 1), return_std=True)
        elif self.interpolation_method == 'rbf':
            pred = self.model(Y_new_clean.reshape(-1, 1))
        elif self.interpolation_method == 'spline':
            pred = self.model(Y_new_clean)
        else:
            raise ValueError(f"Неизвестный метод интерполяции: {self.interpolation_method}")
        
        # Восстанавливаем полный массив
        result = np.full_like(Y_new, np.nan)
        result[valid_mask] = pred
        
        # Применяем физические ограничения к предсказаниям
        if self.enforce_physics:
            result = PhysicsConstraints.enforce_all(
                result,
                x=Y_new,
                **self.physics_params
            )
        
        return result
    
    def denoise(self) -> np.ndarray:
        """
        Возвращает отфильтрованную версию обучающих данных.
        
        Returns:
            Отфильтрованная кривая
        """
        if not self.is_fitted:
            raise RuntimeError("Интерполятор не обучен.")
        
        return self.curve_train
    
    def enforce_physics(self) -> np.ndarray:
        """
        Возвращает версию обучающих данных с применёнными физическими ограничениями.
        
        Returns:
            Кривая с физическими ограничениями
        """
        if not self.is_fitted:
            raise RuntimeError("Интерполятор не обучен.")
        
        return PhysicsConstraints.enforce_all(
            self.curve_train,
            x=self.Y_train,
            **self.physics_params
        )
    
    def batch_fit(
        self,
        Y: np.ndarray,
        curves_matrix: np.ndarray
    ) -> 'UnifiedInterpolator':
        """
        Обучение на банке шаблонов (несколько кривых).
        
        Args:
            Y: Безразмерная ось (1D)
            curves_matrix: Матрица кривых (n_curves, n_points)
        
        Returns:
            self
        """
        curves_matrix = np.asarray(curves_matrix)
        
        if curves_matrix.ndim == 1:
            # Одна кривая
            return self.fit(Y, curves_matrix)
        
        # Обрабатываем каждую кривую отдельно
        # Для batch режима можно использовать среднюю кривую или обучать на всех
        # Здесь используем среднюю кривую после фильтрации каждой
        
        n_curves, n_points = curves_matrix.shape
        
        filtered_curves = []
        for i in range(n_curves):
            curve = curves_matrix[i, :]
            # Применяем фильтрацию и ограничения к каждой кривой
            curve_filtered = SignalFilters.denoise(
                curve,
                method=self.filter_method or 'hybrid',
                x=Y
            )
            
            if self.enforce_physics:
                curve_filtered = PhysicsConstraints.enforce_all(
                    curve_filtered,
                    x=Y,
                    **self.physics_params
                )
            
            filtered_curves.append(curve_filtered)
        
        # Используем среднюю кривую для обучения
        curve_mean = np.nanmean(filtered_curves, axis=0)
        
        return self.fit(Y, curve_mean)

