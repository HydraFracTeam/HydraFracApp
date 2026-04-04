import json
import zipfile
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from core.app_state import AppState
from core.models import (
    RawDynamicData,
    ProcessingDynamicData,
    SolverState,
)
from schemas import StaticParams, OptimizeThresholds


VERSION = 1


# =========================
# SAVE
# =========================

def save_state(state: AppState, path: str) -> None:
    path = Path(path)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # --- RAW ---
        if state.raw_dynamic_data:
            raw = state.raw_dynamic_data
            df_raw = pd.DataFrame({
                "t": raw.t,
                "P": raw.P,
                "Q": raw.Q,
            })

            pq.write_table(
                pa.Table.from_pandas(df_raw),
                tmp / "raw.parquet",
                compression="zstd"
            )

            raw_meta = {
                "is_Q_in_dynamic_input": raw.is_Q_in_dynamic_input
            }
        else:
            raw_meta = None

        # --- PROCESSING ---
        if state.processing_dynamic_data:
            p = state.processing_dynamic_data

            df_proc = pd.DataFrame({
                "t": p.t,
                "P": p.P,
                "Q": p.Q,
                "dP": p.dP,
                "burde": _safe_array(p.burde),

                "P_interp_mask": _safe_array(p.P_interpolated_mask),
                "Q_interp_mask": _safe_array(p.Q_interpolated_mask),

                "P_extrap_mask": _safe_array(p.P_extrapolated_mask),
                "Q_extrap_mask": _safe_array(p.Q_extrapolated_mask),
                "t_extrap_mask": _safe_array(p.t_extrapolated_mask),
            })

            pq.write_table(
                pa.Table.from_pandas(df_proc),
                tmp / "processing.parquet",
                compression="zstd"
            )

            proc_meta = {
                "is_P_interpolated": p.is_P_interpolated,
                "is_Q_interpolated": p.is_Q_interpolated,
                "is_P_extrapolated": p.is_P_extrapolated,
                "is_Q_extrapolated": p.is_Q_extrapolated,
                "is_t_extrapolated": p.is_t_extrapolated,
                "is_Q_normalized": p.is_Q_normalized,
            }
        else:
            proc_meta = None

        # --- META ---
        meta = {
            "version": VERSION,
            "raw_meta": raw_meta,
            "processing_meta": proc_meta,
            "static_params": state.static_params.model_dump() if state.static_params else None,
            "thresholds": state.optimize_thresholds.model_dump() if state.optimize_thresholds else None,
        }

        (tmp / "meta.json").write_text(json.dumps(meta))

        # --- SOLVER ---
        if state.solver_state:
            solver = {
                "k": state.solver_state.k_current,
                "L": state.solver_state.L_current,
                "skin": state.solver_state.skin_current,
                "residual": state.solver_state.residual,
            }
            (tmp / "solver.json").write_text(json.dumps(solver))

        # --- ZIP ---
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for file in tmp.iterdir():
                z.write(file, arcname=file.name)


# =========================
# LOAD
# =========================

def load_state(path: str) -> AppState:
    path = Path(path)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        with zipfile.ZipFile(path, "r") as z:
            z.extractall(tmp)

        # --- META ---
        meta = json.loads((tmp / "meta.json").read_text())

        if meta["version"] != VERSION:
            raise ValueError("Unsupported session version")

        state = AppState()

        # --- RAW ---
        raw_path = tmp / "raw.parquet"
        if raw_path.exists():
            df = pq.read_table(raw_path).to_pandas()

            raw_meta = meta.get("raw_meta") or {}

            state.raw_dynamic_data = RawDynamicData(
                t=df["t"].to_numpy(),
                P=df["P"].to_numpy(),
                Q=df["Q"].to_numpy(),
                is_Q_in_dynamic_input=raw_meta.get("is_Q_in_dynamic_input", True),
            )

        # --- PROCESSING ---
        proc_path = tmp / "processing.parquet"
        if proc_path.exists():
            df = pq.read_table(proc_path).to_pandas()

            proc_meta = meta.get("processing_meta") or {}

            state.processing_dynamic_data = ProcessingDynamicData(
                t=df["t"].to_numpy(),
                P=df["P"].to_numpy(),
                Q=df["Q"].to_numpy(),
                dP=df["dP"].to_numpy(),

                burde=_restore_optional(df.get("burde")),

                P_interpolated_mask=_restore_optional(df.get("P_interp_mask")),
                Q_interpolated_mask=_restore_optional(df.get("Q_interp_mask")),

                P_extrapolated_mask=_restore_optional(df.get("P_extrap_mask")),
                Q_extrapolated_mask=_restore_optional(df.get("Q_extrap_mask")),
                t_extrapolated_mask=_restore_optional(df.get("t_extrap_mask")),

                is_P_interpolated=proc_meta.get("is_P_interpolated", False),
                is_Q_interpolated=proc_meta.get("is_Q_interpolated", False),
                is_P_extrapolated=proc_meta.get("is_P_extrapolated", False),
                is_Q_extrapolated=proc_meta.get("is_Q_extrapolated", False),
                is_t_extrapolated=proc_meta.get("is_t_extrapolated", False),
                is_Q_normalized=proc_meta.get("is_Q_normalized", False),
            )

        # --- STATIC ---
        if meta.get("static_params"):
            state.static_params = StaticParams(**meta["static_params"])

        # --- THRESHOLDS ---
        if meta.get("thresholds"):
            state.optimize_thresholds = OptimizeThresholds(**meta["thresholds"])

        # --- SOLVER ---
        solver_path = tmp / "solver.json"
        if solver_path.exists():
            s = json.loads(solver_path.read_text())

            state.solver_state = SolverState(
                k_current=s["k"],
                L_current=s["L"],
                skin_current=s["skin"],
                residual=s["residual"],
            )

        return state


# =========================
# HELPERS
# =========================

def _safe_array(arr: Optional[np.ndarray]):
    if arr is None:
        return None
    return arr


def _restore_optional(series):
    if series is None:
        return None
    values = series.to_numpy()
    if np.all(pd.isna(values)):
        return None
    return values
