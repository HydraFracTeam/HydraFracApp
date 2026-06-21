# solver/solver_wrapper.py
import numpy as np
from typing import Tuple, List, Optional
import logging

from .solver_new import ReservoirSolver
from .vectorized_solver import (
    VectorizedReservoirSolver,
    build_vectorized_library,
    VectorizedLibrary,
)
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
    Обёртка над ReservoirSolver / VectorizedReservoirSolver.

    Поддерживает два режима работы:
      - ``use_vectorized=False`` (по умолчанию): оригинальный последовательный ReservoirSolver
      - ``use_vectorized=True``: векторизованный солвер с предвычисленной библиотекой

    Векторизованный режим значительно ускоряет шаги 1–3 (поиск Skin, N, a/L),
    так как невязка считается сразу для всех подходящих образцов библиотеки,
    без Python-циклов. Шаг 4 (L) и шаг 5 (k) остаются с тем же качеством
    что и в оригинале.
    """

    def __init__(self, db_path: str = None, use_vectorized: bool = False, overlap_percentage: float = 5.0):
        self.reference_repo = ReferenceRepository(db_path)
        self.use_vectorized = use_vectorized
        self.overlap_percentage = overlap_percentage
        self._reservoir_solver: Optional[ReservoirSolver] = None
        self._vectorized_lib: Optional[VectorizedLibrary] = None
        self._vectorized_solver: Optional[VectorizedReservoirSolver] = None

    def _ensure_library_loaded(self):
        overlap_threshold = self.overlap_percentage / 100.0
        if self.use_vectorized:
            if self._vectorized_lib is None:
                skin_library = self.reference_repo.get_skin_library()
                if not skin_library:
                    raise ValueError("Библиотека референсных кривых пуста")
                logger.info("Сборка векторизованной библиотеки…")
                self._vectorized_lib = build_vectorized_library(skin_library)
                self._vectorized_solver = VectorizedReservoirSolver(
                    self._vectorized_lib, overlap_threshold=overlap_threshold
                )
                logger.info("Векторизованная библиотека готова.")
        else:
            if self._reservoir_solver is None:
                skin_library = self.reference_repo.get_skin_library()
                if not skin_library:
                    raise ValueError("Библиотека референсных кривых пуста")
                self._reservoir_solver = ReservoirSolver(
                    skin_library, overlap_threshold=overlap_threshold
                )

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

        k не восстанавливается автоматически; используется значение по умолчанию
        или задаётся явно. Для восстановления k используйте recover_k_step.

        Args:
            x_fact: массив безразмерных X (фактические)
            y_fact: массив безразмерных Y (фактические)
            W_fixed: фиксированная ширина трещины (м) или 0/None для любого W
            k_bounds: (min, max) границы проницаемости, мД
            L_bounds: (min, max) границы полудлины трещины, м
            N_fixed: фиксированное количество трещин или None для автоматического подбора
            h_known: известная толщина пласта (м) для взвешивания по h или None
            beam_width: ширина beam-search (количество топ-кандидатов на каждом шаге)
        """
        self._ensure_library_loaded()

        x_fact = np.asarray(x_fact, dtype=float)
        y_fact = np.asarray(y_fact, dtype=float)

        logger.info(f"solve_from_dimensionless: {len(x_fact)} точек, "
                    f"W={W_fixed}, N={N_fixed}, h={h_known}")
        logger.info(f"  X=[{np.min(x_fact):.4f}, {np.max(x_fact):.4f}], "
                    f"Y=[{np.min(y_fact):.4f}, {np.max(y_fact):.4f}]")

        if self.use_vectorized:
            result = self._vectorized_solver.solve(
                x_fact=x_fact,
                y_fact=y_fact,
                W_fixed=W_fixed,
                N_fixed=N_fixed,
                h_known=h_known,
                k_bounds=k_bounds,
                xf_bounds=L_bounds,
                beam=beam_width,
            )
        else:
            # Сброс кэша перед новым решением
            self._reservoir_solver._x_grid = None
            self._reservoir_solver._y_fact = None
            self._reservoir_solver._x_fact_raw = None
            self._reservoir_solver._y_fact_raw = None
            self._reservoir_solver._alpha_fact = None

            result = self._reservoir_solver.solve(
                x_fact=x_fact,
                y_fact=y_fact,
                W_fixed=W_fixed,
                N_fixed=N_fixed,
                h_known=h_known,
                k_bounds=k_bounds,
                xf_bounds=L_bounds,
                beam=beam_width,
            )

        # L из найденной кривой библиотеки, clipped по bounds
        L_opt = float(np.clip(result["L"], L_bounds[0], L_bounds[1]))

        # k получается из recover_k на шаге 5, но пока используем значение по умолчанию
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

        W_scale_factor = result.get("W_scale_factor", 1.0)

        # For non-vectorized solver, compute W_scale_factor
        if W_scale_factor == 1.0 and W_fixed is not None and W_fixed > 0 and result.get("W"):
            W_scale_factor = result["W"] / W_fixed

        return SolverResult(
            S_opt=float(result["skin"]),
            k_opt=k_opt,
            L_opt=L_opt,
            aL_opt=float(result["aL"]),
            N_opt=float(result["N"]) if result["N"] is not None else None,
            error_value=float(error_val),
            W_scale_factor=W_scale_factor,
        )

    def solve_top5(
        self,
        x_fact,
        y_fact,
        W_fixed,
        k_bounds,
        L_bounds,
        N_fixed,
        h_known,
    ) -> List[SolverResult]:
        """
        Возвращает top-5 решений (использует тот же солвер что и solve_from_dimensionless).
        """
        self._ensure_library_loaded()

        if self.use_vectorized:
            raw = self._vectorized_solver.solve_top_candidates(
                x_fact=x_fact,
                y_fact=y_fact,
                W_fixed=W_fixed,
                k_bounds=k_bounds,
                xf_bounds=L_bounds,
                N_fixed=N_fixed,
                h_known=h_known,
                beam=5,
            )
        else:
            raw = self._reservoir_solver.solve_top_candidates(
                x_fact=x_fact,
                y_fact=y_fact,
                W_fixed=W_fixed,
                k_bounds=k_bounds,
                xf_bounds=L_bounds,
                N_fixed=N_fixed,
                h_known=h_known,
                beam=5,
            )

        out = []
        for r in raw:
            out.append(
                SolverResult(
                    S_opt=r["skin"],
                    k_opt=r["k"],
                    L_opt=r["L"],
                    aL_opt=r["aL"],
                    N_opt=r["N"],
                    error_value=r["misfit"],
                )
            )
        return out

    def set_vectorized(self, enabled: bool):
        """Переключает режим векторизованного солвера."""
        self.use_vectorized = enabled
        # Сброс кэша при переключении
        self._reservoir_solver = None
        self._vectorized_lib = None
        self._vectorized_solver = None
        logger.info(f"Режим солвера: {'векторизованный' if enabled else 'последовательный'}")
