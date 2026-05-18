# solver/derivative.py
import numpy as np
def compute_derivative(X, Y, mode="linear"):
    mask = (X > 0) & (Y > 0)
    X = X[mask]
    Y = Y[mask]
    if mode == "loglog":
        X = np.log(X)
        Y = np.log(Y)
    alpha = np.gradient(Y, X)
    return X, alpha