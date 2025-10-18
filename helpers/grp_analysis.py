import numpy as np
import pandas as pd
from typing import Tuple, Dict, Optional, List
from scipy import signal
from scipy.optimize import curve_fit

from schemas.well_data import WellTimeSeries, FlowRegimeAnalysis, TypeCurveMatch


def compute_pressure_derivative(time_series: WellTimeSeries) -> pd.Series:
    """
    Вычисляет производную давления по времени для анализа режимов течения.
    """
    time = time_series.time
    pressure = time_series.pressure
    
    # Используем логарифмическую производную для лучшей стабильности
    log_time = np.log(time)
    log_pressure = np.log(pressure)
    
    # Численная производная
    derivative = np.gradient(log_pressure) / np.gradient(log_time)
    
    # Умножаем на время для получения производной давления
    pressure_derivative = derivative * pressure
    
    return pd.Series(pressure_derivative, index=time.index, name='dP/dt')


def compute_flow_rate_derivative(time_series: WellTimeSeries) -> pd.Series:
    """
    Вычисляет производную дебита по времени.
    """
    time = time_series.time
    flow_rate = time_series.flow_rate
    
    derivative = np.gradient(flow_rate) / np.gradient(time)
    
    return pd.Series(derivative, index=time.index, name='dQ/dt')


def analyze_flow_regime(time_series: WellTimeSeries) -> FlowRegimeAnalysis:
    """
    Анализирует режим течения на основе производных давления и дебита.
    """
    # Вычисляем производные
    dp_dt = compute_pressure_derivative(time_series)
    dq_dt = compute_flow_rate_derivative(time_series)
    
    # Анализируем наклон кривой давления в логарифмическом масштабе
    log_time = np.log(time_series.time + 1e-10)  # Добавляем малое значение для избежания log(0)
    log_pressure = np.log(time_series.pressure + 1e-10)
    
    # Проверяем на наличие NaN или inf значений
    valid_mask = np.isfinite(log_time) & np.isfinite(log_pressure)
    if not np.any(valid_mask):
        return FlowRegimeAnalysis(
            regime_type="Неопределенный",
            confidence=0.0,
            characteristic_time=None,
            parameters={'error': 'Некорректные данные'}
        )
    
    log_time_clean = log_time[valid_mask]
    log_pressure_clean = log_pressure[valid_mask]
    
    # Линейная регрессия для определения наклона с обработкой ошибок
    try:
        if len(log_time_clean) < 2:
            slope = 0.0
        else:
            # Используем более стабильный метод для линейной регрессии
            slope = np.polyfit(log_time_clean, log_pressure_clean, 1)[0]
    except (np.linalg.LinAlgError, ValueError):
        # Если SVD не сходится, используем простой метод наклона
        if len(log_time_clean) >= 2:
            slope = (log_pressure_clean[-1] - log_pressure_clean[0]) / (log_time_clean[-1] - log_time_clean[0])
        else:
            slope = 0.0
    
    # Классификация режима течения
    if slope > -0.5:
        regime_type = "Билинейное течение"
        confidence = min(abs(slope + 0.5) / 0.5, 1.0)
    elif slope > -1.0:
        regime_type = "Линейное течение"
        confidence = min(abs(slope + 0.75) / 0.25, 1.0)
    else:
        regime_type = "Псевдорадиальное течение"
        confidence = min(abs(slope + 1.0) / 0.5, 1.0)
    
    # Определяем характерное время перехода
    characteristic_time = None
    if len(time_series.time) > 10:
        try:
            # Ищем точку изменения наклона с более стабильным методом
            window_size = max(5, len(time_series.time) // 10)
            rolling_slope = []
            
            for i in range(window_size, len(log_time_clean)):
                window_time = log_time_clean[i-window_size:i]
                window_pressure = log_pressure_clean[i-window_size:i]
                
                if len(window_time) >= 2:
                    try:
                        local_slope = np.polyfit(window_time, window_pressure, 1)[0]
                        rolling_slope.append(local_slope)
                    except (np.linalg.LinAlgError, ValueError):
                        rolling_slope.append(0.0)
            
            if rolling_slope:
                rolling_slope = np.array(rolling_slope)
                slope_change = np.abs(np.diff(rolling_slope))
                if len(slope_change) > 0:
                    max_change_idx = np.argmax(slope_change)
                    if max_change_idx < len(time_series.time):
                        characteristic_time = float(time_series.time.iloc[max_change_idx + window_size])
        except Exception:
            characteristic_time = None
    
    return FlowRegimeAnalysis(
        regime_type=regime_type,
        confidence=confidence,
        characteristic_time=characteristic_time,
        parameters={
            'slope': slope,
            'skin_factor': time_series.skin,
            'fractures_count': time_series.fractures_count,
            'a_l_ratio': time_series.a_l_ratio
        }
    )


def generate_type_curves(skin: float, n_fractures: int, a_l_ratio: float, 
                        time_range: np.ndarray) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """
    Генерирует эталонные кривые для различных режимов течения.
    """
    curves = {}
    
    # Билинейное течение
    def bilinear_curve(t):
        return 100 * np.exp(-0.05 * t) * (1 + skin * 0.1)
    
    # Линейное течение
    def linear_curve(t):
        return 80 * np.exp(-0.1 * t) * (1 + skin * 0.05)
    
    # Псевдорадиальное течение
    def pseudoradial_curve(t):
        return 60 * np.exp(-0.2 * t) * (1 - skin * 0.1)
    
    curves['bilinear'] = (time_range, bilinear_curve(time_range))
    curves['linear'] = (time_range, linear_curve(time_range))
    curves['pseudoradial'] = (time_range, pseudoradial_curve(time_range))
    
    return curves


def match_type_curves(time_series: WellTimeSeries) -> TypeCurveMatch:
    """
    Сопоставляет данные скважины с эталонными кривыми.
    """
    # Генерируем эталонные кривые
    time_range = np.linspace(time_series.time.min(), time_series.time.max(), 100)
    type_curves = generate_type_curves(
        time_series.skin, 
        time_series.fractures_count, 
        time_series.a_l_ratio, 
        time_range
    )
    
    best_match = None
    best_quality = 0
    best_residuals = None
    
    for curve_type, (t_curve, q_curve) in type_curves.items():
        # Интерполируем эталонную кривую на временные точки данных
        q_interp = np.interp(time_series.time, t_curve, q_curve)
        
        # Вычисляем остатки
        residuals = time_series.flow_rate - q_interp
        
        # Качество сопоставления (R²)
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((time_series.flow_rate - np.mean(time_series.flow_rate))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        if r_squared > best_quality:
            best_quality = r_squared
            best_match = curve_type
            best_residuals = pd.Series(residuals, index=time_series.time.index)
    
    # Оцененные параметры
    estimated_params = {
        'skin_factor': time_series.skin,
        'fractures_count': time_series.fractures_count,
        'a_l_ratio': time_series.a_l_ratio,
        'r_squared': best_quality
    }
    
    return TypeCurveMatch(
        curve_type=best_match or 'unknown',
        match_quality=best_quality,
        estimated_parameters=estimated_params,
        residuals=best_residuals or pd.Series()
    )


def compute_well_productivity_index(time_series: WellTimeSeries) -> Dict[str, float]:
    """
    Вычисляет индекс продуктивности скважины.
    """
    # Средний дебит
    avg_flow_rate = time_series.flow_rate.mean()
    
    # Среднее давление
    avg_pressure = time_series.pressure.mean()
    
    # Индекс продуктивности (упрощенная формула)
    productivity_index = avg_flow_rate / avg_pressure if avg_pressure > 0 else 0
    
    # Коэффициент эффективности ГРП
    fracture_efficiency = (time_series.fractures_count * time_series.fracture_length) / time_series.thickness
    
    return {
        'productivity_index': productivity_index,
        'fracture_efficiency': fracture_efficiency,
        'average_flow_rate': avg_flow_rate,
        'average_pressure': avg_pressure,
        'skin_impact': time_series.skin,
        'total_fracture_length': time_series.fractures_count * time_series.fracture_length
    }


def detect_flow_regime_transitions(time_series: WellTimeSeries) -> List[Dict]:
    """
    Обнаруживает переходы между режимами течения.
    """
    transitions = []
    
    # Вычисляем производную давления
    dp_dt = compute_pressure_derivative(time_series)
    
    # Сглаживаем производную для уменьшения шума
    smoothed_derivative = pd.Series(dp_dt).rolling(window=5, center=True).mean()
    
    # Ищем точки изменения наклона
    derivative_diff = smoothed_derivative.diff()
    
    # Порог для обнаружения значительных изменений
    threshold = derivative_diff.std() * 2
    
    for i in range(1, len(derivative_diff)):
        if abs(derivative_diff.iloc[i]) > threshold:
            transitions.append({
                'time': float(time_series.time.iloc[i]),
                'pressure': float(time_series.pressure.iloc[i]),
                'flow_rate': float(time_series.flow_rate.iloc[i]),
                'derivative_change': float(derivative_diff.iloc[i]),
                'regime_change': 'detected'
            })
    
    return transitions
