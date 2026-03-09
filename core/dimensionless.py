import numpy as np


def compute_x(k: float, h: float, delta_p: np.ndarray, mu: float, bo: float, Q: np.ndarray) -> np.ndarray:
    """
    Calculate dimensionless filtration parameter X for oil wells.
    
    Formula: X = (0.00864 * k * h * |ΔP|) / (μ * Bo * Q/N)
    
    Args:
        k: 
        h: Formation height
        delta_p: Pressure drop array
        mu: Viscosity
        bo: Oil volume coefficient
        q_per_fracture: Flow rate per fracture array
        
    Returns:
        X: Dimensionless filtration parameter array
    """
    abs_delta_p = np.abs(delta_p)
    numerator = 0.00864 * k * h * abs_delta_p
    denominator = mu * bo * Q
    
    # Avoid division by zero
    denominator = np.where(denominator == 0, 1e-10, denominator)
    
    x_result = numerator / denominator
    return x_result


def compute_y(q_per_fracture: np.ndarray, bo: float, t: np.ndarray, phi: float, ct: float, 
              h: float, delta_p: np.ndarray, l: float) -> np.ndarray:
    """
    Calculate dimensionless capacity parameter Y.
    
    Formula: Y = (Q/N * Bo * t) / (24 * φ * Ct * h * |ΔP| * L^2)
    
    Args:
        q_per_fracture: Flow rate per fracture array
        bo: Oil volume coefficient
        t: Time array
        phi: Porosity
        ct: Total compressibility
        h: Formation height
        delta_p: Pressure drop array
        l: Fracture half-length
        
    Returns:
        Y: Dimensionless capacity parameter array
    """
    # TODO: Implement the actual formula for computing Y based on physics
    # This is a placeholder implementation
    abs_delta_p = np.abs(delta_p)
    numerator = q_per_fracture * bo * t
    denominator = 24 * phi * ct * h * abs_delta_p * (l ** 2)
    
    # Avoid division by zero
    denominator = np.where(denominator == 0, 1e-10, denominator)
    
    y_result = numerator / denominator
    return y_result

