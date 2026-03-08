from dataclasses import dataclass
from typing import Optional

from core.models import (
    RawDynamicData,
    ReferenceCurve,
    SolverState,
    UserDataset,
)


@dataclass
class AppState:
    """
    Central application state container.
    Stores all runtime data used by UI and solver.
    """

    raw_dynamic: Optional[RawDynamicData] = None

    fact_data: Optional[UserDataset] = None
    
    reference_curve: Optional[ReferenceCurve] = None

    solver_state: Optional[SolverState] = None

