from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import os
import sqlite3
import tempfile
import time
from typing import Callable

import numpy as np

from core.dimensionless import calculate_x, calculate_y
from core.reference_repo import ReferenceRepository
from processing.loaders.csv_loader import load_dynamic_data_from_csv
from processing.rebuild_processing_dynamic import rebuild_processing_dynamic
from schemas.static_params import StaticParams
from solver.solver_new import ReservoirSolver


@dataclass(frozen=True)
class BenchmarkMetric:
    cold_seconds: float
    warm_seconds: float

    @property
    def speedup(self) -> float:
        if self.warm_seconds <= 0:
            return float("inf")
        return self.cold_seconds / self.warm_seconds

    def to_dict(self) -> dict:
        data = asdict(self)
        data["speedup"] = self.speedup
        return data


@dataclass(frozen=True)
class PipelineMetric:
    seconds_per_run: float
    rows: int
    nan_count_p: int
    nan_count_dp: int
    nan_count_x: int
    nan_count_y: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkReport:
    repository_query: BenchmarkMetric
    solver_sample_misfit: BenchmarkMetric
    pipeline_good: PipelineMetric
    pipeline_bad: PipelineMetric

    def to_dict(self) -> dict:
        return {
            "repository_query": self.repository_query.to_dict(),
            "solver_sample_misfit": self.solver_sample_misfit.to_dict(),
            "pipeline_good": self.pipeline_good.to_dict(),
            "pipeline_bad": self.pipeline_bad.to_dict(),
        }


def build_static_params() -> StaticParams:
    return StaticParams(
        W=1350.0,
        h=10.0,
        mu=1.0,
        phi=0.2,
        B=1.0,
        ct=4e-5,
        N=10,
        P0=300.0,
    )


def median_seconds_per_call(fn: Callable[[], object], loops: int, rounds: int = 7) -> float:
    values = []
    for _ in range(rounds):
        started = time.perf_counter()
        for _ in range(loops):
            fn()
        values.append((time.perf_counter() - started) / loops)
    return float(np.median(values))


def build_synthetic_reference_db(directory: Path) -> Path:
    fd, raw_path = tempfile.mkstemp(suffix=".db", dir=directory)
    os.close(fd)
    db_path = Path(raw_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE statics (
            curve_id INTEGER PRIMARY KEY,
            Skin REAL,
            h REAL,
            N INTEGER,
            W REAL,
            L REAL,
            aL REAL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE dynamics (
            curve_id INTEGER,
            elemIdx INTEGER,
            X REAL,
            Y REAL
        )
        """
    )

    statics_rows = []
    dynamics_rows = []
    for curve_id in range(1, 61):
        skin = float(curve_id % 6)
        statics_rows.append((curve_id, skin, 10.0, 10, 1350.0, 20.0 + curve_id, 0.625))
        for elem_idx in range(1, 151):
            x_value = 0.5 + elem_idx * 0.1 + curve_id * 0.01
            y_value = 20.0 / (1.0 + elem_idx * 0.03 + curve_id * 0.001)
            dynamics_rows.append((curve_id, elem_idx, x_value, y_value))

    cursor.executemany(
        "INSERT INTO statics (curve_id, Skin, h, N, W, L, aL) VALUES (?, ?, ?, ?, ?, ?, ?)",
        statics_rows,
    )
    cursor.executemany(
        "INSERT INTO dynamics (curve_id, elemIdx, X, Y) VALUES (?, ?, ?, ?)",
        dynamics_rows,
    )
    conn.commit()
    conn.close()
    return db_path


def benchmark_pipeline_case(file_path: Path, loops: int = 20, rounds: int = 7) -> PipelineMetric:
    static = build_static_params()
    baseline = {}

    def run_once():
        raw = load_dynamic_data_from_csv(str(file_path))
        processing = rebuild_processing_dynamic(
            raw_data=raw,
            static_data=static,
            current_processing_data=None,
        )
        x_values = calculate_x(
            k=5.0,
            h=static.h,
            delta_p=processing.dP,
            mu=static.mu,
            B=static.B,
            Q=processing.Q,
        )
        y_values = calculate_y(
            Q=processing.Q,
            B=static.B,
            t=processing.t,
            phi=static.phi,
            ct=static.ct,
            h=static.h,
            delta_p=processing.dP,
            L=32.0,
        )
        baseline["rows"] = len(processing.t)
        baseline["nan_count_p"] = int(np.isnan(raw.P).sum())
        baseline["nan_count_dp"] = int(np.isnan(processing.dP).sum())
        baseline["nan_count_x"] = int(np.isnan(x_values).sum())
        baseline["nan_count_y"] = int(np.isnan(y_values).sum())
        return float(np.nanmean(x_values) + np.nanmean(y_values))

    seconds_per_run = median_seconds_per_call(run_once, loops=loops, rounds=rounds)
    return PipelineMetric(seconds_per_run=seconds_per_run, **baseline)


def benchmark_repository_queries(directory: Path) -> BenchmarkMetric:
    db_path = build_synthetic_reference_db(directory)
    repo = ReferenceRepository(str(db_path))

    def cold_query():
        repo._cached_available_skins.cache_clear()
        repo._cached_available_N_values.cache_clear()
        repo._cached_curve_ids_by_skin.cache_clear()
        repo._cached_reference_curve.cache_clear()
        skins = repo.get_available_skins()
        curve_ids = repo.get_curves_by_skin(skins[0])
        repo.get_reference_curve(curve_ids[0])

    def warm_query():
        skins = repo.get_available_skins()
        curve_ids = repo.get_curves_by_skin(skins[0])
        repo.get_reference_curve(curve_ids[0])

    cold_seconds = median_seconds_per_call(cold_query, loops=40, rounds=5)
    warm_query()
    warm_seconds = median_seconds_per_call(warm_query, loops=400, rounds=5)

    repo._close_connection()
    db_path.unlink(missing_ok=True)
    return BenchmarkMetric(cold_seconds=cold_seconds, warm_seconds=warm_seconds)


def benchmark_solver_sample_misfit(directory: Path) -> BenchmarkMetric:
    db_path = build_synthetic_reference_db(directory)
    repo = ReferenceRepository(str(db_path))
    solver = ReservoirSolver(repo.get_skin_library())
    sample_group = next(iter(solver.skin_library.values()))
    sample = sample_group[0]

    solver._prepare(sample["x"], sample["y"])

    def cold_call():
        solver._sample_misfit_cache.clear()
        solver._sample_misfit(sample)

    def warm_call():
        solver._sample_misfit(sample)

    cold_seconds = median_seconds_per_call(cold_call, loops=50, rounds=5)
    solver._sample_misfit_cache.clear()
    solver._sample_misfit(sample)
    warm_seconds = median_seconds_per_call(warm_call, loops=2000, rounds=5)

    repo._close_connection()
    db_path.unlink(missing_ok=True)
    return BenchmarkMetric(cold_seconds=cold_seconds, warm_seconds=warm_seconds)


def collect_cache_benchmark_report(repo_root: Path) -> BenchmarkReport:
    repo_root = repo_root.resolve()
    temp_dir = repo_root / ".pytest_cache"
    temp_dir.mkdir(exist_ok=True)

    good_file = repo_root / "data_files" / "user_input.csv"
    bad_file = repo_root / "data_files" / "user_input_empty.csv"

    return BenchmarkReport(
        repository_query=benchmark_repository_queries(temp_dir),
        solver_sample_misfit=benchmark_solver_sample_misfit(temp_dir),
        pipeline_good=benchmark_pipeline_case(good_file),
        pipeline_bad=benchmark_pipeline_case(bad_file),
    )
