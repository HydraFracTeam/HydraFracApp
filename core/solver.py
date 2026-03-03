"""
Solver module for HydraFracApp.
Implements the optimization algorithm for determining S (skin), k (permeability), and L (fracture length).
Uses a hybrid approach with external S iteration and internal k-L optimization.
"""

import numpy as np
from scipy.optimize import minimize
from typing import Tuple, List
import logging

from .models import StaticParams, DynamicParams, SolverResult
from .dimensionless import compute_x, compute_y
from .w_scaling import scale_reference_by_w
from .objective import l1_error, l2_error


class Solver:
    """
    Main solver class implementing the hybrid optimization approach:
    - External loop: iterate through skin factor values
    - Internal optimization: optimize k and L using L-BFGS-B
    """
    
    def __init__(self):
        """Initialize the solver with default settings."""
        self.logger = logging.getLogger(__name__)
        
    def run(
        self,
        pressure_data: np.ndarray,
        time_data: np.ndarray,
        flow_rate_data: np.ndarray,
        static_params: StaticParams,
        dynamic_params: DynamicParams,
        reference_repo,
        skin_grid: List[float] = None
    ) -> SolverResult:
        """
        Execute the main optimization routine.
        
        Args:
            pressure_data: Array of pressure measurements
            time_data: Array of time measurements
            flow_rate_data: Array of flow rate measurements
            static_params: Static reservoir and well parameters
            dynamic_params: Optimization bounds for k and L
            reference_repo: Repository for accessing reference curves
            skin_grid: Grid of skin factor values to test (default: 0 to 5 with step 0.5)
            
        Returns:
            SolverResult: Contains optimized parameters and metrics
        """
        # Set default skin grid if not provided
        if skin_grid is None:
            skin_grid = [i * 0.5 for i in range(11)]  # 0, 0.5, 1.0, ..., 5.0
        
        best_result = None
        best_error = float('inf')
        
        # External loop: iterate through skin factor values
        for s in skin_grid:
            self.logger.info(f"Testing Skin={s}")
            
            # Get reference curve for this skin value (with interpolation if needed)
            # TODO: Implement interpolation between reference curves for intermediate S values
            ref_curve_ids = reference_repo.get_curves_by_skin(s)
            
            if not ref_curve_ids:
                # Try to find closest skins for interpolation
                available_skins = reference_repo.get_available_skins()
                if not available_skins:
                    raise ValueError("No reference curves available")
                
                # Find closest skin values for interpolation
                closest_skins = self._find_closest_skins(s, available_skins)
                
                if len(closest_skins) == 1:
                    # Direct match or closest available
                    ref_curve_ids = reference_repo.get_curves_by_skin(closest_skins[0])
                elif len(closest_skins) >= 2:
                    # Interpolate between two closest values
                    ref_x, ref_y = self._interpolate_reference_curve(
                        reference_repo, s, closest_skins[0], closest_skins[1]
                    )
                else:
                    continue
            else:
                # Get reference curve directly
                curve_id = ref_curve_ids[0]  # Take first available
                ref_x, ref_y = reference_repo.get_reference_curve(curve_id)
                
                # Get reference metadata to access W for scaling
                ref_metadata = reference_repo.get_static_metadata(curve_id)
                ref_w = ref_metadata.get('W', static_params.W)  # Default to user's W if not available
                
                # Scale reference Y by W factor
                ref_y = scale_reference_by_w(ref_y, ref_w, static_params.W)
            
            # Perform inner optimization for k and L
            current_result = self._optimize_k_and_l(
                s, pressure_data, time_data, flow_rate_data, 
                static_params, dynamic_params, ref_x, ref_y
            )
            
            if current_result.error_value < best_error:
                best_error = current_result.error_value
                best_result = current_result
                self.logger.info(f"Best result updated: S={best_result.S_opt}, "
                               f"k={best_result.k_opt}, L={best_result.L_opt}, "
                               f"error={best_result.error_value:.6f}")
        
        if best_result is None:
            raise RuntimeError("No valid solution found during optimization")
        
        return best_result
    
    def _find_closest_skins(self, target_skin: float, available_skins: List[float]) -> List[float]:
        """
        Find the closest available skin values for interpolation.
        
        Args:
            target_skin: Target skin value
            available_skins: Available skin values in the reference database
            
        Returns:
            List of closest skin values (typically 1 or 2 values)
        """
        sorted_skins = sorted(available_skins)
        
        # If exact match exists
        if target_skin in sorted_skins:
            return [target_skin]
        
        # Find two closest values
        lower_skins = [s for s in sorted_skins if s < target_skin]
        upper_skins = [s for s in sorted_skins if s > target_skin]
        
        closest_skins = []
        if lower_skins:
            closest_skins.append(lower_skins[-1])
        if upper_skins:
            closest_skins.append(upper_skins[0])
        
        return closest_skins
    
    def _interpolate_reference_curve(self, reference_repo, target_skin: float, 
                                   skin1: float, skin2: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Linearly interpolate between two reference curves for different skin values.
        
        Args:
            reference_repo: Reference repository
            target_skin: Target skin value for interpolation
            skin1: First skin value (lower)
            skin2: Second skin value (upper)
            
        Returns:
            Interpolated X and Y arrays
        """
        # Get curves for both skin values
        ids1 = reference_repo.get_curves_by_skin(skin1)
        ids2 = reference_repo.get_curves_by_skin(skin2)
        
        if not ids1 or not ids2:
            raise ValueError(f"Could not find reference curves for skins {skin1} and/or {skin2}")
        
        curve1_id = ids1[0]
        curve2_id = ids2[0]
        
        x1, y1 = reference_repo.get_reference_curve(curve1_id)
        x2, y2 = reference_repo.get_reference_curve(curve2_id)
        
        # For now, assume x values are the same for both curves
        # In practice, you might need to align or interpolate x values as well
        if not np.allclose(x1, x2, rtol=1e-5):
            # TODO: Handle case where x values are different between curves
            # This would require interpolation onto common x grid
            pass
        
        # Linear interpolation of y values
        weight = (target_skin - skin1) / (skin2 - skin1)
        interpolated_y = y1 * (1 - weight) + y2 * weight
        
        return x1, interpolated_y
    
    def _optimize_k_and_l(
        self,
        s: float,
        pressure_data: np.ndarray,
        time_data: np.ndarray,
        flow_rate_data: np.ndarray,
        static_params: StaticParams,
        dynamic_params: DynamicParams,
        ref_x: np.ndarray,
        ref_y: np.ndarray
    ) -> SolverResult:
        """
        Inner optimization to find optimal k and L for a fixed skin value.
        
        Args:
            s: Fixed skin factor
            pressure_data: Pressure measurements
            time_data: Time measurements
            flow_rate_data: Flow rate measurements
            static_params: Static parameters
            dynamic_params: Bounds for optimization
            ref_x: Reference X values
            ref_y: Reference Y values (already scaled by W)
            
        Returns:
            SolverResult with current optimization result
        """
        # Define objective function to minimize
        def objective(params):
            k, l = params
            
            # Calculate current X and Y based on k and L
            # Normalize flow rate by number of fractures
            q_per_fracture = flow_rate_data / static_params.N
            
            # Calculate pressure drop (assuming initial pressure is the maximum)
            initial_pressure = np.max(pressure_data)
            delta_p = initial_pressure - pressure_data
            
            # Compute dimensionless X and Y
            calc_x = compute_x(k, static_params.h, delta_p, static_params.mu, 
                              static_params.Bo, q_per_fracture)
            calc_y = compute_y(q_per_fracture, static_params.Bo, time_data, 
                              static_params.phi, static_params.Ct, static_params.h, 
                              delta_p, l)
            
            # Calculate error between calculated and reference curves
            # Use L2 error as default (can be changed based on requirements)
            error = l2_error(ref_x, ref_y, calc_y[:len(ref_y)])  # Trim to match lengths
            
            return error
        
        # Initial guess for k and L (middle of the range)
        initial_k = (dynamic_params.k_min + dynamic_params.k_max) / 2
        initial_L = (dynamic_params.L_min + dynamic_params.L_max) / 2
        
        # Define bounds for k and L
        bounds = [(dynamic_params.k_min, dynamic_params.k_max),
                  (dynamic_params.L_min, dynamic_params.L_max)]
        
        # Run optimization using L-BFGS-B method
        result = minimize(objective, [initial_k, initial_L], 
                         method='L-BFGS-B', bounds=bounds)
        
        if not result.success:
            # Return a result with high error if optimization failed
            return SolverResult(
                S_opt=s,
                k_opt=initial_k,
                L_opt=initial_L,
                error_value=float('inf'),
                W_scale_factor=1.0
            )
        
        # Extract optimized parameters
        k_opt, L_opt = result.x
        error_value = result.fun
        
        # Create and return SolverResult
        return SolverResult(
            S_opt=s,
            k_opt=k_opt,
            L_opt=L_opt,
            error_value=error_value,
            W_scale_factor=1.0  # Placeholder, actual value would come from scaling
        )
