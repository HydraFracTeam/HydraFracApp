import numpy as np
from typing import Tuple, List, Optional
import logging

from .solver_new import ReservoirSolver
from core.reference_repo import ReferenceRepository

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
    ):
        self.S_opt = S_opt
        self.k_opt = k_opt
        self.L_opt = L_opt
        self.aL_opt = aL_opt          # добавлен — результат подбора
        self.N_opt = N_opt
        self.error_value = error_value
        self.W_scale_factor = W_scale_factor

    def __repr__(self):
        return (
            f"SolverResult(S={self.S_opt:.4f}, k={self.k_opt:.6f}, "
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
        W_fixed: float,                          # длина скважины — обязателен
        k_bounds: Tuple[float, float] = (1e-5, 10),
        L_bounds: Tuple[float, float] = (1e-3, 100),
        N_fixed: Optional[int] = None,           # None → подбирается
        h_known: Optional[float] = None,         # ориентировочная толщина пласта
        beam_width: int = 3,
    ) -> SolverResult:
        """
        Основной метод. Принимает безразмерные X-Y, возвращает SolverResult.

        Args:
            x_fact    : безразмерные X фактической кривой
            y_fact    : безразмерные Y фактической кривой
            W_fixed   : длина скважины (жёсткий фильтр библиотеки)
            k_bounds  : допустимый диапазон k для clip результата
            L_bounds  : допустимый диапазон L для clip результата
            N_fixed   : число трещин (None = подбирается на шаге 2)
            h_known   : толщина пласта (мягкий приоритет, ±50%)
            beam_width: ширина beam search на шагах 1-3
        """
        self._ensure_library_loaded()

        logger.info(f"solve_from_dimensionless: {len(x_fact)} точек, "
                    f"W={W_fixed}, N={N_fixed}, h={h_known}")
        logger.info(f"  X=[{np.min(x_fact):.4f}, {np.max(x_fact):.4f}], "
                    f"Y=[{np.min(y_fact):.4f}, {np.max(y_fact):.4f}]")

        # Сброс кэша перед новым решением
        self._reservoir_solver._x_grid = None
        self._reservoir_solver._y_fact = None

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

        # Извлекаем параметры — это параметры найденной кривой, не регрессия
        skin_opt  = result["skin"]
        N_opt     = result["N"]
        L_opt     = float(np.clip(result["L"], L_bounds[0], L_bounds[1]))
        aL_opt    = result["aL"]
        k_opt     = float(np.clip(result["params"]["k"], k_bounds[0], k_bounds[1]))
        error_val = result["misfit"]

        logger.info(
            f"Результат: S={skin_opt:.4f}, k={k_opt:.6f}, "
            f"L={L_opt:.4f}, a/L={aL_opt:.4f}, N={N_opt}, "
            f"error={error_val:.6f}"
        )

        return SolverResult(
            S_opt=float(skin_opt),
            k_opt=k_opt,
            L_opt=L_opt,
            aL_opt=float(aL_opt),
            N_opt=float(N_opt) if N_opt is not None else None,
            error_value=float(error_val),
            W_scale_factor=1.0,
        )

    def get_available_skins(self) -> List[float]:
        self._ensure_library_loaded()
        return self.reference_repo.get_available_skins()
