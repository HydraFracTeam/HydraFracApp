"""
Functions for scaling reference curves by well length (W).
This module handles the scaling of Y values based on differences between 
reference curve W and user-provided W.
"""

import numpy as np


def scale_reference_by_w(y_std: np.ndarray, w_ref: float, w_user: float) -> np.ndarray:
    """
    Scale reference Y values by the ratio of reference W to user W.
    
    Formula: Y_scaled = Y_std * (W_ref / W_user)
    
    Args:
        y_std: Standard Y values from reference curve
        w_ref: Well length from reference curve
        w_user: Well length provided by user
        
    Returns:
        y_scaled: Scaled Y values
    """
    # Avoid division by zero
    w_user_safe = w_user if w_user != 0 else 1e-10
    
    scale_factor = w_ref / w_user_safe
    y_scaled = y_std * scale_factor
    
    return y_scaled
