"""
tests/test_vectorized_solver.py

Сравнение векторизованного солвера против последовательного на синтетических кейсах.
Запускается отдельно, не зависит от pytest.
"""

import sys
import os
import numpy as np
import logging
import json

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solver.vectorized_solver import VectorizedReservoirSolver, build_vectorized_library
from core.reference_repo import ReferenceRepository
from core.dimensionless import calculate_x, calculate_y

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_test_cases(n_cases: int = 20, random_seed: int = 42) -> list:
    """Загружает случайные CSV-кейсы из dataset_cases."""
    import glob
    rng = np.random.default_rng(random_seed)
    case_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset_cases")
    all_files = sorted(glob.glob(os.path.join(case_dir, "*.csv")))
    if not all_files:
        logger.warning("dataset_cases не найден, используется синтетическая проверка")
        return _make_synthetic_cases(n_cases)

    selected = rng.choice(all_files, size=min(n_cases, len(all_files)), replace=False)
    cases = []
    for f in selected:
        try:
            data = np.genfromtxt(f, delimiter=",", skip_header=1)
            if data.ndim < 2 or data.shape[1] < 2:
                continue
            t = data[:, 0]
            P = data[:, 1]
            Q = data[:, 2] if data.shape[1] > 2 else None
            cases.append({"t": t, "P": P, "Q": Q, "file": os.path.basename(f)})
        except Exception as e:
            logger.warning(f"Не удалось прочитать {f}: {e}")
    return cases


def _make_synthetic_cases(n: int) -> list:
    """Создаёт синтетические кейсы вручную, если dataset_cases пуст."""
    rng = np.random.default_rng(0)
    cases = []
    for i in range(n):
        t = np.logspace(-2, 3, 150)  # 0.01 — 1000 мин
        # Псевдо-закон спада давления
        P0 = 300.0
        P = P0 - 200.0 * np.exp(-0.01 * t) + rng.normal(0, 5, len(t))
        Q = np.full(len(t), 150.0)
        cases.append({"t": t, "P": P, "Q": Q, "file": f"synthetic_{i:03d}.csv"})
    return cases


def run_comparison(n_cases: int = 20, db_path: str = None):
    """
    Запускает оба солвера на одних и тех же кейсах и сравнивает результаты.
    Возвращает сводный словарь с метриками.
    """
    if db_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, "storage", "db", "reference_curves.db")

    # Загружаем библиотеку один раз
    repo = ReferenceRepository(db_path)
    skin_library = repo.get_skin_library()
    if not skin_library:
        raise RuntimeError("Библиотека пуста — нечего сравнивать")

    # Строим векторизованную библиотеку
    logger.info("Сборка векторизованной библиотеки…")
    vlib = build_vectorized_library(skin_library)
    logger.info(f"Библиотека готова: {vlib.n_samples} образцов, {vlib.n_grid} точек сетки")

    # Только статические параметры для dimensionless-расчёта
    from config import Settings
    s = Settings()

    cases = load_test_cases(n_cases)

    results = []
    for i, case in enumerate(cases):
        t = case["t"]
        P = case["P"]
        Q = case["Q"]

        dP_arr = np.abs(s.REF_P0 - P)
        Q_arr = np.full_like(t, float(Q) if Q is not None else s.REF_P0 * 0.1, dtype=float)

        # H-зависимый расчёт
        x_fact = calculate_x(s.REF_k, 10.0, dP_arr, s.REF_mu, s.REF_B, Q_arr)
        # Y-зависимый расчёт
        y_fact = calculate_y(
            Q_arr, s.REF_B, t, s.REF_phi, s.REF_ct, 10.0, dP_arr, L=50.0
        )
        mask = (x_fact > 0) & (y_fact > 0)
        xf = x_fact[mask]
        yf = y_fact[mask]

        if len(xf) < 20:
            logger.warning(f"[{i:03d}] skip: мало валидных точек ({len(xf)})")
            results.append({"file": case.get("file", "?"), "skip": True})
            continue

        # ── Оригинальный солвер ──
        orig_solver = ReservoirSolver(skin_library)
        try:
            orig_res = orig_solver.solve(
                x_fact=xf, y_fact=yf,
                W_fixed=0, N_fixed=None, h_known=10.0,
                k_bounds=(1e-5, 100), xf_bounds=(1e-3, 500), beam=5,
            )
        except Exception as e:
            logger.error(f"[{i:03d}] orig FAILED: {e}")
            orig_res = {"skin": None, "N": None, "L": None, "aL": None, "params": {"k": None}, "misfit": np.inf}

        # ── Векторизованный солвер ──
        vec_solver = VectorizedReservoirSolver(vlib)
        try:
            vec_res = vec_solver.solve(
                x_fact=xf, y_fact=yf,
                W_fixed=0, N_fixed=None, h_known=10.0,
                k_bounds=(1e-5, 100), xf_bounds=(1e-3, 500), beam=5,
            )
        except Exception as e:
            logger.error(f"[{i:03d}] vec FAILED: {e}")
            vec_res = {"skin": None, "N": None, "L": None, "aL": None, "params": {"k": None}, "misfit": np.inf}

        results.append({
            "file": case.get("file", "?"),
            "skip": False,
            "orig": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                     for k, v in orig_res.items() if k != "x_ref_matched" and k != "y_ref_matched"},
            "vec":  {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                     for k, v in vec_res.items() if k != "x_ref_matched" and k != "y_ref_matched"},
        })
        logger.info(
            f"[{i:03d}] orig: S={orig_res['skin']:.3f} k={orig_res['params']['k']:.4f} "
            f"L={orig_res['L']:.2f} N={orig_res['N']} → "
            f"vec:  S={vec_res['skin']:.3f} k={vec_res['params']['k']:.4f} "
            f"L={vec_res['L']:.2f} N={vec_res['N']}"
        )

    # Статистика
    _print_summary(results)
    return results


def _print_summary(results: list):
    """Печатает сводную таблицу совпадений."""
    valid = [r for r in results if not r.get("skip", False)]
    if not valid:
        logger.warning("Нет валидных результатов для статистики")
        return

    print("\n" + "=" * 80)
    print(f"{'#':>4} {'skin_orig':>10} {'skin_vec':>10} {'dS':>8} "
          f"{'L_orig':>8} {'L_vec':>8} {'dL':>8} "
          f"{'F_orig':>10} {'F_vec':>10}")
    print("-" * 80)

    max_dS = max_dL = 0.0
    n_match = 0
    for r in valid:
        o = r["orig"]
        v = r["vec"]
        dS = abs(o["skin"] - v["skin"]) if o["skin"] is not None and v["skin"] is not None else np.nan
        dL = abs(o["L"] - v["L"]) if o["L"] is not None and v["L"] is not None else np.nan
        max_dS = max(max_dS, dS if np.isfinite(dS) else 0)
        max_dL = max(max_dL, dL if np.isfinite(dL) else 0)
        match = "✓" if (np.isfinite(dS) and dS < 0.01 and np.isfinite(dL) and dL < 1.0) else "✗"
        if match == "✓":
            n_match += 1
        print(f"{valid.index(r):>4} {o['skin']:>10.4f} {v['skin']:>10.4f} {dS:>8.4f} "
              f"{o['L']:>8.2f} {v['L']:>8.2f} {dL:>8.2f} "
              f"{o['misfit']:>10.6f} {v['misfit']:>10.6f}  {match}")

    print("-" * 80)
    print(f"Макс. |ΔS| = {max_dS:.4f}, макс. |ΔL| = {max_dL:.2f} м, совпадений: {n_match}/{len(valid)}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Сравнение векторизованного и последовательного солверов")
    parser.add_argument("-n", "--n-cases", type=int, default=20, help="Количество кейсов для теста")
    parser.add_argument("--db", type=str, default=None, help="Путь к БД референсных кривых")
    args = parser.parse_args()

    results = run_comparison(n_cases=args.n_cases, db_path=args.db)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vectorized_comparison.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Результаты сохранены в {out_path}")


if __name__ == "__main__":
    main()
