from pathlib import Path

import pytest

from utils.cache_benchmarks import (
    benchmark_pipeline_case,
    benchmark_repository_queries,
    benchmark_solver_sample_misfit,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
GOOD_CSV = ROOT_DIR / "data_files" / "user_input.csv"
PROBLEM_CSV = ROOT_DIR / "data_files" / "user_input_empty.csv"


@pytest.mark.performance
def test_repository_warm_cache_has_meaningful_speedup(tmp_path: Path, record_property):
    metric = benchmark_repository_queries(tmp_path)
    record_property("cold_seconds", metric.cold_seconds)
    record_property("warm_seconds", metric.warm_seconds)
    record_property("speedup", metric.speedup)
    assert metric.speedup >= 5.0


@pytest.mark.performance
def test_solver_sample_misfit_warm_cache_has_meaningful_speedup(tmp_path: Path, record_property):
    metric = benchmark_solver_sample_misfit(tmp_path)
    record_property("cold_seconds", metric.cold_seconds)
    record_property("warm_seconds", metric.warm_seconds)
    record_property("speedup", metric.speedup)
    assert metric.speedup >= 20.0


@pytest.mark.performance
@pytest.mark.parametrize("file_path", [GOOD_CSV, PROBLEM_CSV])
def test_pipeline_benchmark_reports_stable_shape(file_path: Path, record_property):
    metric = benchmark_pipeline_case(file_path)
    record_property("seconds_per_run", metric.seconds_per_run)
    record_property("rows", metric.rows)
    record_property("nan_count_p", metric.nan_count_p)
    record_property("nan_count_dp", metric.nan_count_dp)
    record_property("nan_count_x", metric.nan_count_x)
    record_property("nan_count_y", metric.nan_count_y)

    assert metric.seconds_per_run > 0
    assert metric.rows >= 20
    assert metric.nan_count_dp >= metric.nan_count_p
    assert metric.nan_count_x >= metric.nan_count_dp
    assert metric.nan_count_y >= metric.nan_count_dp
