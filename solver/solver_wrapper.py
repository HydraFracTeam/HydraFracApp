# solver/solver_wrapper.py
import numpy as np
from typing import Tuple, List, Optional
import logging

from .solver_new import ReservoirSolver
from core.reference_repo import ReferenceRepository
from core.models import ReferenceCurves

logger = logging.getLogger(__name__)


class SolverResult:
    """Результат оптимизации."""

    def __init__(
        self,
        S_opt: float,
        k_opt: float,
        L_opt: float,
        aL_opt: float,
        N_opt: Optional[float],
        error_value: float,
        W_scale_factor: float = 1.0,
        reference_curves: Optional[ReferenceCurves] = None,
    ):
        self.S_opt = S_opt
        self.k_opt = k_opt
        self.L_opt = L_opt
        self.aL_opt = aL_opt          # добавлен — результат подбора
        self.N_opt = N_opt
        self.error_value = error_value
        self.W_scale_factor = W_scale_factor
        self.reference_curves = reference_curves

    def __repr__(self):
        k_str = f"{self.k_opt:.6f}" if self.k_opt is not None else "N/A"
        return (
            f"SolverResult(S={self.S_opt:.4f}, k={k_str}, "
            f"L={self.L_opt:.4f}, a/L={self.aL_opt:.4f}, "
            f"N={self.N_opt}, error={self.error_value:.6f})"
        )


class Solver:
    """
    Обёртка над ReservoirSolver.

    Ступенчатый алгоритм подбора параметров трещины по совпадению
    формы кривой dY/dX (безразмерные X-Y):

      Шаг 0: фильтрация библиотеки по W + N (если задан)
      Шаг 1: select_skin   — beam search по форме, h-взвешивание
      Шаг 2: select_N      — если N не задан
      Шаг 3: select_aL     — перебор a/L при зафиксированных Skin, N
      Шаг 4: select_L      — перебор L + интерполяция между соседями
      Шаг 5: recover_k     — аналитически из уровня Y
    """

    def __init__(self, db_path: str = None):
        self.reference_repo = ReferenceRepository(db_path)
        self._reservoir_solver: Optional[ReservoirSolver] = None

    def _ensure_library_loaded(self):
        if self._reservoir_solver is None:
            skin_library = self.reference_repo.get_skin_library()
            if not skin_library:
                raise ValueError("Библиотека референсных кривых пуста")
            self._reservoir_solver = ReservoirSolver(skin_library)

    def solve_from_dimensionless(
        self,
        x_fact: np.ndarray,
        y_fact: np.ndarray,
        W_fixed: float,
        k_bounds: Tuple[float, float] = (1e-5, 10),
        L_bounds: Tuple[float, float] = (1e-3, 100),
        N_fixed: Optional[int] = None,
        h_known: Optional[float] = None,
        beam_width: int = 5,
    ) -> SolverResult:
        """
        Подбор параметров трещины по совпадению формы кривой dY/dX.

        Параметры результата (Skin, N, L, a/L) берутся напрямую из
        найденной кривой библиотеки — так же как Skin подбирается
        по форме, так и остальные из совпадения.

        k пока не восстанавливается (result.k_opt = None).
        """
        self._ensure_library_loaded()

        logger.info(f"solve_from_dimensionless: {len(x_fact)} точек, "
                    f"W={W_fixed}, N={N_fixed}, h={h_known}")
        logger.info(f"  X=[{np.min(x_fact):.4f}, {np.max(x_fact):.4f}], "
                    f"Y=[{np.min(y_fact):.4f}, {np.max(y_fact):.4f}]")

        # Сброс кэша перед новым решением
        self._reservoir_solver._x_grid = None
        self._reservoir_solver._y_fact = None
        self._reservoir_solver._x_fact_raw = None
        self._reservoir_solver._y_fact_raw = None
        self._reservoir_solver._alpha_fact = None  # сброс предпосчитанной производной

        result = self._reservoir_solver.solve(
            x_fact=np.asarray(x_fact, dtype=float),
            y_fact=np.asarray(y_fact, dtype=float),
            W_fixed=W_fixed,
            N_fixed=N_fixed,
            h_known=h_known,
            k_bounds=k_bounds,
            xf_bounds=L_bounds,
            beam=beam_width,
        )

        # L из найденной кривой библиотеки, clipped по bounds
        L_opt = float(np.clip(result["L"], L_bounds[0], L_bounds[1]))

        # k пока не восстанавливается — используем значение по умолчанию 5.0
        k_raw = result["params"].get("k")
        if k_raw is not None:
            k_opt = float(np.clip(k_raw, k_bounds[0], k_bounds[1]))
        else:
            k_opt = 5.0  # Значение по умолчанию пока подбор не производится

        error_val = result["misfit"]

        logger.info(
            f"Результат: S={result['skin']:.4f}, k={k_opt}, "
            f"L={L_opt:.4f}, a/L={result['aL']:.4f}, "
            f"N={result['N']}, error={result['misfit']:.6f}"
        )

        return SolverResult(
            S_opt=float(result["skin"]),
            k_opt=k_opt,
            L_opt=L_opt,
            aL_opt=float(result["aL"]),
            N_opt=float(result["N"]) if result["N"] is not None else None,
            error_value=float(error_val),
            W_scale_factor=1.0,
        )
    
    def solve_top5(
        self,
        x_fact,
        y_fact,
        W_fixed,
        k_bounds,
        L_bounds,
        N_fixed,
        h_known
    ) -> List[SolverResult]:

        self._ensure_library_loaded()

        raw = self._reservoir_solver.solve_top_candidates(
            x_fact=x_fact,
            y_fact=y_fact,
            W_fixed=W_fixed,
            k_bounds=k_bounds,
            xf_bounds=L_bounds,
            N_fixed=N_fixed,
            h_known=h_known,
            beam=5
        )

        out=[]

        for r in raw:

            out.append(
                SolverResult(
                    S_opt=r["skin"],
                    k_opt=r["k"],
                    L_opt=r["L"],
                    aL_opt=r["aL"],
                    N_opt=r["N"],
                    error_value=r["misfit"]
                )
            )

        return out
