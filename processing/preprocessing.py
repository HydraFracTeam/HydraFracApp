"""
Preprocessing module for HydraFracApp.
Handles data cleaning, interpolation, smoothing, and conversion to numpy arrays.
All functions operate on pandas DataFrames and return numpy arrays.
"""

import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit


def interpolate_nan(df: pd.DataFrame) -> pd.DataFrame:
    """
    Interpolate NaN values in pressure data.
    
    Args:
        df: DataFrame with columns including 'P' for pressure
        
    Returns:
        DataFrame with interpolated values
    """
    df_interpolated = df.copy()
    
    # Interpolate NaN values in pressure column
    if 'P' in df_interpolated.columns:
        df_interpolated['P'] = df_interpolated['P'].interpolate(method='linear')
    
    # Also interpolate other potentially missing columns
    if 'dP' in df_interpolated.columns:
        df_interpolated['dP'] = df_interpolated['dP'].interpolate(method='linear')
    
    return df_interpolated


def smooth_pressure(df: pd.DataFrame, window_length: int = 11, polyorder: int = 3) -> pd.DataFrame:
    """
    Apply Savitzky-Golay filter to smooth pressure data.
    
    Args:
        df: DataFrame with columns including 'P' for pressure
        window_length: Length of the filter window (must be odd)
        polyorder: Order of polynomial for filtering
        
    Returns:
        DataFrame with smoothed pressure values
    """
    df_smoothed = df.copy()
    
    if 'P' in df_smoothed.columns:
        # Ensure window_length is odd and not larger than the data size
        n_points = len(df_smoothed['P'])
        if window_length >= n_points:
            window_length = n_points if n_points % 2 == 1 else n_points - 1
        if window_length < polyorder + 2:
            window_length = polyorder + 2
            if window_length % 2 == 0:
                window_length += 1
        
        if n_points >= polyorder + 2 and window_length > 0:
            df_smoothed['P'] = savgol_filter(df_smoothed['P'], window_length, polyorder)
    
    return df_smoothed


def to_numpy_arrays(df: pd.DataFrame) -> dict:
    """
    Convert DataFrame to dictionary of numpy arrays.
    
    Args:
        df: DataFrame with time, pressure, and flow rate data
        
    Returns:
        Dictionary containing numpy arrays for each column
    """
    result = {}
    
    for col in df.columns:
        result[col] = df[col].to_numpy()
    
    return result


def extrapolate_pressure(df: pd.DataFrame, n_points: int = None) -> pd.DataFrame:
    """
    Extrapolate pressure data using polynomial fitting.
    
    Args:
        df: DataFrame with time and pressure data
        n_points: Number of points to extrapolate (default: n//2)
        
    Returns:
        DataFrame with extended data
    """
    if n_points is None:
        n_points = len(df) // 2
    
    if n_points <= 0:
        return df
    
    # Prepare data for fitting
    if 't' not in df.columns or 'P' not in df.columns:
        return df  # Need both time and pressure for extrapolation
    
    t_vals = df['t'].values
    p_vals = df['P'].values
    
    # Determine the best fitting polynomial degree
    max_degree = min(5, len(t_vals) - 1)  # Prevent overfitting
    best_degree = 1
    best_rmse = float('inf')
    
    for degree in range(1, max_degree + 1):
        try:
            # Fit polynomial
            coeffs = np.polyfit(t_vals, p_vals, degree)
            poly_func = np.poly1d(coeffs)
            
            # Predict on existing data to calculate RMSE
            predicted = poly_func(t_vals)
            rmse = np.sqrt(np.mean((p_vals - predicted) ** 2))
            
            if rmse < best_rmse:
                best_rmse = rmse
                best_degree = degree
        except:
            continue  # Skip if fitting fails
    
    # Extrapolate using the best polynomial
    try:
        coeffs = np.polyfit(t_vals, p_vals, best_degree)
        poly_func = np.poly1d(coeffs)
        
        # Generate additional time points
        dt_avg = np.mean(np.diff(t_vals))
        t_extended = np.linspace(t_vals[-1] + dt_avg, 
                                t_vals[-1] + dt_avg * n_points, 
                                n_points)
        
        # Calculate extrapolated pressure values
        p_extended = poly_func(t_extended)
        
        # Create new DataFrame with extended data
        extended_df = pd.DataFrame({
            't': np.concatenate([t_vals, t_extended]),
            'P': np.concatenate([p_vals, p_extended])
        })
        
        # Copy other columns if they exist
        for col in df.columns:
            if col not in ['t', 'P']:
                original_col_values = df[col].values
                # Extend other columns with NaN or last value
                extended_values = np.full(len(extended_df), np.nan)
                extended_values[:len(original_col_values)] = original_col_values
                extended_df[col] = extended_values
        
        return extended_df
    except:
        # If extrapolation fails, return original dataframe
        return df


def preprocess_data(df: pd.DataFrame) -> dict:
    """
    Complete preprocessing pipeline: interpolate, smooth, and convert to numpy arrays.
    
    Args:
        df: Raw DataFrame with pressure/time data
        
    Returns:
        Dictionary of processed numpy arrays
    """
    # Step 1: Interpolate NaN values
    df_proc = interpolate_nan(df)
    
    # Step 2: Smooth pressure data
    df_proc = smooth_pressure(df_proc)
    
    # Step 3: Extrapolate if needed
    # df_proc = extrapolate_pressure(df_proc)  # Uncomment if extrapolation is needed
    
    # Step 4: Convert to numpy arrays
    result = to_numpy_arrays(df_proc)
    
    return result
