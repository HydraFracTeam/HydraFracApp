"""
Модуль фильтрации сигналов для безразмерных кривых.
Реализует различные методы фильтрации согласно статье и контракту.
"""

import numpy as np
from typing import Optional, Tuple
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d
import warnings

warnings.filterwarnings('ignore')


class SignalFilters:
    """
    Класс для применения различных методов фильтрации сигналов.
    Реализует методы из статьи: Savitzky-Golay, Gaussian, Kalman, Log-domain, Hybrid.
    """
    
    @staticmethod
    def savgol(
        curve: np.ndarray,
        window_length: Optional[int] = None,
        polyorder: int = 2,
        mode: str = 'nearest'
    ) -> np.ndarray:
        """
        Фильтр Савицкого-Голея для сглаживания сигнала.
        
        Args:
            curve: Входной сигнал
            window_length: Длина окна (должна быть нечётной, >= polyorder+1)
            polyorder: Порядок полинома
            mode: Режим обработки краёв
        
        Returns:
            Отфильтрованный сигнал
        """
        curve = np.asarray(curve)
        valid_mask = np.isfinite(curve)
        
        if not np.any(valid_mask) or np.sum(valid_mask) < 3:
            return curve
        
        # Если все значения валидны, работаем напрямую
        if np.all(valid_mask):
            n = len(curve)
            if window_length is None:
                window_length = min(max(5, n // 4), n if n % 2 == 1 else n - 1)
                window_length = max(window_length, polyorder + 1)
                if window_length % 2 == 0:
                    window_length += 1
            window_length = min(window_length, n if n % 2 == 1 else n - 1)
            window_length = max(window_length, polyorder + 1)
            if window_length > n:
                return curve
            try:
                return savgol_filter(curve, window_length, polyorder, mode=mode)
            except (ValueError, np.linalg.LinAlgError):
                return curve
        
        curve_clean = curve[valid_mask]
        n = len(curve_clean)
        
        # Автоматический выбор window_length
        if window_length is None:
            window_length = min(max(5, n // 4), n if n % 2 == 1 else n - 1)
            window_length = max(window_length, polyorder + 1)
            if window_length % 2 == 0:
                window_length += 1
        
        # Ограничиваем window_length
        window_length = min(window_length, n if n % 2 == 1 else n - 1)
        window_length = max(window_length, polyorder + 1)
        
        if window_length > n:
            return curve
        
        try:
            filtered = savgol_filter(curve_clean, window_length, polyorder, mode=mode)
            result = curve.copy()
            result[valid_mask] = filtered
            return result
        except (ValueError, np.linalg.LinAlgError):
            # Fallback: возвращаем исходный сигнал
            return curve
    
    @staticmethod
    def gaussian(
        curve: np.ndarray,
        sigma: float = 1.0,
        mode: str = 'nearest'
    ) -> np.ndarray:
        """
        Гауссовское сглаживание сигнала.
        
        Args:
            curve: Входной сигнал
            sigma: Стандартное отклонение гауссова ядра
            mode: Режим обработки краёв
        
        Returns:
            Отфильтрованный сигнал
        """
        curve = np.asarray(curve)
        valid_mask = np.isfinite(curve)
        
        if not np.any(valid_mask):
            return curve
        
        # Если все значения валидны, работаем напрямую
        if np.all(valid_mask):
            if len(curve) < 3:
                return curve
            try:
                return gaussian_filter1d(curve, sigma=sigma, mode=mode)
            except Exception:
                return curve
        
        curve_clean = curve[valid_mask]
        
        if len(curve_clean) < 3:
            return curve
        
        try:
            filtered = gaussian_filter1d(curve_clean, sigma=sigma, mode=mode)
            result = curve.copy()
            result[valid_mask] = filtered
            return result
        except Exception:
            return curve
    
    @staticmethod
    def kalman(
        curve: np.ndarray,
        process_noise: float = 0.1,
        measurement_noise: float = 0.1
    ) -> np.ndarray:
        """
        Одномерный фильтр Калмана для нестационарного шума.
        
        Args:
            curve: Входной сигнал
            process_noise: Дисперсия процессного шума (Q)
            measurement_noise: Дисперсия шума измерений (R)
        
        Returns:
            Отфильтрованный сигнал
        """
        curve = np.asarray(curve)
        valid_mask = np.isfinite(curve)
        
        if not np.any(valid_mask):
            return curve
        
        curve_clean = curve[valid_mask]
        n = len(curve_clean)
        
        if n < 2:
            return curve
        
        # Инициализация фильтра Калмана
        x = curve_clean[0]  # Состояние
        P = 1.0  # Ковариация
        
        filtered_values = [x]
        
        for i in range(1, n):
            # Предсказание
            x_pred = x
            P_pred = P + process_noise
            
            # Обновление
            K = P_pred / (P_pred + measurement_noise)  # Коэффициент Калмана
            z = curve_clean[i]  # Измерение
            x = x_pred + K * (z - x_pred)
            P = (1 - K) * P_pred
            
            filtered_values.append(x)
        
        result = curve.copy()
        result[valid_mask] = np.array(filtered_values)
        return result
    
    @staticmethod
    def log_domain(
        curve: np.ndarray,
        base_filter: str = 'savgol',
        **filter_kwargs
    ) -> np.ndarray:
        """
        Фильтрация в логарифмическом масштабе.
        Применяется, когда данные изменяются более чем на порядок.
        
        Args:
            curve: Входной сигнал (должен быть положительным)
            base_filter: Базовый метод фильтрации ('savgol', 'gaussian', 'kalman')
            **filter_kwargs: Параметры базового фильтра
        
        Returns:
            Отфильтрованный сигнал
        """
        curve = np.asarray(curve)
        valid_mask = np.isfinite(curve) & (curve > 0)
        
        if not np.any(valid_mask):
            return curve
        
        curve_clean = curve[valid_mask]
        
        # Переходим в логарифмический масштаб
        log_curve = np.log10(curve_clean)
        
        # Применяем базовый фильтр
        if base_filter == 'savgol':
            filtered_log = SignalFilters.savgol(log_curve, **filter_kwargs)
        elif base_filter == 'gaussian':
            filtered_log = SignalFilters.gaussian(log_curve, **filter_kwargs)
        elif base_filter == 'kalman':
            filtered_log = SignalFilters.kalman(log_curve, **filter_kwargs)
        else:
            filtered_log = log_curve
        
        # Возвращаемся из логарифмического масштаба
        filtered = 10 ** filtered_log
        
        result = curve.copy()
        result[valid_mask] = filtered
        return result
    
    @staticmethod
    def hybrid(
        curve: np.ndarray,
        x: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Гибридный фильтр: SavGol → Gaussian → Log-inverse (если нужно).
        Используется по умолчанию для универсальной фильтрации.
        
        Args:
            curve: Входной сигнал
            x: Координаты (опционально)
        
        Returns:
            Отфильтрованный сигнал
        """
        curve = np.asarray(curve)
        valid_mask = np.isfinite(curve)
        
        if not np.any(valid_mask):
            return curve
        
        curve_clean = curve[valid_mask]
        
        # Проверяем, нужен ли логарифмический масштаб
        from .utils import detect_log_scale
        use_log = detect_log_scale(curve_clean)
        
        if use_log:
            # Используем log-domain фильтрацию
            return SignalFilters.log_domain(curve, base_filter='savgol')
        
        # Применяем последовательность фильтров
        filtered = curve_clean.copy()
        
        # 1. Savitzky-Golay для начального сглаживания
        try:
            # Работаем напрямую с очищенным массивом
            n = len(filtered)
            if n >= 3:
                window_length = min(max(5, n // 4), n if n % 2 == 1 else n - 1)
                window_length = max(window_length, 3)  # polyorder + 1
                if window_length % 2 == 0:
                    window_length += 1
                window_length = min(window_length, n if n % 2 == 1 else n - 1)
                if window_length <= n:
                    filtered = savgol_filter(filtered, window_length, polyorder=2, mode='nearest')
        except Exception:
            pass
        
        # 2. Gaussian для дополнительного сглаживания
        try:
            if len(filtered) >= 3:
                filtered = gaussian_filter1d(filtered, sigma=0.5, mode='nearest')
        except Exception:
            pass
        
        # Восстанавливаем исходный размер только если были NaN
        if np.all(valid_mask):
            return filtered
        else:
            result = curve.copy()
            result[valid_mask] = filtered
            return result
    
    @staticmethod
    def denoise(
        curve: np.ndarray,
        method: Optional[str] = None,
        x: Optional[np.ndarray] = None,
        **kwargs
    ) -> np.ndarray:
        """
        Универсальный метод денойзинга с автоматическим выбором фильтра.
        
        Args:
            curve: Входной сигнал
            method: Метод фильтрации (если None, выбирается автоматически)
            x: Координаты
            **kwargs: Дополнительные параметры фильтра
        
        Returns:
            Отфильтрованный сигнал
        """
        if method is None:
            from .utils import select_filter_method
            method = select_filter_method(curve, x)
        
        if method == 'savgol':
            return SignalFilters.savgol(curve, **kwargs)
        elif method == 'gaussian':
            return SignalFilters.gaussian(curve, **kwargs)
        elif method == 'kalman':
            return SignalFilters.kalman(curve, **kwargs)
        elif method == 'log_domain':
            return SignalFilters.log_domain(curve, **kwargs)
        elif method == 'hybrid':
            return SignalFilters.hybrid(curve, x)
        else:
            raise ValueError(f"Неизвестный метод фильтрации: {method}")

