import numpy as np


def calculate_x(k: float, h: float, delta_p: np.ndarray, mu: float, B: float, Q: np.ndarray) -> np.ndarray:
    """
    Расчёт безразмерного фильтрационного параметра X.

    Формула:
        X = (0.00864 * k * h * |ΔP|) / (μ * Bo * Q)

    Параметры:
        k (float)           : проницаемость пласта
        h (float)           : толщина пласта
        delta_p (np.ndarray): депрессия (разность давлений ΔP)
        mu (float)          : вязкость
        B (float)          : объемный коэффициент нефти
        Q (np.ndarray)      : дебит (уже нормированный на число трещин)

    Возвращает:
        np.ndarray : массив значений безразмерного параметра X
    """

    # модуль депрессии
    abs_delta_p = np.abs(delta_p)

    # числитель формулы
    numerator = 0.00864 * k * h * abs_delta_p

    # знаменатель
    denominator = mu * B * Q

    # защита от деления на ноль
    denominator = np.where(denominator == 0, 1e-3, denominator)

    x_result = numerator / denominator
    return x_result


def calculate_y(
    Q: np.ndarray,
    B: float,
    t: np.ndarray,
    phi: float,
    ct: float,
    h: float,
    delta_p: np.ndarray,
    L: float
) -> np.ndarray:
    """
    Расчёт безразмерного ёмкостного параметра Y.

    Формула:
        Y = (Q/N * Bo * t) / (24 * φ * Ct * h * |ΔP| * L²)

    Параметры:
        Q (np.ndarray): дебит на одну трещину
        B (float)                  : объемный коэффициент нефти
        t (np.ndarray)             : время
        phi (float)                : пористость
        ct (float)                 : общая сжимаемость системы
        h (float)                  : толщина пласта
        delta_p (np.ndarray)       : депрессия (ΔP)
        L (float)                  : полудлина трещины

    Возвращает:
        np.ndarray : массив значений безразмерного параметра Y
    """

    # модуль депрессии
    abs_delta_p = np.abs(delta_p)

    # числитель формулы
    numerator = Q * B * t

    # знаменатель
    denominator = 24 * phi * ct * h * abs_delta_p * (L ** 2)

    # защита от деления на ноль
    denominator = np.where(denominator == 0, 1e-3, denominator)

    y_result = numerator / denominator
    return y_result

