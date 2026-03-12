import numpy as np
from scipy.integrate import trapezoid


def compute_metric(a1, a2, metric_type):

    if metric_type == "L2":
        return np.sum((a1 - a2) ** 2)

    elif metric_type == "L1":
        return np.sum(np.abs(a1 - a2))

    elif metric_type == "integral":
        return np.abs(trapezoid(a1) - trapezoid(a2))

    else:
        raise ValueError("Unknown metric")