"""
Модуль физических ограничений для безразмерных кривых.
Обеспечивает физическую корректность кривых pD(Y).
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
import warnings

warnings.filterwarnings('ignore')


class PhysicsConstraints:
    """
    Класс для применения физических ограничений к безразмерным кривым.
    Обеспечивает монотонность, ограничение кривизны, удаление осцилляций и т.д.
    """
    
    @staticmethod
    def monotonic(
        curve: np.ndarray,
        x: Optional[np.ndarray] = None,
        direction: str = 'non_increasing'
    ) -> np.ndarray:
        """
        Восстанавливает монотонность кривой.
        Для pD кривых типично не возрастающее поведение.
        
        Args:
            curve: Входная кривая
            x: Координаты (если None, используется порядок элементов)
            direction: Направление монотонности ('non_increasing', 'non_decreasing')
        
        Returns:
            Монотонная кривая
        """
        curve = np.asarray(curve)
        valid_mask = np.isfinite(curve)
        
        if not np.any(valid_mask):
            return curve
        
        curve_clean = curve[valid_mask]
        
        if x is not None:
            x_clean = np.asarray(x)[valid_mask]
            # Сортируем по x
            sort_idx = np.argsort(x_clean)
            x_sorted = x_clean[sort_idx]
            curve_sorted = curve_clean[sort_idx]
        else:
            x_sorted = np.arange(len(curve_clean))
            curve_sorted = curve_clean.copy()
        
        if direction == 'non_increasing':
            # Применяем монотонное не возрастание (идём справа налево)
            curve_monotonic = np.maximum.accumulate(curve_sorted[::-1])[::-1]
        elif direction == 'non_decreasing':
            # Применяем монотонное не убывание
            curve_monotonic = np.maximum.accumulate(curve_sorted)
        else:
            raise ValueError(f"Неизвестное направление: {direction}")
        
        # Восстанавливаем исходный порядок
        if x is not None:
            result = curve.copy()
            result[valid_mask] = curve_monotonic[np.argsort(sort_idx)]
        else:
            result = curve.copy()
            result[valid_mask] = curve_monotonic
        
        return result
    
    @staticmethod
    def limit_curvature(
        curve: np.ndarray,
        x: Optional[np.ndarray] = None,
        max_curvature: float = 10.0
    ) -> np.ndarray:
        """
        Ограничивает вторую производную (кривизну) кривой.
        
        Args:
            curve: Входная кривая
            x: Координаты
            max_curvature: Максимальное значение второй производной
        
        Returns:
            Кривая с ограниченной кривизной
        """
        curve = np.asarray(curve)
        valid_mask = np.isfinite(curve)
        
        if not np.any(valid_mask) or np.sum(valid_mask) < 3:
            return curve
        
        curve_clean = curve[valid_mask]
        
        if x is not None:
            x_clean = np.asarray(x)[valid_mask]
            if len(x_clean) < 3:
                return curve
            second_deriv = np.gradient(np.gradient(curve_clean, x_clean), x_clean)
        else:
            second_deriv = np.gradient(np.gradient(curve_clean))
        
        # Ограничиваем вторую производную
        second_deriv_clipped = np.clip(second_deriv, -max_curvature, max_curvature)
        
        # Восстанавливаем кривую интегрированием
        # Интегрируем дважды (с учётом граничных условий)
        first_deriv = np.cumsum(second_deriv_clipped) * (x_clean[1] - x_clean[0] if x is not None else 1.0)
        first_deriv = first_deriv - first_deriv[0]  # Нормализация
        
        curve_restored = np.cumsum(first_deriv) * (x_clean[1] - x_clean[0] if x is not None else 1.0)
        curve_restored = curve_restored - curve_restored[0] + curve_clean[0]  # Сохраняем начальное значение
        
        result = curve.copy()
        result[valid_mask] = curve_restored
        
        return result
    
    @staticmethod
    def remove_oscillations(
        curve: np.ndarray,
        x: Optional[np.ndarray] = None,
        window_size: int = 5,
        threshold: float = 0.1
    ) -> np.ndarray:
        """
        Удаляет осцилляции из кривой на основе изменений знака второй производной.
        """
        curve = np.asarray(curve)
        valid_mask = np.isfinite(curve)
        
        if not np.any(valid_mask) or np.sum(valid_mask) < 3:
            return curve.copy()
        
        curve_clean = curve[valid_mask]
        n = len(curve_clean)
        
        if n < 3:
            result = curve.copy()
            return result
        
        # Вычисляем вторую производную
        if x is not None:
            x_clean = np.asarray(x)[valid_mask]
            if len(x_clean) != n:
                return curve.copy()
            dydx = np.gradient(curve_clean, x_clean)
            d2ydx2 = np.gradient(dydx, x_clean)
        else:
            d2ydx2 = np.gradient(np.gradient(curve_clean))
        
        # Определяем изменения знака второй производной
        sign_d2 = np.sign(d2ydx2)
        # Заменяем 0 на предыдущий ненулевой знак (чтобы не ловить шум)
        sign_d2 = np.where(sign_d2 == 0, np.nan, sign_d2)
        sign_d2 = pd.Series(sign_d2).fillna(method='ffill').fillna(0).values
        
        # Где знак меняется? (с учётом сдвига)
        sign_change = np.diff(sign_d2) != 0  # длина: n - 1
        
        # Расширяем обратно до длины n: добавляем False в начало или конец
        oscillation_mask = np.zeros(n, dtype=bool)
        oscillation_mask[1:] = sign_change  # изменения происходят между точками → относятся к следующей
        # Или можно: oscillation_mask[:-1] |= sign_change
        
        # Дополнительно: если рядом с изменением — большой градиент, считаем это осцилляцией
        gradient_mag = np.abs(np.gradient(curve_clean))
        # Можно усилить условие, но пока просто используем sign_change
        
        # Сглаживаем только в зонах осцилляций
        if np.any(oscillation_mask):
            from scipy.ndimage import uniform_filter1d
            smoothed = uniform_filter1d(curve_clean, size=window_size, mode='nearest')
            curve_clean[oscillation_mask] = smoothed[oscillation_mask]
        
        # Восстанавливаем результат
        result = curve.copy()
        result[valid_mask] = curve_clean
        
        return result
    
    @staticmethod
    def asymptotic_fix(
        curve: np.ndarray,
        x: Optional[np.ndarray] = None,
        early_window: int = 5,
        late_window: int = 5
    ) -> np.ndarray:
        """
        Исправляет асимптотическое поведение в раннем и позднем режимах.
        Обеспечивает стабильность на краях кривой.
        
        Args:
            curve: Входная кривая
            x: Координаты
            early_window: Размер окна для раннего режима
            late_window: Размер окна для позднего режима
        
        Returns:
            Кривая с исправленными асимптотиками
        """
        curve = np.asarray(curve)
        valid_mask = np.isfinite(curve)
        
        if not np.any(valid_mask):
            return curve
        
        curve_clean = curve[valid_mask]
        n = len(curve_clean)
        
        if n < max(early_window, late_window) + 1:
            return curve
        
        result_clean = curve_clean.copy()
        
        # Ранний режим: сглаживание первых точек
        if early_window > 0 and n >= early_window:
            early_mean = np.mean(curve_clean[:early_window])
            # Плавный переход к среднему значению
            for i in range(min(early_window, n)):
                alpha = i / early_window
                result_clean[i] = alpha * curve_clean[i] + (1 - alpha) * early_mean
        
        # Поздний режим: сглаживание последних точек
        if late_window > 0 and n >= late_window:
            late_mean = np.mean(curve_clean[-late_window:])
            # Плавный переход к среднему значению
            for i in range(max(0, n - late_window), n):
                alpha = (i - (n - late_window)) / late_window
                result_clean[i] = alpha * curve_clean[i] + (1 - alpha) * late_mean
        
        result = curve.copy()
        result[valid_mask] = result_clean
        
        return result
    
    @staticmethod
    def enforce_all(
        curve: np.ndarray,
        x: Optional[np.ndarray] = None,
        monotonic: bool = True,
        limit_curvature: bool = True,
        remove_oscillations: bool = True,
        asymptotic_fix: bool = True,
        **kwargs
    ) -> np.ndarray:
        """
        Применяет все физические ограничения последовательно.
        
        Args:
            curve: Входная кривая
            x: Координаты
            monotonic: Применять монотонность
            limit_curvature: Ограничивать кривизну
            remove_oscillations: Удалять осцилляции
            asymptotic_fix: Исправлять асимптотики
            **kwargs: Дополнительные параметры для каждого метода
        
        Returns:
            Кривая с применёнными ограничениями
        """
        result = curve.copy()
        
        if monotonic:
            direction = kwargs.get('monotonic_direction', 'non_increasing')
            result = PhysicsConstraints.monotonic(result, x, direction=direction)
        
        if remove_oscillations:
            window_size = kwargs.get('oscillation_window', 5)
            threshold = kwargs.get('oscillation_threshold', 0.1)
            result = PhysicsConstraints.remove_oscillations(
                result, x, window_size=window_size, threshold=threshold
            )
        
        if limit_curvature:
            max_curvature = kwargs.get('max_curvature', 10.0)
            result = PhysicsConstraints.limit_curvature(result, x, max_curvature=max_curvature)
        
        if asymptotic_fix:
            early_window = kwargs.get('early_window', 5)
            late_window = kwargs.get('late_window', 5)
            result = PhysicsConstraints.asymptotic_fix(
                result, x, early_window=early_window, late_window=late_window
            )
        
        # Финальная проверка монотонности
        if monotonic:
            direction = kwargs.get('monotonic_direction', 'non_increasing')
            result = PhysicsConstraints.monotonic(result, x, direction=direction)
        
        return result

