#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from utils.cache_benchmarks import collect_cache_benchmark_report

    parser = argparse.ArgumentParser(
        description="Run cache and pipeline benchmarks for the current checkout."
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        help="Output format.",
    )
    args = parser.parse_args()

    report = collect_cache_benchmark_report(root)
    payload = report.to_dict()

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("# Cache Performance Report")
    print()
    print("| Metric | Cold / run, s | Warm / run, s | Speedup |")
    print("|---|---:|---:|---:|")
    print(
        f"| Repository query | {payload['repository_query']['cold_seconds']:.6f} | "
        f"{payload['repository_query']['warm_seconds']:.6f} | "
        f"{payload['repository_query']['speedup']:.2f}x |"
    )
    print(
        f"| Solver sample misfit | {payload['solver_sample_misfit']['cold_seconds']:.6f} | "
        f"{payload['solver_sample_misfit']['warm_seconds']:.6f} | "
        f"{payload['solver_sample_misfit']['speedup']:.2f}x |"
    )
    print()
    print("| Pipeline case | Seconds / run | Rows | NaN P | NaN dP | NaN X | NaN Y |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    print(
        f"| Good CSV | {payload['pipeline_good']['seconds_per_run']:.6f} | "
        f"{payload['pipeline_good']['rows']} | "
        f"{payload['pipeline_good']['nan_count_p']} | "
        f"{payload['pipeline_good']['nan_count_dp']} | "
        f"{payload['pipeline_good']['nan_count_x']} | "
        f"{payload['pipeline_good']['nan_count_y']} |"
    )
    print(
        f"| Problem CSV | {payload['pipeline_bad']['seconds_per_run']:.6f} | "
        f"{payload['pipeline_bad']['rows']} | "
        f"{payload['pipeline_bad']['nan_count_p']} | "
        f"{payload['pipeline_bad']['nan_count_dp']} | "
        f"{payload['pipeline_bad']['nan_count_x']} | "
        f"{payload['pipeline_bad']['nan_count_y']} |"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
