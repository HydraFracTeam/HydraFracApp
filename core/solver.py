"""
Solver module for HydraFracApp.
Implements the optimization algorithm for determining S (skin), k (permeability), and L (fracture length).
Uses a hybrid approach with beam search for discrete parameters and Bayesian optimization for continuous.
"""

import numpy as np
from typing import Tuple, List, Optional, Dict
import logging

# Import from new solver module
from solver import ReservoirSolver
from solver.library import build_skin_library
from core.reference_repo import ReferenceRepository

logger = logging.getLogger(__name__)


class SolverResult:
    """Result of the optimization process."""
    
    def __init__(
        self,
        S_opt: float,
        k_opt: float,
        L_opt: float,
        error_value: float,
        N_opt: Optional[float] = None,
        W_scale_factor: float = 1.0
    ):
        self.S_opt = S_opt
        self.k_opt = k_opt
        self.L_opt = L_opt
        self.error_value = error_value
        self.N_opt = N_opt
        self.W_scale_factor = W_scale_factor
    
    def __repr__(self):
        return (f"SolverResult(S={self.S_opt:.4f}, k={self.k_opt:.6f}, "
                f"L={self.L_opt:.4f}, error={self.error_value:.6f})")


class Solver:
    """
    Main solver class implementing the optimization approach:
    - Step 1: Select best skin using beam search
    - Step 2: Select best N (number of fractures) from candidates
    - Step 3: Optimize k and L using Bayesian optimization
    """
    
    def __init__(self, db_path: str = None):
        """Initialize the solver with reference repository."""
        self.logger = logging.getLogger(__name__)
        self.reference_repo = ReferenceRepository(db_path)
        self._reservoir_solver: Optional[ReservoirSolver] = None
        
    def _ensure_library_loaded(self):
        """Lazy load the skin library."""
        if self._reservoir_solver is None:
            skin_library = self.reference_repo.get_skin_library()
            if not skin_library:
                raise ValueError("No reference curves available in database")
            self._reservoir_solver = ReservoirSolver(skin_library)
    
    def run(
        self,
        pressure_data: np.ndarray,
        time_data: np.ndarray,
        flow_rate_data: np.ndarray,
        static_params,
        dynamic_params,
        reference_repo=None,  # Kept for compatibility, not used
        skin_grid: List[float] = None
    ) -> SolverResult:
        """
        Execute the main optimization routine.
        
        Args:
            pressure_data: Array of pressure measurements (not used directly, X/Y are used)
            time_data: Array of time measurements (not used directly)
            flow_rate_data: Array of flow rate measurements (not used directly)
            static_params: Static reservoir and well parameters (schemas.StaticParams)
            dynamic_params: Optimization bounds for k and L (schemas.OptimizeThresholds)
            reference_repo: Kept for compatibility, ignored
            skin_grid: Grid of skin factor values to test (not used in new solver)
            
        Returns:
            SolverResult: Contains optimized parameters and metrics
        """
        self._ensure_library_loaded()
        
        # Build X, Y from dimensionless data (expected to be precomputed)
        # For now, we expect fact_data to have dimensionless data available
        # This should be computed by preprocessing before calling solver
        
        # The new solver works with X, Y arrays directly
        # We need to get them from the app state (fact_data.dimensionless)
        # For compatibility, we'll compute them here if not provided
        
        raise NotImplementedError(
            "Use solve_from_dimensionless() method with pre-computed X, Y arrays. "
            "The run() method is kept for backward compatibility only."
        )
    
    def solve_from_dimensionless(
        self,
        x_fact: np.ndarray,
        y_fact: np.ndarray,
        k_bounds: Tuple[float, float] = (1e-5, 10),
        L_bounds: Tuple[float, float] = (1e-3, 100),
        beam_width: int = 3,
        N_fixed: int = None
    ) -> SolverResult:
        """
        Main entry point for solving with dimensionless X-Y data.
        
        Args:
            x_fact: Dimensionless X array from field data
            y_fact: Dimensionless Y array from field data
            k_bounds: Bounds for permeability optimization (k_min, k_max)
            L_bounds: Bounds for fracture length optimization (L_min, L_max)
            beam_width: Number of top candidates to keep in beam search
            N_fixed: Fixed number of fractures. If None - will be selected automatically.
            
        Returns:
            SolverResult with optimized S, k, L
        """
        self._ensure_library_loaded()
        
        self.logger.info(f"Starting optimization with {len(x_fact)} data points")
        self.logger.info(f"Bounds: k in [{k_bounds[0]:.6f}, {k_bounds[1]:.6f}], L in [{L_bounds[0]:.4f}, {L_bounds[1]:.4f}]")
        if N_fixed is not None:
            self.logger.info(f"Fixed N (number of fractures): {N_fixed}")
        
        # Масштабирование не требуется - X-Y уже безразмерные
        # Интерполяция на сетку референсных кривых происходит в solver
        
        self.logger.info(f"Input X range: [{np.min(x_fact):.4f}, {np.max(x_fact):.4f}]")
        self.logger.info(f"Input Y range: [{np.min(y_fact):.4f}, {np.max(y_fact):.4f}]")
        
        # Use the new reservoir solver with bounds
        result = self._reservoir_solver.solve(
            x_fact, y_fact,
            k_bounds=k_bounds,
            xf_bounds=L_bounds,
            N_fixed=N_fixed
        )
        
        # Очистка кэша после решения
        self._reservoir_solver._x_interp = None
        self._reservoir_solver._y_interp = None
        
        # The new solver returns: {skin, N, params: {k, xf}, misfit}
        # Extract and convert to our format
        skin_opt = result['skin']
        N_opt = result['N']
        params = result['params']
        
        # params is dict with 'k' and 'xf' keys from Bayesian optimization
        k_opt = params.get('k', params.get('xf', 1.0))  # Handle different key names
        L_opt = params.get('xf', params.get('k', 100.0))  # xf is fracture length
        
        # Ensure correct assignment based on bounds
        if k_opt > k_bounds[1] or k_opt < k_bounds[0]:
            k_opt = np.clip(k_opt, k_bounds[0], k_bounds[1])
        if L_opt > L_bounds[1] or L_opt < L_bounds[0]:
            L_opt = np.clip(L_opt, L_bounds[0], L_bounds[1])
        
        error_value = result['misfit']
        
        self.logger.info(
            f"Optimization complete: S={skin_opt:.4f}, k={k_opt:.6f}, "
            f"L={L_opt:.4f}, error={error_value:.6f}"
        )
        
        return SolverResult(
            S_opt=float(skin_opt),
            k_opt=float(k_opt),
            L_opt=float(L_opt),
            error_value=float(error_value),
            N_opt=float(N_opt),
            W_scale_factor=1.0
        )
    
    def get_available_skins(self) -> List[float]:
        """Get list of available skin values from reference database."""
        self._ensure_library_loaded()
        return self.reference_repo.get_available_skins()
