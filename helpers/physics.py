import numpy as np
from typing import Tuple


def compute_transmissivity(permeability_md: np.ndarray, thickness_m: np.ndarray) -> np.ndarray:
    """
    Векторизованно вычисляет трансмиссивность T = k * h.
    Ожидает согласованные массивы одинаковой длины.
    """
    return np.multiply(permeability_md, thickness_m)


def compute_pore_volume(porosity: np.ndarray, thickness_m: np.ndarray) -> np.ndarray:
    """
    Векторизованно вычисляет удельный поровый объём на колонну: Vp = phi * h.
    """
    return np.multiply(porosity, thickness_m)


def compute_darcy_flux(permeability_m2: np.ndarray, viscosity_pa_s: np.ndarray, pressure_grad_pa_per_m: np.ndarray) -> np.ndarray:
    """
    Закон Дарси в одномерной форме (удельный расход): q = - (k / mu) * dp/dx.
    Знак минус отражает направление потока по убыванию давления.
    """
    return -np.divide(permeability_m2, viscosity_pa_s) * pressure_grad_pa_per_m


def compute_diffusivity(permeability_m2: np.ndarray, compressibility_pa_inv: np.ndarray, viscosity_pa_s: np.ndarray, porosity: np.ndarray) -> np.ndarray:
    """
    Давление-диффузивность: alpha = k / (mu * c_t * phi).
    """
    denominator = np.multiply(viscosity_pa_s, np.multiply(compressibility_pa_inv, porosity))
    return np.divide(permeability_m2, denominator)


def compute_grp_parameters(skin: float, n_fractures: int, aL_ratio: float, 
                          permeability: float, thickness: float) -> dict:
    """Вычисление параметров ГРП"""
    return {
        'effective_skin': skin,
        'fracture_intensity': n_fractures / thickness,
        'conductivity_index': aL_ratio * permeability
    }

def predict_production_curve(skin: float, n: int, aL: float, 
                           time_range: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Упрощенная ML-модель для прогноза кривой (заглушка)"""
    # Здесь будет ваша обученная модель
    X = time_range
    Y = 100 * np.exp(-0.1 * X) * (1 - skin * 0.1) * (1 + n * 0.05) * (1 + aL * 2)
    return X, Y

def classify_flow_regime(skin: float, n: int, aL: float) -> str:
    """Классификация режима течения по параметрам ГРП"""
    if n > 5 and aL > 0.3:
        return "Билинейное/линейное течение"
    elif skin > 2:
        return "Течение с повреждением"
    else:
        return "Псевдорадиальное течение"
