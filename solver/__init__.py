# solver/__init__.py
from .solver_new import ReservoirSolver
from .solver_wrapper import Solver, SolverResult
from .vectorized_solver import (
    VectorizedReservoirSolver,
    VectorizedLibrary,
    build_vectorized_library,
)
__all__ = [
    "ReservoirSolver",
    "Solver",
    "SolverResult",
    "VectorizedReservoirSolver",
    "VectorizedLibrary",
    "build_vectorized_library",
]
