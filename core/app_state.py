from dataclasses import dataclass
from typing import Optional

from core.models import (
    RawDynamicData,
    DimensionlessData,
    SolverState,
    UserDataset
)


@dataclass
class AppState:
    """
    Central application state container.
    Stores all runtime data used by UI and solver.
    """

    raw_dynamic: Optional[RawDynamicData] = None

    dataset: Optional[UserDataset] = None

    dimensionless: Optional[DimensionlessData] = None

    solver_state: Optional[SolverState] = None

