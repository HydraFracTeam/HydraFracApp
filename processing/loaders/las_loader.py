import numpy as np
import lasio
from pydantic import ValidationError

from schemas.raw_dynamic_input import RawDynamicDataInput
from core.models import RawDynamicData
from utils import format_pydantic_error


def load_dynamic_data_from_las(file_path: str) -> RawDynamicData:
    """
    Load dynamic well test data from LAS file.
    Expected curves:
        T  - time
        P  - pressure
        Q  - flow rate (optional)
    """

    las = lasio.read(file_path)
    
    curves = {c.mnemonic.lower(): c.mnemonic for c in las.curves}

    if "t" not in curves or "p" not in curves:
        raise ValueError("LAS файл должен содержать кривые T и P")

    t = las[curves["t"]].tolist()
    P = las[curves["p"]].tolist()

    Q = None
    if "q" in curves:
        Q = las[curves["q"]].tolist()

    try:
        validated = RawDynamicDataInput(
            t=t,
            P=P,
            Q=Q
        )

    except ValidationError as e:
        raise ValueError(format_pydantic_error(e))

    return RawDynamicData(
        t=np.asarray(validated.t, dtype=float),
        P=np.asarray(validated.P, dtype=float),
        Q=np.asarray(validated.Q, dtype=float) if validated.Q else None,
        is_Q_in_dynamic_input=validated.Q is not None,
        source_file=file_path
    )
