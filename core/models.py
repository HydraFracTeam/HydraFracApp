"""
Models for HydraFracApp - defines the data structures used across the application.
Contains dataclasses for static parameters, dynamic parameters, and solver results.
"""

from dataclasses import dataclass
import numpy as np
from typing import Optional


@dataclass
class StaticParams:
    """
    Represents static reservoir and well parameters that do not change during optimization.
    These are considered known values and are not optimized.
    """
    phi: float  # Porosity
    mu: float   # Viscosity
    Ct: float   # Total compressibility
    B: float   # Oil volume coefficient
    h: float    # Formation height
    N: float    # Number of fractures
    W: float    # Horizontal well length
    # Add other static parameters as needed


@dataclass
class DynamicParams:
    """
    Represents dynamic parameters that are subject to optimization.
    Contains ranges for permeability and fracture length.
    """
    k_min: float  # Minimum permeability for optimization range
    k_max: float  # Maximum permeability for optimization range
    L_min: float  # Minimum fracture length for optimization range
    L_max: float  # Maximum fracture length for optimization range


@dataclass
class SolverResult:
    """
    Represents the result of the solver optimization process.
    Contains optimized parameters and associated metrics.
    """
    S_opt: float      # Optimized skin factor
    k_opt: float      # Optimized permeability
    L_opt: float      # Optimized fracture length
    error_value: float  # Error metric value (L1 or L2 norm)
    W_scale_factor: float  # W scaling coefficient
    # Add other relevant results as needed
    # For example: execution_time, convergence_info, etc.
