import json
import zipfile
import tempfile
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from core.app_state import AppState


def save_state(state: AppState, path: str) -> None:
    path = Path(path)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        meta = {}

        # RAW
        if state.raw_dynamic_data:
            raw = state.raw_dynamic_data

            df = pd.DataFrame({
                "t": raw.t,
                "P": raw.P,
                "Q": raw.Q,
            })

            pq.write_table(pa.Table.from_pandas(df), tmp / "raw.parquet")

            meta["raw"] = {
                "is_Q_in_dynamic_input": raw.is_Q_in_dynamic_input
            }

        # PROCESSING
        if state.processing_dynamic_data:
            p = state.processing_dynamic_data

            df = pd.DataFrame({
                "t": p.t,
                "P": p.P,
                "Q": p.Q,

                "P_interpolated_mask": p.P_interpolated_mask,
                "Q_interpolated_mask": p.Q_interpolated_mask,

                "P_extrapolated_mask": p.P_extrapolated_mask,
                "Q_extrapolated_mask": p.Q_extrapolated_mask,
                "t_extrapolated_mask": p.t_extrapolated_mask,
            })

            pq.write_table(pa.Table.from_pandas(df), tmp / "processing.parquet")

            meta["processing"] = {
                "is_P_interpolated": p.is_P_interpolated,
                "is_Q_interpolated": p.is_Q_interpolated,
                "is_P_extrapolated": p.is_P_extrapolated,
                "is_Q_extrapolated": p.is_Q_extrapolated,
                "is_t_extrapolated": p.is_t_extrapolated,
                "is_Q_normalized": p.is_Q_normalized,
            }

        # STATIC
        if state.static_params:
            meta["static"] = state.static_params.model_dump()

        # THRESHOLDS
        if state.optimize_thresholds:
            meta["thresholds"] = state.optimize_thresholds.model_dump()

        # SOLVER
        if state.solver_state:
            meta["solver"] = {
                "k": state.solver_state.k_current,
                "L": state.solver_state.L_current,
                "skin": state.solver_state.skin_current,
                "residual": state.solver_state.residual,
            }

        # META
        (tmp / "meta.json").write_text(json.dumps(meta))

        # ZIP
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for f in tmp.iterdir():
                z.write(f, arcname=f.name)
