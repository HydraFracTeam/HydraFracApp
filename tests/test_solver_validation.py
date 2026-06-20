"""
tests/test_solver_validation.py - точность подбора с порогом 5%
"""

import sys
import os
import numpy as np
import json
import time
import glob
import warnings
from scipy.signal import savgol_filter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

warnings.filterwarnings('ignore', category=UserWarning)

MU = 1.0
PHI = 0.2
CT = 0.00004
B = 1.0
P0 = 300.0
Q = 100.0
K_REF = 5.0

# 5% tolerance for all parameters
EPS = 0.05

def main():
    from solver.vectorized_solver import VectorizedReservoirSolver, build_vectorized_library
    from core.reference_repo import ReferenceRepository
    from core.dimensionless import calculate_x, calculate_y
    
    repo = ReferenceRepository()
    skin_library = repo.get_skin_library()
    vlib = build_vectorized_library(skin_library)
    
    case_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset_cases")
    all_files = sorted(glob.glob(os.path.join(case_dir, "*.csv")))
    
    valid_cases = []
    for f in all_files[:50]:
        data = np.genfromtxt(f, delimiter=",", skip_header=1)
        if data.ndim == 2 and data.shape[1] >= 8 and data.shape[0] > 10:
            valid_cases.append(data)
    
    selected = valid_cases[:10]
    noise_levels = [0.0, 0.02, 0.05, 0.10]
    
    print("Testing with 5%% tolerance for all parameters (Q=%.0f)" % Q)
    print("-" * 90)
    print(" Noise  Filter  Skin%%   L%%     k%%")
    
    for noise_level in noise_levels:
        for filt in [False, True]:
            results = []
            for data in selected:
                t_raw = data[:, 0]
                P_raw = data[:, 1]
                Skin_true = float(data[0, 2])
                h_true = float(data[0, 3])
                N_true = int(data[0, 4])
                W_true = float(data[0, 5])
                L_true = float(data[0, 6])
                
                P = P_raw.copy()
                if noise_level > 0:
                    noise_val = noise_level * np.std(P)
                    P_noisy = P + np.random.normal(0, noise_val, len(P))
                    P = np.clip(P_noisy, 1e-10, None)
                
                if filt and noise_level > 0:
                    window = min(len(P) // 6, 11)
                    if window % 2 == 0:
                        window += 1
                    if window >= 5:
                        P = savgol_filter(P, window, 2)
                
                dP_arr = np.abs(P[0] - P)
                Q_arr = np.full_like(t_raw, Q, dtype=float)
                
                X = calculate_x(k=K_REF, h=h_true, delta_p=dP_arr, mu=MU, B=B, Q=Q_arr)
                Y = calculate_y(Q=Q_arr, B=B, t=t_raw, phi=PHI, ct=CT, h=h_true, delta_p=dP_arr, L=L_true)
                
                mask = np.isfinite(X) & np.isfinite(Y) & (X > 0) & (Y > 0)
                X, Y = X[mask], Y[mask]
                
                if len(X) < 50:
                    continue
                
                solver = VectorizedReservoirSolver(vlib)
                result = {"misfit": np.inf}
                try:
                    result = solver.solve(
                        x_fact=X, y_fact=Y, W_fixed=W_true, N_fixed=N_true,
                        h_known=h_true, k_bounds=(1e-5, 100),
                        xf_bounds=(1, 500), beam=5
                    )
                except Exception:
                    pass
                
                found_skin = result.get("skin")
                found_L = result.get("L", np.nan)
                found_k = result.get("params", {}).get("k")
                
                skin_ok = found_skin is not None and abs(found_skin - Skin_true) <= Skin_true * EPS if Skin_true > 0 else False
                L_ok = found_L is not None and found_L > 0 and abs(found_L - L_true) / L_true <= EPS if L_true > 0 else False
                k_ok = found_k is not None and found_k > 0 and abs(found_k - K_REF) / K_REF <= EPS if K_REF > 0 else False
                
                results.append({"skin_ok": skin_ok, "L_ok": L_ok, "k_ok": k_ok})
            
            if results:
                skin_pct = len([r for r in results if r["skin_ok"]]) / len(results) * 100
                L_pct = len([r for r in results if r["L_ok"]]) / len(results) * 100
                k_pct = len([r for r in results if r["k_ok"]]) / len(results) * 100
                filt_str = "Yes" if filt else "No"
                print(" %5.1f%%  %5s   %5.1f%% %5.1f%% %5.1f%%" % (
                    noise_level*100, filt_str, skin_pct, L_pct, k_pct))
    
    print("-" * 90)


if __name__ == "__main__":
    main()