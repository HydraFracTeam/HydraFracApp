import numpy as np

def calculate_burde(t: np.ndarray, dP: np.ndarray) -> np.ndarray:
    """
    Расчёт производной Бурде: d(ΔP) / d(ln t) между соседними точками.

    Вход:
        t  - время (np.ndarray)
        dP - перепад давления ΔP (np.ndarray)

    Выход:
        burde - np.ndarray той же длины, первая точка = NaN
    """

    t = np.asarray(t, dtype=float)
    dP = np.asarray(dP, dtype=float)

    ln_t = np.log(t, where=(t > 0), out=np.full_like(t, np.nan))

    delta_dP = np.diff(dP)
    delta_ln_t = np.diff(ln_t)

    burde = np.full_like(t, np.nan)

    valid = delta_ln_t != 0
    burde[1:][valid] = delta_dP[valid] / delta_ln_t[valid]

    return burde
