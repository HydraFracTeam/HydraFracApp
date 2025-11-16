"""
Модуль фильтрации безразмерных кривых для МГРП.
Реализует физически корректную фильтрацию и унифицированную интерполяцию.
"""

from .filters import SignalFilters
from .physics import PhysicsConstraints
from .unified_interpolator import UnifiedInterpolator
from .utils import (
    compute_snr,
    compute_derivative_variance,
    compute_oscillation_score,
    detect_log_scale,
    select_filter_method,
    fill_missing_values,
    remove_outliers
)

# Опциональный импорт ML-денойзера
try:
    from .denoise import MLDenoiser, apply_ml_denoising
    __all__ = [
        'SignalFilters',
        'PhysicsConstraints',
        'UnifiedInterpolator',
        'MLDenoiser',
        'apply_ml_denoising',
        'compute_snr',
        'compute_derivative_variance',
        'compute_oscillation_score',
        'detect_log_scale',
        'select_filter_method',
        'fill_missing_values',
        'remove_outliers'
    ]
except ImportError:
    __all__ = [
        'SignalFilters',
        'PhysicsConstraints',
        'UnifiedInterpolator',
        'compute_snr',
        'compute_derivative_variance',
        'compute_oscillation_score',
        'detect_log_scale',
        'select_filter_method',
        'fill_missing_values',
        'remove_outliers'
    ]

