"""
Objective functions for calculating error metrics between curves.
Implements L1 and L2 norms for measuring mismatch between reference and calculated curves.
"""

import numpy as np
from scipy.integrate import trapezoid


def l1_error(x: np.ndarray, y1: np.ndarray, y2: np.ndarray) -> float:
    """
    Calculate L1-norm error (integral of absolute difference) between two curves.
    
    Formula: ∫|Y_std - Y_calc| dX
    
    Args:
        x: X values (independent variable)
        y1: First Y array (e.g., reference curve)
        y2: Second Y array (e.g., calculated curve)
        
    Returns:
        error: L1-norm error value
    """
    # Calculate absolute difference
    abs_diff = np.abs(y1 - y2)
    
    # Integrate using trapezoidal rule
    error = trapezoid(abs_diff, x)
    
    return float(error)


def l2_error(x: np.ndarray, y1: np.ndarray, y2: np.ndarray) -> float:
    """
    Calculate L2-norm error (root mean square error) between two curves.
    
    Formula: √∫(Y_std - Y_calc)² dX
    
    Args:
        x: X values (independent variable)
        y1: First Y array (e.g., reference curve)
        y2: Second Y array (e.g., calculated curve)
        
    Returns:
        error: L2-norm error value
    """
    # Calculate squared difference
    squared_diff = (y1 - y2) ** 2
    
    # Integrate using trapezoidal rule and take square root
    integral = trapezoid(squared_diff, x)
    error = np.sqrt(integral)
    
    return float(error)
