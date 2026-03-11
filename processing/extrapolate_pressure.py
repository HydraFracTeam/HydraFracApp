# import numpy as np
# from core.app_state import ProcessingDynamicData


# def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
#     return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


# def _poly_predict(t_train, P_train, t_pred, degree):

#     coeffs = np.polyfit(t_train, P_train, degree)
#     poly = np.poly1d(coeffs)

#     return poly(t_pred)


# def _log_predict(t_train, P_train, t_pred):

#     log_t = np.log(t_train)
#     coeffs = np.polyfit(log_t, P_train, 1)
#     a, b = coeffs

#     return a * np.log(t_pred) + b


# def _evaluate_models(t, P):

#     n = len(t)

#     holdout = max(int(n * 0.2), 3)

#     train_t = t[:-holdout]
#     train_P = P[:-holdout]

#     test_t = t[-holdout:]
#     test_P = P[-holdout:]

#     models = {}

#     # polynomial models
#     for deg in (3,):

#         pred = _poly_predict(train_t, train_P, test_t, deg)

#         models[f"poly{deg}"] = _rmse(test_P, pred)

#     # log model
#     if np.all(train_t > 0):

#         pred = _log_predict(train_t, train_P, test_t)

#         models["log"] = _rmse(test_P, pred)

#     best_model = min(models, key=models.get)
#     print(best_model)

#     return best_model


# def _fit_predict_full(t, P, t_new, model_name):

#     if model_name.startswith("poly"):

#         deg = int(model_name[-1])

#         coeffs = np.polyfit(t, P, deg)
#         poly = np.poly1d(coeffs)

#         return poly(t_new)

#     elif model_name == "log":

#         log_t = np.log(t)
#         coeffs = np.polyfit(log_t, P, 1)
#         a, b = coeffs

#         return a * np.log(t_new) + b

#     else:

#         raise ValueError("Unknown model")


# def extrapolate_pressure(
#     data: ProcessingDynamicData,
#     extend_fraction: float = 0.5,
# ) -> ProcessingDynamicData:

#     if data.is_P_extrapolated:
#         raise RuntimeError("Extrapolation already performed")

#     if not data.is_P_interpolated:
#         raise RuntimeError("Interpolation must be performed before extrapolation")

#     t = data.t
#     P = data.P

#     if np.isnan(P).any():
#         raise ValueError("Pressure still contains NaN values")

#     if len(t) < 6:
#         raise ValueError("Not enough points for extrapolation")

#     # выбор модели
#     best_model = _evaluate_models(t, P)

#     # количество новых точек
#     n = len(t)
#     n_new = max(int(n * extend_fraction), 1)

#     dt = np.average(np.diff(t))

#     t_last = t[-1]

#     t_new = t_last + dt * np.arange(1, n_new + 1)

#     # прогноз
#     P_new = _fit_predict_full(t, P, t_new, best_model)

#     # объединяем массивы
#     t_ext = np.concatenate([t, t_new])
#     P_ext = np.concatenate([P, P_new])
    
#     old_len = len(P)
#     new_len = len(P_ext)

#     # расширяем маску интерполяции
#     if data.P_interpolated_mask is not None:

#         interp_mask = np.zeros(new_len, dtype=bool)
#         interp_mask[:old_len] = data.P_interpolated_mask

#         data.P_interpolated_mask = interp_mask

#     # создаем маску экстраполяции
#     extra_mask = np.zeros(new_len, dtype=bool)
#     extra_mask[old_len:] = True

#     data.P_extrapolated_mask = extra_mask

#     # маска для времени
#     t_mask = np.zeros(new_len, dtype=bool)
#     t_mask[old_len:] = True

#     data.t_extrapolated_mask = t_mask

#     # маска экстраполяции
#     mask = np.zeros_like(P_ext, dtype=bool)
#     mask[-n_new:] = True

#     # запись результата
#     data.t = t_ext
#     data.P = P_ext
#     data.P_extrapolated_mask = mask
#     data.is_P_extrapolated = True

#     return data
