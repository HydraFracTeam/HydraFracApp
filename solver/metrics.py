# solver/metrics.py
import numpy as np
def compute_metric(alpha1, alpha2, metric_type="integral", X=None):
    if metric_type == "L2":
        return np.sqrt(np.mean((alpha1 - alpha2) ** 2))
    elif metric_type == "L1":
        return np.mean(np.abs(alpha1 - alpha2))
    else:  # integral
        if X is None:
            X = np.arange(len(alpha1), dtype=float)
        # np.trapz was renamed to np.trapezoid in NumPy 2.0
        trapz_fn = getattr(np, 'trapezoid', getattr(np, 'trapz', None))
        if trapz_fn is None:
            return np.trapz(np.abs(alpha1 - alpha2), X)
        return trapz_fn(np.abs(alpha1 - alpha2), X)