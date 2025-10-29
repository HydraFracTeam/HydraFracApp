"""
Модуль для работы с безразмерными параметрами МГРП
Реализует конвертацию в безразмерные координаты и интерполяцию в пространстве безразмерных кривых
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Optional, List, Union
from dataclasses import dataclass
from scipy.interpolate import griddata, RBFInterpolator, UnivariateSpline
from scipy.signal import savgol_filter
from scipy.optimize import minimize
import warnings

warnings.filterwarnings('ignore')


@dataclass
class DimensionlessParameters:
    """Безразмерные параметры для МГРП"""
    # Фильтрационный параметр
    X: np.ndarray  # (0.00864 * k * h * Δp_i) / (μ * B * Q)
    # Ёмкостной параметр  
    Y: np.ndarray  # (Q * B * t) / (24 * φ * c_t * h * L² * Δp_i)
    
    # Исходные физические данные
    pressure: np.ndarray  # Исходное давление, атм
    flow_rate: np.ndarray  # Исходный дебит, м³/сут
    
    # Исходные физические параметры
    k: float  # Проницаемость, мД
    h: float  # Толщина пласта, м
    mu: float  # Вязкость, мПа·с
    B: float  # Объемный коэффициент
    phi: float  # Пористость
    c_t: float  # Общая сжимаемость, 1/атм
    L: float  # Длина трещины, м
    delta_p_i: float  # Начальное падение давления, атм
    Q: float  # Дебит, м³/сут
    t: np.ndarray  # Время, ч


class DimensionlessConverter:
    """Конвертер в безразмерные параметры для МГРП"""
    
    def __init__(self):
        self.default_params = {
            'k': 1.0,  # мД
            'mu': 1.0,  # мПа·с
            'B': 1.0,  # безразмерный
            'phi': 0.1,  # безразмерный
            'c_t': 1e-4,  # 1/атм
        }
    
    def convert_to_dimensionless(self, 
                                time: pd.Series,
                                pressure: pd.Series,
                                flow_rate: pd.Series,
                                well_params: Dict[str, float]) -> DimensionlessParameters:
        """
        Конвертация в безразмерные параметры
        
        Args:
            time: Временной ряд, ч
            pressure: Давление, атм
            flow_rate: Дебит, м³/сут
            well_params: Параметры скважины (k, h, mu, B, phi, c_t, L, skin, N, a_L)
        """
        # Извлекаем параметры
        k = well_params.get('k', self.default_params['k'])
        h = well_params.get('h', 10.0)
        mu = well_params.get('mu', self.default_params['mu'])
        B = well_params.get('B', self.default_params['B'])
        phi = well_params.get('phi', self.default_params['phi'])
        c_t = well_params.get('c_t', self.default_params['c_t'])
        L = well_params.get('L', 100.0)
        
        # Начальное падение давления
        delta_p_i = pressure.iloc[0] - pressure.iloc[-1] if len(pressure) > 1 else pressure.iloc[0]
        
        # Средний дебит
        Q = flow_rate.mean() if not flow_rate.empty else 1.0
        
        # Конвертируем в numpy массивы
        t = time.values
        p = pressure.values
        q = flow_rate.values
        
        # Фильтрационный параметр X = (0.00864 * k * h * Δp_i) / (μ * B * Q)
        X = (0.00864 * k * h * delta_p_i) / (mu * B * Q)
        
        # Ёмкостной параметр Y = (Q * B * t) / (24 * φ * c_t * h * L² * Δp_i)
        Y = (Q * B * t) / (24 * phi * c_t * h * L**2 * delta_p_i)
        
        return DimensionlessParameters(
            X=np.full_like(t, X),  # X постоянен для всех временных точек
            Y=Y,
            pressure=p,  # Сохраняем исходные данные
            flow_rate=q,
            k=k, h=h, mu=mu, B=B, phi=phi, c_t=c_t, L=L, 
            delta_p_i=delta_p_i, Q=Q, t=t
        )
    
    def convert_from_dimensionless(self, 
                                 dimensionless: DimensionlessParameters,
                                 target_times: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Обратная конвертация из безразмерных параметров в физические
        
        Args:
            dimensionless: Безразмерные параметры
            target_times: Целевые временные точки
            
        Returns:
            Tuple[pressure, flow_rate]: Восстановленные физические величины
        """
        # Восстанавливаем давление
        # p = p_i - (X * Y * mu * B * Q) / (0.00864 * k * h)
        pressure = (dimensionless.delta_p_i - 
                   (dimensionless.X[0] * dimensionless.Y * dimensionless.mu * dimensionless.B * dimensionless.Q) / 
                   (0.00864 * dimensionless.k * dimensionless.h))
        
        # Восстанавливаем дебит
        # Q = (Y * 24 * φ * c_t * h * L² * Δp_i) / (B * t)
        flow_rate = (dimensionless.Y * 24 * dimensionless.phi * dimensionless.c_t * 
                    dimensionless.h * dimensionless.L**2 * dimensionless.delta_p_i) / (dimensionless.B * target_times)
        
        return pressure, flow_rate


class DimensionlessInterpolator:
    """Интерполятор в пространстве безразмерных кривых"""
    
    def __init__(self, method: str = 'rbf'):
        self.method = method
        self.fitted = False
        self.interpolator = None
        self.dimensionless_data = None
        
    def fit(self, 
            time: pd.Series,
            pressure: pd.Series, 
            flow_rate: pd.Series,
            well_params: Dict[str, float]) -> 'DimensionlessInterpolator':
        """
        Обучение интерполятора на безразмерных данных
        
        Args:
            time: Временной ряд
            pressure: Давление
            flow_rate: Дебит
            well_params: Параметры скважины
        """
        converter = DimensionlessConverter()
        self.dimensionless_data = converter.convert_to_dimensionless(
            time, pressure, flow_rate, well_params
        )
        
        # Подготавливаем данные для интерполяции
        X_coords = self.dimensionless_data.X.reshape(-1, 1)
        Y_coords = self.dimensionless_data.Y.reshape(-1, 1)
        coords = np.hstack([X_coords, Y_coords])
        
        # Целевые значения (давление в безразмерном виде)
        target_values = pressure.values / self.dimensionless_data.delta_p_i
        
        if self.method == 'rbf':
            self.interpolator = RBFInterpolator(coords, target_values, 
                                              function='multiquadric', smoothing=0.0)
        elif self.method == 'linear':
            self.interpolator = 'linear'  # Будем использовать griddata
        else:
            raise ValueError(f"Неизвестный метод: {self.method}")
        
        self.fitted = True
        return self
    
    def predict(self, 
                target_times: np.ndarray,
                target_params: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Предсказание в безразмерном пространстве
        
        Args:
            target_times: Целевые временные точки
            target_params: Параметры для целевых точек
            
        Returns:
            Tuple[pressure, flow_rate]: Предсказанные значения
        """
        if not self.fitted:
            raise ValueError("Интерполятор не обучен")
        
        # Конвертируем целевые параметры в безразмерные
        converter = DimensionlessConverter()
        
        # Создаем временные ряды для конвертации
        target_time_series = pd.Series(target_times)
        target_pressure_series = pd.Series(np.ones_like(target_times))  # Заглушка
        target_flow_rate_series = pd.Series(np.ones_like(target_times))  # Заглушка
        
        target_dimensionless = converter.convert_to_dimensionless(
            target_time_series, target_pressure_series, target_flow_rate_series, target_params
        )
        
        # Подготавливаем координаты для интерполяции
        X_coords = target_dimensionless.X.reshape(-1, 1)
        Y_coords = target_dimensionless.Y.reshape(-1, 1)
        target_coords = np.hstack([X_coords, Y_coords])
        
        # Интерполируем
        if self.method == 'rbf':
            interpolated_values = self.interpolator(target_coords)
        else:  # linear
            # Подготавливаем исходные данные
            source_X = self.dimensionless_data.X.reshape(-1, 1)
            source_Y = self.dimensionless_data.Y.reshape(-1, 1)
            source_coords = np.hstack([source_X, source_Y])
            source_values = self.dimensionless_data.pressure / self.dimensionless_data.delta_p_i
            
            interpolated_values = griddata(source_coords, source_values, target_coords, method='linear')
        
        # Восстанавливаем физические величины
        pressure = interpolated_values * target_dimensionless.delta_p_i
        flow_rate = target_dimensionless.Q * np.ones_like(target_times)  # Упрощение
        
        return pressure, flow_rate


def get_dimensionless_series(dimensionless: DimensionlessParameters) -> Dict[str, np.ndarray]:
    """Возвращает безразмерные ряды pD(Y) и qD(Y) для 1D анализа по оси Y.

    pD = P / Δp_i, qD = Q / Q̄. Удобно для интерполяции/фильтрации вдоль Y.
    """
    pD = dimensionless.pressure / dimensionless.delta_p_i if dimensionless.delta_p_i != 0 else np.zeros_like(dimensionless.pressure)
    q_mean = dimensionless.Q if dimensionless.Q != 0 else 1.0
    qD = dimensionless.flow_rate / q_mean
    Y = dimensionless.Y
    return {"Y": Y, "logY": np.log10(np.clip(Y, 1e-30, None)), "pD": pD, "qD": qD}


class DimensionlessCurveInterpolator1D:
    """1D-интерполятор вдоль оси Y (или log10(Y)) для pD(Y) и qD(Y).

    Использует UnivariateSpline в логарифмическом масштабе по умолчанию и опционально
    сглаживание Савицкого–Голея для устойчивости к шуму.
    """

    def __init__(self, use_logY: bool = True, spline_smooth: Optional[float] = None,
                 apply_savgol: bool = True, window: int = 7, polyorder: int = 2):
        self.use_logY = use_logY
        self.spline_smooth = spline_smooth
        self.apply_savgol = apply_savgol
        self.window = window
        self.polyorder = polyorder
        self._spline: Optional[UnivariateSpline] = None
        self._x: Optional[np.ndarray] = None
        self._y: Optional[np.ndarray] = None

    def fit(self, Y: np.ndarray, values: np.ndarray) -> "DimensionlessCurveInterpolator1D":
        mask = ~(np.isnan(Y) | np.isnan(values) | np.isinf(Y) | np.isinf(values))
        Yc = Y[mask]
        Vc = values[mask]
        if len(Yc) < 4:
            # Недостаточно точек для сплайна — оставим как есть
            self._x = Yc
            self._spline = None
            return self

        # Сортировка по возрастанию Y
        idx = np.argsort(Yc)
        Yc = Yc[idx]
        Vc = Vc[idx]

        x = np.log10(np.clip(Yc, 1e-30, None)) if self.use_logY else Yc

        # Опциональная фильтрация значений перед обучением сплайна
        if self.apply_savgol and len(Vc) >= max(self.window, self.polyorder + 2):
            try:
                Vc = savgol_filter(Vc, self.window if self.window % 2 == 1 else self.window + 1, self.polyorder)
            except Exception:
                pass

        try:
            self._spline = UnivariateSpline(x, Vc, s=self.spline_smooth if self.spline_smooth is not None else 0.0)
            self._x = x
            self._y = Vc
        except Exception:
            self._spline = None
            self._x = x
            self._y = Vc
        return self

    def predict(self, target_Y: np.ndarray) -> np.ndarray:
        if self._x is None or len(self._x) == 0:
            return np.full_like(target_Y, np.nan, dtype=float)
        xt = np.log10(np.clip(target_Y, 1e-30, None)) if self.use_logY else target_Y
        if self._spline is None:
            # Линейная интерполяция как фоллбэк
            return np.interp(xt, self._x, self._y)
        return self._spline(xt)


def resample_dimensionless_series(dimensionless: DimensionlessParameters,
                                  n_points: int = 64,
                                  smooth: bool = True) -> Dict[str, np.ndarray]:
    """Ресэмплинг pD(Y), qD(Y) на равномерной сетке по log10(Y).

    Возвращает словарь с ключами: Y_new, pD_new, qD_new.
    """
    series = get_dimensionless_series(dimensionless)
    Y = series["Y"]
    pD = series["pD"]
    qD = series["qD"]
    if np.any(Y <= 0):
        Y = np.clip(Y, 1e-30, None)
    y_min, y_max = np.nanmin(Y), np.nanmax(Y)
    if not np.isfinite(y_min) or not np.isfinite(y_max) or y_min <= 0 or y_min == y_max:
        return {"Y_new": Y, "pD_new": pD, "qD_new": qD}
    log_grid = np.linspace(np.log10(y_min), np.log10(y_max), n_points)
    Y_new = 10 ** log_grid
    interp_p = DimensionlessCurveInterpolator1D(use_logY=True, apply_savgol=smooth)
    interp_q = DimensionlessCurveInterpolator1D(use_logY=True, apply_savgol=smooth)
    interp_p.fit(Y, pD)
    interp_q.fit(Y, qD)
    pD_new = interp_p.predict(Y_new)
    qD_new = interp_q.predict(Y_new)
    return {"Y_new": Y_new, "pD_new": pD_new, "qD_new": qD_new}


class PhysicsConstrainedDimensionlessInterpolator:
    """Физически ограниченная интерполяция для безразмерных кривых"""
    
    def __init__(self):
        self.fitted = False
        self.interpolator = None
        self.constraints = {
            'max_skin': 50.0,
            'min_skin': -10.0,
            'max_n_fractures': 100,
            'min_n_fractures': 1,
            'max_a_l_ratio': 1.0,
            'min_a_l_ratio': 0.01,
            'max_pressure_gradient': 100.0,  # МПа/час
            'min_flow_rate': 0.0,
            'max_flow_rate': 1000.0  # м³/сут
        }
    
    def fit(self, 
            time: pd.Series,
            pressure: pd.Series,
            flow_rate: pd.Series,
            well_params: Dict[str, float]) -> 'PhysicsConstrainedDimensionlessInterpolator':
        """Обучение с физическими ограничениями"""
        self.interpolator = DimensionlessInterpolator(method='rbf')
        self.interpolator.fit(time, pressure, flow_rate, well_params)
        self.fitted = True
        return self
    
    def predict(self, 
                target_times: np.ndarray,
                target_params: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
        """Предсказание с физическими ограничениями"""
        if not self.fitted:
            raise ValueError("Интерполятор не обучен")
        
        # Применяем физические ограничения к параметрам
        constrained_params = target_params.copy()
        
        # Ограничиваем параметры ГРП
        constrained_params['skin'] = np.clip(
            constrained_params.get('skin', 0), 
            self.constraints['min_skin'], 
            self.constraints['max_skin']
        )
        
        constrained_params['N'] = np.clip(
            constrained_params.get('N', 1), 
            self.constraints['min_n_fractures'], 
            self.constraints['max_n_fractures']
        )
        
        constrained_params['a_L'] = np.clip(
            constrained_params.get('a_L', 0.1), 
            self.constraints['min_a_l_ratio'], 
            self.constraints['max_a_l_ratio']
        )
        
        # Получаем предсказания
        pressure, flow_rate = self.interpolator.predict(target_times, constrained_params)
        
        # Применяем ограничения к результатам
        # Ограничиваем градиент давления
        if len(pressure) > 1:
            dt = np.diff(target_times)
            dp = np.diff(pressure)
            gradient = dp / dt
            
            # Если градиент слишком большой, сглаживаем
            high_gradient = np.abs(gradient) > self.constraints['max_pressure_gradient']
            if np.any(high_gradient):
                # Применяем скользящее среднее
                window = min(3, len(pressure))
                pressure = pd.Series(pressure).rolling(window=window, center=True).mean().values
        
        # Ограничиваем дебит
        flow_rate = np.clip(flow_rate, 
                          self.constraints['min_flow_rate'],
                          self.constraints['max_flow_rate'])
        
        return pressure, flow_rate


class DimensionlessExtrapolator:
    """Экстраполятор для безразмерных кривых"""
    
    def __init__(self, method: str = 'physics_constrained'):
        self.method = method
        self.fitted = False
        self.interpolator = None
        
    def fit(self, 
            time: pd.Series,
            pressure: pd.Series,
            flow_rate: pd.Series,
            well_params: Dict[str, float]) -> 'DimensionlessExtrapolator':
        """Обучение экстраполятора"""
        if self.method == 'physics_constrained':
            self.interpolator = PhysicsConstrainedDimensionlessInterpolator()
        else:
            self.interpolator = DimensionlessInterpolator(method=self.method)
        
        self.interpolator.fit(time, pressure, flow_rate, well_params)
        self.fitted = True
        return self
    
    def extrapolate(self, 
                   future_times: np.ndarray,
                   extrapolation_params: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
        """Экстраполяция в будущее"""
        if not self.fitted:
            raise ValueError("Экстраполятор не обучен")
        
        # Получаем предсказания
        pressure, flow_rate = self.interpolator.predict(future_times, extrapolation_params)
        
        # Применяем физически обоснованные ограничения для экстраполяции
        if self.method == 'physics_constrained':
            # Экспоненциальное затухание для давления
            time_decay = np.exp(-future_times / (future_times.max() * 0.1))
            pressure = pressure * time_decay
            
            # Экспоненциальное затухание для дебита
            flow_rate = flow_rate * time_decay
        
        return pressure, flow_rate


# Функции для удобного использования
def convert_to_dimensionless_curves(time: pd.Series,
                                   pressure: pd.Series,
                                   flow_rate: pd.Series,
                                   well_params: Dict[str, float]) -> DimensionlessParameters:
    """Конвертация в безразмерные кривые"""
    converter = DimensionlessConverter()
    return converter.convert_to_dimensionless(time, pressure, flow_rate, well_params)


def interpolate_dimensionless_curves(time: pd.Series,
                                   pressure: pd.Series,
                                   flow_rate: pd.Series,
                                   well_params: Dict[str, float],
                                   target_times: np.ndarray,
                                   target_params: Dict[str, float],
                                   method: str = 'rbf') -> Tuple[np.ndarray, np.ndarray]:
    """Интерполяция в пространстве безразмерных кривых"""
    interpolator = DimensionlessInterpolator(method=method)
    interpolator.fit(time, pressure, flow_rate, well_params)
    return interpolator.predict(target_times, target_params)


def extrapolate_dimensionless_curves(time: pd.Series,
                                    pressure: pd.Series,
                                    flow_rate: pd.Series,
                                    well_params: Dict[str, float],
                                    future_times: np.ndarray,
                                    extrapolation_params: Dict[str, float],
                                    method: str = 'physics_constrained') -> Tuple[np.ndarray, np.ndarray]:
    """Экстраполяция безразмерных кривых"""
    extrapolator = DimensionlessExtrapolator(method=method)
    extrapolator.fit(time, pressure, flow_rate, well_params)
    return extrapolator.extrapolate(future_times, extrapolation_params)


def create_dimensionless_type_curves(skin_range: Tuple[float, float] = (-5, 20),
                                   n_fractures_range: Tuple[int, int] = (1, 50),
                                   a_l_range: Tuple[float, float] = (0.01, 0.5),
                                   n_points: int = 100) -> Dict[str, np.ndarray]:
    """Создание библиотеки безразмерных эталонных кривых"""
    # Создаем сетку параметров
    skin_values = np.linspace(skin_range[0], skin_range[1], 10)
    n_fractures_values = np.linspace(n_fractures_range[0], n_fractures_range[1], 10)
    a_l_values = np.linspace(a_l_range[0], a_l_range[1], 10)
    
    type_curves = {}
    
    for skin in skin_values:
        for n in n_fractures_values:
            for a_l in a_l_values:
                # Создаем временной ряд
                time = np.linspace(0.1, 100, n_points)
                
                # Физически обоснованные кривые
                # Билинейное течение
                bilinear_pressure = 100 * np.exp(-0.05 * time) * (1 + skin * 0.1)
                bilinear_flow = 50 * np.exp(-0.1 * time) * (1 + n * 0.01)
                
                # Линейное течение
                linear_pressure = 80 * np.exp(-0.1 * time) * (1 + skin * 0.05)
                linear_flow = 40 * np.exp(-0.2 * time) * (1 + n * 0.02)
                
                # Псевдорадиальное течение
                pseudoradial_pressure = 60 * np.exp(-0.2 * time) * (1 - skin * 0.1)
                pseudoradial_flow = 30 * np.exp(-0.3 * time) * (1 - n * 0.01)
                
                # Сохраняем кривые
                curve_id = f"skin_{skin:.1f}_n_{n:.0f}_al_{a_l:.3f}"
                type_curves[curve_id] = {
                    'time': time,
                    'bilinear_pressure': bilinear_pressure,
                    'bilinear_flow': bilinear_flow,
                    'linear_pressure': linear_pressure,
                    'linear_flow': linear_flow,
                    'pseudoradial_pressure': pseudoradial_pressure,
                    'pseudoradial_flow': pseudoradial_flow,
                    'skin': skin,
                    'n_fractures': n,
                    'a_l_ratio': a_l
                }
    
    return type_curves
