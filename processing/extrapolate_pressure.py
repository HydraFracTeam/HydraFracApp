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

# экстраполяция
def extrapolate_pressure(
    data: ProcessingDynamicData,
    jump_threshold: float = 1.2,
) -> ProcessingDynamicData:

    if data.is_P_extrapolated:
        raise RuntimeError("Pressure already extrapolated")

    if not data.is_t_extrapolated:
        raise RuntimeError("Time must be extrapolated first")

    t = data.t
    P = data.P

    if np.isnan(P).any():
        raise ValueError("Значения ряда давления содержат NaN")

    # расширение массива давления
    if len(P) < len(t):
        P_ext = np.full(len(t), np.nan)
        P_ext[:len(P)] = P
        P = P_ext

    n_original = np.sum(~data.t_extrapolated_mask)

    t_train_full = t[:n_original]
    P_train_full = P[:n_original]

    # берем хвост
    tail_fraction = 0.4
    start = int(len(t_train_full) * (1 - tail_fraction))

    t_train = t_train_full[start:]
    P_train = P_train_full[start:]

    # ОПРЕДЕЛЕНИЕ НАПРАВЛЕНИЯ ТРЕНДА
    positive = t_train[t_train > 0]
    eps = np.min(np.diff(positive)) if len(positive) > 1 else positive[0] * 1e-3

    x = np.log(t_train + eps)

    # линейная регрессия для оценки наклона
    slope = np.polyfit(x, P_train, 1)[0]

    if abs(slope) < 1e-6:
        # fallback (если почти горизонтально)
        trend_up = P_train[0] < P_train[-1]
    else:
        trend_up = slope > 0

    # МОДЕЛЬ
    degree = select_degree_model(t_train, P_train)
    model, eps = fit_log_model(t_train, P_train, degree)

    t_future = t[data.t_extrapolated_mask]
    P_future = model(np.log(t_future + eps))

    # уберем сильный скачок P для экстраполированных
    if len(P_future) > 0:
        p_last = P[n_original - 1]
        p_first_ext = P_future[0]

        diff = abs(p_last - p_first_ext)

        if diff > jump_threshold:
            shift = diff - jump_threshold

            if p_first_ext > p_last:
                P_future = P_future - shift
            else:
                P_future = P_future + shift

    # ФИЗИЧЕСКОЕ ОГРАНИЧЕНИЕ
    if trend_up:
        # КВД — давление растёт
        P_future = np.maximum.accumulate(P_future)
    else:
        # КСД — давление падает
        P_future = np.minimum.accumulate(P_future)

    # ОБЪЕДИНЕНИЕ
    P_ext = P.copy()
    P_ext[data.t_extrapolated_mask] = P_future

    data.P = P_ext
    data.P_extrapolated_mask = data.t_extrapolated_mask.copy()
    data.is_P_extrapolated = True

    return data
