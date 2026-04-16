#sessions/load_state.py

import json
import zipfile
import tempfile
from pathlib import Path
import tarfile
import zstandard as zstd

import pyarrow.parquet as pq

from core.app_state import AppState
from core.models import (
    RawDynamicData,
    ProcessingDynamicData,
    SolverState,
)
from schemas import StaticParams, OptimizeThresholds


def _to_numpy(series):
    return None if series is None else series.to_numpy()

def load_state(path: str) -> AppState:
    path = Path(path)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # zstd -> tar
        dctx = zstd.ZstdDecompressor()

        tar_path = tmp / "data.tar"
        with open(path, "rb") as f_in, open(tar_path, "wb") as f_out:
            f_out.write(dctx.decompress(f_in.read()))

        # tar -> files
        with tarfile.open(tar_path, "r") as tar:
            tar.extractall(tmp)

        meta = json.loads((tmp / "meta.json").read_text())

        state = AppState()


        # RAW
        raw_path = tmp / "raw.parquet"
        if raw_path.exists():
            df = pq.read_table(raw_path).to_pandas()

            m = meta["raw"]

            state.raw_dynamic_data = RawDynamicData(
                t=df["t"].to_numpy(),
                P=df["P"].to_numpy(),
                Q=df["Q"].to_numpy(),
                is_Q_in_dynamic_input=m["is_Q_in_dynamic_input"],
            )

        # PROCESSING
        proc_path = tmp / "processing.parquet"
        if proc_path.exists():
            df = pq.read_table(proc_path).to_pandas()

            m = meta["processing"]

            state.processing_dynamic_data = ProcessingDynamicData(
                t=df["t"].to_numpy(),
                P=df["P"].to_numpy(),
                Q=df["Q"].to_numpy(),

                P_interpolated_mask=_to_numpy(df["P_interpolated_mask"]),
                Q_interpolated_mask=_to_numpy(df["Q_interpolated_mask"]),

                P_extrapolated_mask=_to_numpy(df["P_extrapolated_mask"]),
                Q_extrapolated_mask=_to_numpy(df["Q_extrapolated_mask"]),
                t_extrapolated_mask=_to_numpy(df["t_extrapolated_mask"]),

                is_P_interpolated=m["is_P_interpolated"],
                is_Q_interpolated=m["is_Q_interpolated"],
                is_P_extrapolated=m["is_P_extrapolated"],
                is_Q_extrapolated=m["is_Q_extrapolated"],
                is_t_extrapolated=m["is_t_extrapolated"],
                is_Q_normalized=m["is_Q_normalized"],
            )

        # STATIC
        if "static" in meta:
            state.static_params = StaticParams(**meta["static"])

        # THRESHOLDS
        if "thresholds" in meta:
            state.optimize_thresholds = OptimizeThresholds(**meta["thresholds"])

        # SOLVER
        if "solver" in meta:
            s = meta["solver"]

            state.solver_state = SolverState(
                k_current=s["k"],
                L_current=s["L"],
                skin_current=s["skin"],
                residual=s["residual"],
            )

        return state
