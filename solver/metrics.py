import numpy as np
from scipy.integrate import trapezoid


def compute_metric(a1, a2, metric_type, X=None):
    """
    Метрика расстояния между двумя массивами производных.

    Args:
        a1, a2      : массивы производных одинаковой длины
        metric_type : "L2", "L1", "integral"
        X           : координаты для интегрирования (обязателен для "integral")

    "integral" — интеграл модуля разности, то есть площадь расхождения
    между двумя кривыми производных. Это НЕ разность интегралов:

        правильно : trapezoid(|a1 - a2|, X)   — площадь между кривыми
        неверно   : |trapezoid(a1) - trapezoid(a2)| — может быть нулём
                    при полном расхождении с разными знаками

    X передаётся явно потому что в loglog-режиме compute_derivative
    возвращает X_out = log(X) — интегрирование должно идти по тем же
    координатам что и производная.
    """
    if metric_type == "L2":
        return float(np.sum((a1 - a2) ** 2))

    elif metric_type == "L1":
        return float(np.sum(np.abs(a1 - a2)))

    elif metric_type == "integral":
        diff = np.abs(a1 - a2)
        if X is not None:
            return float(trapezoid(diff, X))
        return float(trapezoid(diff))

    else:
        raise ValueError(f"Unknown metric_type: {metric_type!r}")
