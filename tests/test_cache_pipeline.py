from pathlib import Path
import sqlite3

import numpy as np
import pytest

from core.dimensionless import calculate_x, calculate_y
from core.reference_repo import ReferenceRepository
from processing.loaders.csv_loader import load_dynamic_data_from_csv
from processing.rebuild_processing_dynamic import rebuild_processing_dynamic
from schemas.static_params import StaticParams
from solver.solver_new import ReservoirSolver


ROOT_DIR = Path(__file__).resolve().parents[1]
GOOD_CSV = ROOT_DIR / "data_files" / "user_input.csv"
PROBLEM_CSV = ROOT_DIR / "data_files" / "user_input_empty.csv"


def _static_params() -> StaticParams:
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


def _build_pipeline(file_path: Path):
    raw = load_dynamic_data_from_csv(str(file_path))
    static = _static_params()
    processing = rebuild_processing_dynamic(
        raw_data=raw,
        static_data=static,
        current_processing_data=None,
    )
    dimensionless_x = calculate_x(
        k=5.0,
        h=static.h,
        delta_p=processing.dP,
        mu=static.mu,
        B=static.B,
        Q=processing.Q,
    )
    dimensionless_y = calculate_y(
        Q=processing.Q,
        B=static.B,
        t=processing.t,
        phi=static.phi,
        ct=static.ct,
        h=static.h,
        delta_p=processing.dP,
        L=32.0,
    )
    return raw, processing, dimensionless_x, dimensionless_y


def _assert_arrays_equal(left: np.ndarray, right: np.ndarray) -> None:
    np.testing.assert_allclose(left, right, equal_nan=True)


@pytest.fixture
def reference_db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "reference_curves.db"
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

    statics_rows = [
        (1, 0.5, 10.0, 10, 1350.0, 32.0, 0.625),
        (2, 1.5, 10.0, 10, 1350.0, 40.0, 0.625),
    ]
    dynamics_rows = [
        (1, 1, 1.0, 10.0),
        (1, 2, 2.0, 8.0),
        (1, 3, 3.0, 6.0),
        (2, 1, 1.1, 9.0),
        (2, 2, 2.2, 7.0),
        (2, 3, 3.3, 5.0),
    ]

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


def test_good_csv_pipeline_is_repeatable_over_many_runs():
    baseline_raw, baseline_processing, baseline_x, baseline_y = _build_pipeline(GOOD_CSV)

    assert not np.isnan(baseline_raw.P).any()
    assert np.isfinite(baseline_x).all()
    assert np.isfinite(baseline_y).all()

    for _ in range(15):
        raw, processing, dimensionless_x, dimensionless_y = _build_pipeline(GOOD_CSV)
        _assert_arrays_equal(raw.t, baseline_raw.t)
        _assert_arrays_equal(raw.P, baseline_raw.P)
        _assert_arrays_equal(raw.Q, baseline_raw.Q)
        _assert_arrays_equal(processing.dP, baseline_processing.dP)
        _assert_arrays_equal(processing.burde, baseline_processing.burde)
        _assert_arrays_equal(dimensionless_x, baseline_x)
        _assert_arrays_equal(dimensionless_y, baseline_y)


def test_problem_csv_preserves_nan_signature_over_many_runs():
    baseline_raw, baseline_processing, baseline_x, baseline_y = _build_pipeline(PROBLEM_CSV)

    assert np.isnan(baseline_raw.P).any()
    assert np.isnan(baseline_processing.dP).any()
    assert np.isnan(baseline_x).any()
    assert np.isnan(baseline_y).any()

    baseline_pressure_mask = np.isnan(baseline_raw.P)
    baseline_dp_mask = np.isnan(baseline_processing.dP)
    baseline_x_mask = np.isnan(baseline_x)
    baseline_y_mask = np.isnan(baseline_y)

    for _ in range(15):
        raw, processing, dimensionless_x, dimensionless_y = _build_pipeline(PROBLEM_CSV)
        np.testing.assert_array_equal(np.isnan(raw.P), baseline_pressure_mask)
        np.testing.assert_array_equal(np.isnan(processing.dP), baseline_dp_mask)
        np.testing.assert_array_equal(np.isnan(dimensionless_x), baseline_x_mask)
        np.testing.assert_array_equal(np.isnan(dimensionless_y), baseline_y_mask)
        _assert_arrays_equal(processing.dP, baseline_processing.dP)
        _assert_arrays_equal(dimensionless_x, baseline_x)
        _assert_arrays_equal(dimensionless_y, baseline_y)


def test_reference_repository_lru_cache_hits_on_repeated_queries(reference_db_path: Path):
    repo = ReferenceRepository(str(reference_db_path))
    repo._cached_available_N_values.cache_clear()
    repo._cached_available_skins.cache_clear()
    repo._cached_curve_ids_by_skin.cache_clear()
    repo._cached_reference_curve.cache_clear()

    n_values_first = repo.get_available_N_values()
    n_values_second = repo.get_available_N_values()
    assert n_values_first == n_values_second
    assert repo._cached_available_N_values.cache_info().hits >= 1

    skins = repo.get_available_skins()
    assert skins
    curve_ids = repo.get_curves_by_skin(skins[0])
    assert curve_ids

    x1, y1 = repo.get_reference_curve(curve_ids[0])
    x2, y2 = repo.get_reference_curve(curve_ids[0])
    _assert_arrays_equal(x1, x2)
    _assert_arrays_equal(y1, y2)
    assert repo._cached_reference_curve.cache_info().hits >= 1

    repo._close_connection()


def test_solver_sample_misfit_cache_reuses_result_for_same_sample(reference_db_path: Path):
    repo = ReferenceRepository(str(reference_db_path))
    solver = ReservoirSolver(repo.get_skin_library())
    first_skin = next(iter(solver.skin_library.values()))
    sample = first_skin[0]

    solver._prepare(sample["x"], sample["y"])
    result_first = solver._sample_misfit(sample)
    cache_size_after_first = len(solver._sample_misfit_cache)
    result_second = solver._sample_misfit(sample)

    assert result_first == result_second
    assert cache_size_after_first == 1
    assert len(solver._sample_misfit_cache) == 1
