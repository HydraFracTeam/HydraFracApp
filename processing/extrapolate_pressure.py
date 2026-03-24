import numpy as np
from sklearn.metrics import mean_squared_error

from core.models import ProcessingDynamicData


# --------------------------------------------------
# метрика
# --------------------------------------------------

def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


# --------------------------------------------------
# выбор модели в log-времени
# --------------------------------------------------
def select_degree_model(t: np.ndarray, P: np.ndarray) -> int:

    positive = t[t > 0]

    if len(positive) == 0:
        raise ValueError("Time array contains no positive values")

    eps = np.min(np.diff(positive)) if len(positive) > 1 else positive[0] * 1e-3

    x = np.log(t + eps)

    n = len(x)
    holdout = max(int(n * 0.2), 3)

    x_train = x[:-holdout]
    P_train = P[:-holdout]

    x_test = x[-holdout:]
    P_test = P[-holdout:]

    scores = {}

    # polynomial models
    for deg in (1, 2, 3):

        try:

            poly = np.poly1d(np.polyfit(x_train, P_train, deg))

            pred = poly(x_test)

            scores[("poly", deg)] = rmse(P_test, pred)

        except Exception:
            continue

    if not scores:
        raise RuntimeError("No valid model could be fitted")

    return min(scores, key=scores.get)[1]


# --------------------------------------------------
# построение модели
# --------------------------------------------------

def fit_log_model(t: np.ndarray, P: np.ndarray, degree: int):

    positive = t[t > 0]

    eps = np.min(np.diff(positive)) if len(positive) > 1 else positive[0] * 1e-3

    x = np.log(t + eps)

    coeff = np.polyfit(x, P, degree)

    return np.poly1d(coeff), eps

# --------------------------------------------------
# экстраполяция
# --------------------------------------------------

def extrapolate_pressure(
    data: ProcessingDynamicData,
) -> ProcessingDynamicData:

    if data.is_P_extrapolated:
        raise RuntimeError("Pressure already extrapolated")

    if not data.is_t_extrapolated:
        raise RuntimeError("Time must be extrapolated first")

    t = data.t
    P = data.P

    if np.isnan(P).any():
        raise ValueError("Pressure contains NaN")

    # если время уже расширено — расширяем P
    if len(P) < len(t):

        P_ext = np.full(len(t), np.nan)
        P_ext[:len(P)] = P

        P = P_ext

    n_original = np.sum(~data.t_extrapolated_mask)

    t_train = t[:n_original]
    P_train = P[:n_original]
    
    tail_fraction = 0.4
    start = int(len(t_train) * (1 - tail_fraction))

    t_train = t_train[start:]
    P_train = P_train[start:]

    degree = select_degree_model(t_train, P_train)


    model, eps = fit_log_model(t_train, P_train, degree)

    t_future = t[data.t_extrapolated_mask]
    
    P_future = model(np.log(t_future + eps))
    # новые точки времени


    # физическое ограничение: давление не должно расти
    P_future = np.minimum.accumulate(P_future)

    # объединяем массив
    P_ext = P.copy()
    P_ext[data.t_extrapolated_mask] = P_future

    # маска
    mask = data.t_extrapolated_mask.copy()

    # запись
    data.P = P_ext
    data.P_extrapolated_mask = mask
    data.is_P_extrapolated = True

    return data
