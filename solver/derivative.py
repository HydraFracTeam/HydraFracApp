import numpy as np


def compute_derivative(X, Y, mode="linear"):
    """
    Вычисление производной dy/dx.
    
    Args:
        X (np.ndarray): X координаты кривой
        Y (np.ndarray): Y координаты кривой
        mode (str): 'linear' - линейный масштаб, 'loglog' - двойной логарифмический
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: Отфильтрованные X и производная alpha
    """

    mask = (X > 0) & (Y > 0)
    X = X[mask]
    Y = Y[mask]

    if mode == "loglog":
        X = np.log(X)
        Y = np.log(Y)

    alpha = np.gradient(Y, X)

    return X, alpha