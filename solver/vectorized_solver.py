"""
solver/vectorized_solver.py

Модуль-транслятор и векторизованный солвер для HydraFracApp.

Архитектура:
  1. VectorizedLibrary — загружает skin_library (dict) и транслирует в
     предвычисленные numpy-структуры (матрицы X_ref, Y_ref на единой сетке).
  2. VectorizedReservoirSolver — ступенчатый подбор Skin/N/aL/L с векторными
     операциями невязки; Шаг 5 (k) остаётся скалярным как и в оригинале.
"""

import numpy as np
import logging
from scipy.interpolate import interp1d
from typing import Dict, List, Tuple, Optional

from .misfit import misfit_shape
from .beam_search import select_top_k
from .derivative import compute_derivative
from .metrics import compute_metric
from .solver_new import align_fact_to_ref


def _choose_alpha(f1, f2):
    """
    Коэффициент смешивания по относительной разности ошибок:
      < 30%  → берём ближайшую (0 или 1)
      30-40% → линейная интерполяция
      > 40%  → середина (0.5)
    """
    if not (np.isfinite(f1) and np.isfinite(f2)):
        return 0.0 if np.isfinite(f1) else 1.0
    denom = max(f1, f2)
    if denom == 0:
        return 0.0
    rel = abs(f1 - f2) / denom
    if rel < 0.30:
        return 0.0 if f1 <= f2 else 1.0
    elif rel > 0.40:
        return 0.5
    else:
        t = (rel - 0.30) / 0.10
        return t * 0.5


def _blend_curves(y1, y2, alpha):
    """
    Линейная смесь двух кривых: alpha=0 → y1, alpha=1 → y2.
    nan-точки одной кривой заполняются из другой.
    """
    out = (1.0 - alpha) * y1 + alpha * y2
    out = np.where(np.isnan(y1), y2, out)
    out = np.where(np.isnan(y2), y1, out)
    return out

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции (уровень модуля)
# ─────────────────────────────────────────────────────────────────────────────

def _h_weight_batch(h_arr: np.ndarray, h_known: Optional[float]) -> np.ndarray:
    """Векторизованный расчёт веса по h для массива значений h."""
    if h_known is None or h_known <= 0:
        return np.ones(len(h_arr), dtype=float)
    return 1.0 / (1.0 + np.abs(h_arr - h_known) / h_known)


def _misfit_batch(
    x_fact_aligned: np.ndarray,
    y_fact_aligned: np.ndarray,
    X_ref: np.ndarray,            # (n_samples, n_grid)
    Y_ref: np.ndarray,            # (n_samples, n_grid)
    overlap_per_sample: np.ndarray,  # (n_samples,) доля перекрытия диапазона
    derivative_mode: str = "linear",
    metric_type: str = "integral",
    penalty_default: float = 1e10,
) -> np.ndarray:
    """
    Векторизованный расчёт misfit_shape для батча референсных кривых сразу.

    Args:
        x_fact_aligned: факт после якорного сдвига (1D)
        y_fact_aligned: факт Y после сдвига (1D)
        X_ref: матрица референсных X (n_samples × n_grid)
        Y_ref: матрица референсных Y (n_samples × n_grid)
        overlap_per_sample: доля перекрытия диапазона X для каждого образца
        derivative_mode, metric_type: параметры misfit
        penalty_default: значение для невалидных образцов

    Returns:
        F_penalized: массив невязок (n_samples,)
    """
    n_samples = X_ref.shape[0]
    n_grid_ref = X_ref.shape[1]

    # Все референсные кривые уже выровнены на глобальную сетку на этапе трансляции.
    # Факт тоже интерполирован на глобальную сетку.
    # x_fact_aligned отсортирован по возрастанию X (часть глобальной сетки).

    # Валидные точки факта
    mask_fact = (x_fact_aligned > 0) & (y_fact_aligned > 0) & np.isfinite(y_fact_aligned)
    if mask_fact.sum() < 20:
        return np.full(n_samples, penalty_default, dtype=float)

    x_fact_v = x_fact_aligned[mask_fact]
    y_fact_v = y_fact_aligned[mask_fact]

    # Общая лог-сетка по диапазону факта
    x_grid = np.logspace(
        np.log10(x_fact_v.min()),
        np.log10(x_fact_v.max()),
        200,
    )

    # Интерполяция факта на общую сетку (один раз)
    f_fact = interp1d(x_fact_v, y_fact_v, bounds_error=False, fill_value=np.nan)
    y_fact_i = f_fact(x_grid)
    mask_fi = (~np.isnan(y_fact_i)) & (y_fact_i > 0)
    if mask_fi.sum() < 20:
        return np.full(n_samples, penalty_default, dtype=float)

    xg  = x_grid[mask_fi]
    y1g = y_fact_i[mask_fi]
    n_f = len(xg)

    # Интерполяция всех референсов на xg одновременно
    # X_ref[i] — уже на глобальной сетке, переинтерполируем на xg
    Y_ri = np.full((n_samples, n_f), np.nan, dtype=float)

    for i in range(n_samples):
        xi = X_ref[i]
        yi = Y_ref[i]
        mask_ri = (xi > 0) & (yi > 0) & np.isfinite(xi) & np.isfinite(yi)
        if mask_ri.sum() < 10:
            continue
        x_pos = xi[mask_ri]
        y_pos = yi[mask_ri]
        try:
            f_ref = interp1d(x_pos, y_pos, bounds_error=False, fill_value=np.nan)
            Y_ri[i] = f_ref(xg)
        except Exception:
            Y_ri[i] = np.nan

    mask_valid = (~np.isnan(Y_ri)) & (Y_ri > 0)  # (n_samples, n_f)
    n_valid = mask_valid.sum(axis=1)

    F = np.full(n_samples, penalty_default, dtype=float)
    valid_mask = n_valid >= 20

    if not np.any(valid_mask):
        return F

    for i in np.where(valid_mask)[0]:
        mv = mask_valid[i]
        # Filter both fact and reference to points where both are valid
        x_common = xg[mv]
        y1g_f = y1g[mv]
        y2g = Y_ri[i][mv]

        med1 = np.median(y1g)
        med2 = np.median(y2g)
        if med1 <= 0 or med2 <= 0:
            continue

        y1n = y1g_f / med1
        y2n = y2g / med2

        _, a1 = compute_derivative(x_common, y1n, derivative_mode)
        _, a2 = compute_derivative(x_common, y2n, derivative_mode)

        F[i] = compute_metric(a1, a2, metric_type, X=x_common)

    # Штраф за малое перекрытие
    F = F / np.maximum(overlap_per_sample, 0.1)
    return F


# ─────────────────────────────────────────────────────────────────────────────
# Транслятор: словарь → векторизованная numpy-структура
# ─────────────────────────────────────────────────────────────────────────────

class VectorizedLibrary:
    """
    Транслирует словарный skin_library в предвычисленные numpy-матрицы.

    После инициализации все операции с библиотекой выполняются на матрицах,
    без Python-циклов по образцам.
    """

    def __init__(
        self,
        skin_library: Dict,
        x_grid_size: int = 200,
    ):
        self.n_grid = x_grid_size
        self._raw = skin_library

        samples = self._flatten(skin_library)
        if not samples:
            raise ValueError("Пустой skin_library")

        # 1. Сбор сырых массивов
        skin_list:      List[float] = []
        L_list:         List[float] = []
        aL_list:        List[float] = []
        N_list:         List[int]   = []
        h_list:         List[float] = []
        W_list:         List[float] = []
        X_clean_list:   List[np.ndarray] = []
        Y_clean_list:   List[np.ndarray] = []

        for s in samples:
            x = s["dynamic"]["X"].values.astype(float)
            y = s["dynamic"]["Y"].values.astype(float)
            mask = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y)
            if mask.sum() < 5:
                logger.warning(f"Образец пропущен: мало валидных точек ({mask.sum()})")
                continue
            x_clean = x[mask]
            y_clean = y[mask]
            X_clean_list.append(x_clean)
            Y_clean_list.append(y_clean)
            skin_list.append(float(s["skin"]))
            L_list.append(float(s.get("L", 0.0)))
            aL_list.append(float(s.get("a/L", 0.0)))
            N_list.append(int(s.get("N", 1)))
            h_list.append(float(s.get("h", 0.0)))
            W_list.append(float(s.get("W", 0.0)))

        self.n_samples = len(X_clean_list)

        # 2. Общая лог-сетка по диапазону всех референсных X
        x_all = np.concatenate(X_clean_list)
        self._global_x_grid = np.logspace(
            np.log10(x_all.min()), np.log10(x_all.max()), x_grid_size
        )

        # 3. Интерполяция всех референсных кривых на общую сетку
        X_mat = np.zeros((self.n_samples, x_grid_size), dtype=float)
        Y_mat = np.zeros((self.n_samples, x_grid_size), dtype=float)
        x_min_arr = np.zeros(self.n_samples, dtype=float)
        x_max_arr = np.zeros(self.n_samples, dtype=float)
        x_first_arr = np.zeros(self.n_samples, dtype=float)

        for i in range(self.n_samples):
            xi = X_clean_list[i]
            yi = Y_clean_list[i]
            try:
                fi = interp1d(xi, yi, bounds_error=False, fill_value=np.nan)
                yi_interp = fi(self._global_x_grid)
            except Exception:
                yi_interp = np.full(x_grid_size, np.nan)
            X_mat[i] = self._global_x_grid
            Y_mat[i] = yi_interp

            # Статистика по диапазону референса
            xi_pos = xi[xi > 0]
            x_first_arr[i] = xi_pos[0] if len(xi_pos) > 0 else 1.0
            valid_mask = (~np.isnan(yi_interp)) & (yi_interp > 0)
            xv = self._global_x_grid[valid_mask]
            x_min_arr[i] = xv.min() if len(xv) > 0 else 0.0
            x_max_arr[i] = xv.max() if len(xv) > 0 else 0.0

        self.X_ref        = X_mat          # (n_samples, n_grid)
        self.Y_ref        = Y_mat          # (n_samples, n_grid)
        self.x_min_arr    = x_min_arr      # (n_samples,) левая граница валидных X
        self.x_max_arr    = x_max_arr      # (n_samples,) правая граница валидных X
        self.x_first_arr  = x_first_arr    # (n_samples,) первая положительная точка X

        self.lib_x0_median = float(np.median(x_first_arr))

        self.skin_arr = np.array(skin_list, dtype=float)
        self.L_arr    = np.array(L_list,   dtype=float)
        self.aL_arr   = np.array(aL_list,  dtype=float)
        self.N_arr    = np.array(N_list,   dtype=int)
        self.h_arr    = np.array(h_list,   dtype=float)
        self.W_arr    = np.array(W_list,   dtype=float)

        logger.info(
            f"Трансляция завершена: {self.n_samples} образцов, "
            f"grid_size={x_grid_size}, lib_x0_median={self.lib_x0_median:.4f}"
        )

    def __getstate__(self):
        """Сериализация для pickle: сохраняем только numpy-матрицы, без _raw."""
        return {
            'n_grid':        self.n_grid,
            'n_samples':     self.n_samples,
            'X_ref':         self.X_ref,
            'Y_ref':         self.Y_ref,
            'x_min_arr':     self.x_min_arr,
            'x_max_arr':     self.x_max_arr,
            'x_first_arr':   self.x_first_arr,
            'global_x_grid': self._global_x_grid,
            'skin_arr':      self.skin_arr,
            'L_arr':         self.L_arr,
            'aL_arr':        self.aL_arr,
            'N_arr':         self.N_arr,
            'h_arr':         self.h_arr,
            'W_arr':         self.W_arr,
            'lib_x0_median': self.lib_x0_median,
        }

    def __setstate__(self, state):
        """Десериализация из pickle: восстанавливаем все атрибуты."""
        self.n_grid         = state['n_grid']
        self.n_samples      = state['n_samples']
        self.X_ref          = state['X_ref']
        self.Y_ref          = state['Y_ref']
        self.x_min_arr      = state['x_min_arr']
        self.x_max_arr      = state['x_max_arr']
        self.x_first_arr    = state['x_first_arr']
        self._global_x_grid = state['global_x_grid']
        self.skin_arr       = state['skin_arr']
        self.L_arr          = state['L_arr']
        self.aL_arr         = state['aL_arr']
        self.N_arr          = state['N_arr']
        self.h_arr          = state['h_arr']
        self.W_arr          = state['W_arr']
        self.lib_x0_median  = state['lib_x0_median']
        self._raw           = None

    @staticmethod
    def _flatten(skin_library):
        samples = []
        for skin_val, slist in skin_library.items():
            for s in slist:
                s_copy = dict(s)
                s_copy["skin"] = skin_val  # Ensure skin is in sample
                samples.append(s_copy)
        return samples


# ─────────────────────────────────────────────────────────────────────────────
# Векторизованный солвер
# ─────────────────────────────────────────────────────────────────────────────

class VectorizedReservoirSolver:
    """
    Ступенчатый подбор параметров с векторными операциями невязки.

    Отличие от ReservoirSolver:
      - шаг 1 (Skin): невязка считается сразу для всех образцов в один вызов,
        без Python-цикла по словарю
      - шаг 2 (N): фильтрация по top_skins векторизована, misfit в батче
      - шаг 3 (a/L): аналогично шагу 1
      - шаг 4 (L): дискретный перебор векторизован; blend между соседями
        остаётся последовательным из-за пороговой логики _choose_alpha
      - шаг 5 (k): скалярный, как в оригинале
    """

    def __init__(self, vlib: VectorizedLibrary, progress_callback=None):
        self.vlib = vlib
        self.progress_callback = progress_callback
        self.derivative_mode = "linear"
        self.metric_type = "integral"

        # Внутреннее состояние (кэшируется после _prepare)
        self._x_fact_aligned: Optional[np.ndarray] = None
        self._y_fact_aligned: Optional[np.ndarray] = None
        self._x_fact_raw: Optional[np.ndarray] = None
        self._y_fact_raw: Optional[np.ndarray] = None

    # ── шаг 0 — подготовка фактической кривой ──────────────────────────────

    def _prepare(self, x_fact_raw, y_fact_raw, n_points=200):
        """Интерполирует фактическую кривую на общую сетку библиотеки."""
        mask = (x_fact_raw > 0) & (y_fact_raw > 0) & np.isfinite(x_fact_raw) & np.isfinite(y_fact_raw)
        xf = x_fact_raw[mask]
        yf = y_fact_raw[mask]

        self._x_fact_raw = xf
        self._y_fact_raw = yf

        try:
            f = interp1d(xf, yf, bounds_error=False, fill_value=np.nan)
            y_on_grid = f(self.vlib._global_x_grid)
        except Exception:
            y_on_grid = np.full(self.vlib.n_grid, np.nan)

        valid = (~np.isnan(y_on_grid)) & (y_on_grid > 0)
        self._x_fact_aligned = self.vlib._global_x_grid[valid]
        self._y_fact_aligned = y_on_grid[valid]

        logger.info(
            f"Подготовка: {len(xf)} исходных точек → "
            f"{len(self._x_fact_aligned)} на общей сетке "
            f"X=[{self._x_fact_aligned[0]:.4e}, {self._x_fact_aligned[-1]:.4e}]"
        )

    # ── повреждённая невязка по фактору ───────────────────────────────────

    def _compute_misfit_vectorized(
        self,
        indices: np.ndarray,
        W_fixed: Optional[float] = None,
        N_fixed: Optional[int] = None,
    ) -> np.ndarray:
        """
        Вычисляет взвешенную невязку для батча индексов референсов.

        Фильтрация по W: если W_fixed задан и != 0, выбираются только
        образцы с W == W_fixed. W_scale_factor вычисляется позже.

        Векторизованная замена последовательных вызовов _sample_misfit.
        """
        # Фильтрация по W и N
        mask_w = np.ones(len(indices), dtype=bool)
        if W_fixed is not None and W_fixed != 0:
            mask_w = (self.vlib.W_arr[indices] == W_fixed)

        mask_n = np.ones(len(indices), dtype=bool)
        if N_fixed is not None:
            mask_n = (self.vlib.N_arr[indices] == N_fixed)

        active = mask_w & mask_n
        if not np.any(active):
            return np.full(len(indices), np.inf, dtype=float)

        # Overlap: доля перекрытия диапазона факта с диапазоном каждого референса
        fa_min  = self._x_fact_aligned.min()
        fa_max  = self._x_fact_aligned.max()
        fa_span = fa_max - fa_min

        overlap = np.zeros(len(indices), dtype=float)
        if fa_span > 0:
            idx_active = np.where(active)[0]
            r_min = self.vlib.x_min_arr[idx_active]
            r_max = self.vlib.x_max_arr[idx_active]
            # Верхняя граница пересечения: max(нижних_границ)
            x_upper = np.fmax(fa_min, r_min)
            # Нижняя граница пересечения: min(верхних_границ)
            x_lower = np.fmin(fa_max, r_max)
            overlap[idx_active] = np.maximum(x_lower - x_upper, 0.0) / fa_span

        # Batch misfit для всех индексов
        F_raw = _misfit_batch(
            x_fact_aligned=self._x_fact_aligned,
            y_fact_aligned=self._y_fact_aligned,
            X_ref=self.vlib.X_ref[indices],
            Y_ref=self.vlib.Y_ref[indices],
            overlap_per_sample=overlap,
            derivative_mode=self.derivative_mode,
            metric_type=self.metric_type,
        )

        # Взвешивание по h
        h_weights = _h_weight_batch(self.vlib.h_arr[indices], None)
        F_w = np.where(np.isfinite(F_raw), F_raw / h_weights, np.inf)

        return F_w

    # ── шаг 1 — Skin ───────────────────────────────────────────────────────

    def select_skin(self, samples, h_known=None, beam=5):
        """Векторизованный подбор Skin по всем образцам библиотеки сразу."""
        n_total = self.vlib.n_samples
        all_idx = np.arange(n_total)

        F_all = self._compute_misfit_vectorized(all_idx)

        # Группировка по Skin: минимальная невязка для каждого значения
        unique_skins = np.unique(self.vlib.skin_arr)
        skin_scores  = {}
        for sk in unique_skins:
            skin_mask = (self.vlib.skin_arr == sk)
            if not np.any(~np.isinf(F_all[skin_mask])):
                continue
            skin_scores[sk] = float(np.min(F_all[skin_mask]))

        top_skins = select_top_k(skin_scores, beam)
        logger.info(
            f"Шаг 1 — Skin. Векторизовано: {n_total} образцов, "
            f"уникальных Skin: {len(unique_skins)}, топ: {top_skins}"
        )
        return top_skins, skin_scores

    # ── шаг 2 — N ─────────────────────────────────────────────────────────

    def select_N(self, samples, top_skins, beam=5):
        """Векторизованный подбор N в пределах top_skins."""
        skin_mask = np.isin(self.vlib.skin_arr, top_skins)
        indices = np.where(skin_mask)[0]

        if len(indices) == 0:
            logger.warning("Нет образцов для top_skins, возвращаю N=1")
            return top_skins[0], 1, {}

        F_all = self._compute_misfit_vectorized(indices)

        # Группировка по (Skin, N): минимальная невязка для каждой пары
        sn_scores: Dict[Tuple[float, int], float] = {}
        for pos, idx in enumerate(indices):
            sk  = self.vlib.skin_arr[idx]
            nv  = int(self.vlib.N_arr[idx])
            fv  = F_all[pos]
            if np.isinf(fv):
                continue
            key = (sk, nv)
            if key not in sn_scores or fv < sn_scores[key]:
                sn_scores[key] = fv

        if not sn_scores:
            best_skin, best_N = top_skins[0], 1
        else:
            best_key               = min(sn_scores, key=sn_scores.get)
            best_skin, best_N      = best_key

        logger.info(
            f"Шаг 2 — N. Проверено пар: {len(sn_scores)}, "
            f"лучший: Skin={best_skin:.3f}, N={best_N}"
        )
        return best_skin, best_N, sn_scores

    # ── шаг 3 — a/L ───────────────────────────────────────────────────────

    def select_aL(self, samples, skin, N, beam=5):
        """Векторизованный подбор a/L."""
        skin_mask = (self.vlib.skin_arr == skin)
        n_mask    = (self.vlib.N_arr == N)
        indices   = np.where(skin_mask & n_mask)[0]

        if len(indices) == 0:
            logger.warning(f"Нет образцов для Skin={skin}, N={N} на шаге 3")
            return [], {}

        F_all = self._compute_misfit_vectorized(indices)

        # Группировка по a/L: минимальная невязка для каждого a/L
        al_scores: Dict[float, float] = {}
        for pos, idx in enumerate(indices):
            al = float(self.vlib.aL_arr[idx])
            fv = F_all[pos]
            if np.isinf(fv):
                continue
            if al not in al_scores or fv < al_scores[al]:
                al_scores[al] = fv

        top_aL = select_top_k(al_scores, beam)
        logger.info(
            f"Шаг 3 — a/L (S={skin:.3f}, N={N}). "
            f"Проверено: {len(al_scores)} значений"
        )
        return top_aL, al_scores

    # ── шаг 4 — L ─────────────────────────────────────────────────────────

    def select_L(self, samples, skin, N, top_aL):
        """
        Подбор L. Дискретный перебор векторизован, blend остаётся
        последовательным из-за пороговой логики выбора alpha.
        """
        skin_mask = (self.vlib.skin_arr == skin)
        n_mask    = (self.vlib.N_arr == N)
        al_mask   = np.isin(self.vlib.aL_arr, top_aL)
        indices   = np.where(skin_mask & n_mask & al_mask)[0]

        if len(indices) == 0:
            logger.warning("Нет образцов для поиска L (шаг 4)")
            return None, None, None, None, 1.0, 1.0, np.inf

        # Векторизованный дискретный перебор L
        L_all = self.vlib.L_arr[indices]
        F_all = self._compute_misfit_vectorized(indices)

        # Группировка по L: min(F) для каждого L
        L_scores:    Dict[float, float]   = {}
        L_best_idx:  Dict[float, int]     = {}
        for pos, idx in enumerate(indices):
            L_val = float(self.vlib.L_arr[idx])
            fv    = F_all[pos]
            if np.isinf(fv):
                continue
            if L_val not in L_scores or fv < L_scores[L_val]:
                L_scores[L_val]   = fv
                L_best_idx[L_val] = idx

        if not L_scores:
            return None, None, None, None, 1.0, 1.0, np.inf

        sorted_L  = sorted(L_scores, key=lambda L: L_scores[L])
        best_L    = sorted_L[0]
        best_F    = L_scores[best_L]
        best_idx  = L_best_idx[best_L]

        logger.info(f"Шаг 4 — L. Проверено {len(sorted_L)} значений, лучший L={best_L:.2f}")

        # Blend-интерполяция между соседями (последовательная, пороговая логика)
        best_pos = sorted_L.index(best_L)
        neighbours: List[Tuple[float, float, int]] = []
        if best_pos > 0:
            nb_L = sorted_L[best_pos - 1]
            neighbours.append((nb_L, L_scores[nb_L], L_best_idx[nb_L]))
        if best_pos < len(sorted_L) - 1:
            nb_L = sorted_L[best_pos + 1]
            neighbours.append((nb_L, L_scores[nb_L], L_best_idx[nb_L]))

        if neighbours:
            L_nb, F_nb, idx_nb = min(neighbours, key=lambda t: t[1])
            alpha = _choose_alpha(best_F, F_nb)

            if 0.0 < alpha < 1.0:
                x_best = self.vlib.X_ref[best_idx]
                y_best = self.vlib.Y_ref[best_idx]
                x_nb   = self.vlib.X_ref[idx_nb]
                y_nb   = self.vlib.Y_ref[idx_nb]

                xb = np.logspace(
                    np.log10(max(x_best.min(), x_nb.min())),
                    np.log10(min(x_best.max(), x_nb.max())),
                    300,
                )
                y_best_i = interp1d(x_best, y_best, bounds_error=False, fill_value=np.nan)(xb)
                y_nb_i   = interp1d(x_nb,   y_nb,   bounds_error=False, fill_value=np.nan)(xb)
                yb       = _blend_curves(y_best_i, y_nb_i, alpha)

                x_al, y_al, _, _ = align_fact_to_ref(
                    self._x_fact_raw, self._y_fact_raw, xb, yb
                )
                xa_pos = x_al[x_al > 0]
                xb_pos = xb[xb > 0]

                F_bl = np.inf
                if len(xa_pos) > 0 and len(xb_pos) > 0:
                    xmin_b  = max(xa_pos.min(), xb_pos.min())
                    xmax_b  = min(xa_pos.max(), xb_pos.max())
                    span_b  = xa_pos.max() - xa_pos.min()
                    overlap_b = ((xmax_b - xmin_b) / span_b) if span_b > 0 else 0.0
                    F_bl    = misfit_shape(
                        x_al, y_al, xb, yb,
                        derivative_mode=self.derivative_mode,
                        metric_type=self.metric_type,
                    )
                    F_bl    = F_bl / max(overlap_b, 0.1)

                L_bl = (1.0 - alpha) * best_L + alpha * L_nb
                aL_bl = (1.0 - alpha) * float(self.vlib.aL_arr[best_idx]) + alpha * float(self.vlib.aL_arr[idx_nb])

                logger.info(
                    f"  Blend: L={best_L:.1f}+{L_nb:.1f}, alpha={alpha:.3f} "
                    f"→ L={L_bl:.2f}, F={F_bl:.6f}"
                )
                if F_bl <= best_F:
                    return L_bl, aL_bl, xb, yb, 1.0, 1.0, F_bl

        return (
            best_L, float(self.vlib.aL_arr[best_idx]),
            self.vlib.X_ref[best_idx], self.vlib.Y_ref[best_idx],
            1.0, 1.0, best_F,
        )

    # ── шаг 5 — k ─────────────────────────────────────────────────────────

    def recover_k(self, X_ref_best: np.ndarray, k_ref: float = 5.0,
                  k_bounds: Tuple[float, float] = (1e-5, 100)) -> float:
        """Восстановление k из соотношения медиан X факта и референса."""
        x_ref_v  = X_ref_best[X_ref_best > 0]
        x_fact_v = self._x_fact_aligned[self._x_fact_aligned > 0]

        if len(x_ref_v) == 0 or len(x_fact_v) == 0:
            logger.warning("recover_k: нет положительных X")
            return k_ref

        med_fact = np.median(x_fact_v)
        med_ref  = np.median(x_ref_v)
        if med_ref == 0:
            return k_ref

        k_real = k_ref * (med_fact / med_ref)
        k_real = float(np.clip(k_real, k_bounds[0], k_bounds[1]))
        logger.info(
            f"Шаг 5 — k: median_fact={med_fact:.4f}, "
            f"median_ref={med_ref:.4f} → k={k_real:.6f} мД"
        )
        return k_real

    # ── главный метод solve ────────────────────────────────────────────────

    def solve(
        self,
        x_fact: np.ndarray,
        y_fact: np.ndarray,
        W_fixed: Optional[float] = None,
        N_fixed: Optional[int] = None,
        h_known: Optional[float] = None,
        k_bounds: Tuple[float, float] = (1e-5, 100),
        xf_bounds: Tuple[float, float] = (1e-3, 500),
        beam: int = 5,
    ):
        """
        Полный ступенчатый подбор. Возвращает словарь с результатами,
        совместимый с ReservoirSolver.solve().
        """
        logger.info("=" * 60)
        logger.info("ВЕКТОРИЗОВАННЫЙ ОПТИМИЗАЦИЯ: W={}, N={}, h={}".format(W_fixed, N_fixed, h_known))

        self._prepare(x_fact, y_fact)

        # Шаг 1 — векторизованный Skin
        logger.info("\n--- Шаг 1: Skin (вектор) ---")
        top_skins, _ = self.select_skin(None, h_known=h_known, beam=beam)

        # Шаг 2 — векторизованный N
        if N_fixed is not None:
            best_skin, best_N = top_skins[0], N_fixed
            logger.info(f"\n--- Шаг 2: N зафиксирован={N_fixed} ---")
        else:
            logger.info("\n--- Шаг 2: N (вектор) ---")
            best_skin, best_N, _ = self.select_N(None, top_skins, beam=beam)

        logger.info(f"  → Skin={best_skin:.3f}, N={best_N}")

        # Шаг 3 — векторизованный a/L
        logger.info("\n--- Шаг 3: a/L (вектор) ---")
        top_aL, _ = self.select_aL(None, best_skin, best_N, beam=beam)

        # Шаг 4 — L (дискретный перебор векторизован, blend последовательный)
        logger.info("\n--- Шаг 4: L (вектор + blend) ---")
        result_L = self.select_L(None, best_skin, best_N, top_aL)
        if result_L[0] is None:
            raise ValueError("Не удалось подобрать L — нет подходящих образцов.")

        best_L, best_aL, x_ref_f, y_ref_f, _, _, misfit_f = result_L

        # Compute W_scale_factor from best sample
        # Find the best sample index to get its W value
        L_diffs = np.abs(self.vlib.L_arr - best_L)
        skin_b  = self.vlib.skin_arr
        n_b     = self.vlib.N_arr
        candidate_mask = (skin_b == best_skin) & (n_b == best_N)
        if candidate_mask.any():
            L_diffs[~candidate_mask] = np.inf
        else:
            L_diffs[:] = np.inf
        best_sample_idx = int(np.argmin(L_diffs))
        best_W = float(self.vlib.W_arr[best_sample_idx])

        if W_fixed is not None and W_fixed > 0 and best_W > 0:
            W_scale_factor = best_W / W_fixed
        else:
            W_scale_factor = 1.0

        # Шаг 5 — k (скалярно)
        logger.info("\n--- Шаг 5: k ---")
        X_ref_best = self.vlib.X_ref[best_sample_idx]

        k_opt = self.recover_k(X_ref_best, k_ref=5.0, k_bounds=k_bounds)
        best_h = float(self.vlib.h_arr[best_sample_idx])

        logger.info(
            f"\nРЕЗУЛЬТАТ: Skin={best_skin:.4f}, k={k_opt:.6f} мД, "
            f"L={best_L:.4f} м, a/L={best_aL:.4f}, "
            f"N={best_N}, misfit={misfit_f:.6f}"
        )
        logger.info("=" * 60)

        return {
            "skin":  best_skin,
            "N":     best_N,
            "L":     best_L,
            "aL":    best_aL,
            "h":     best_h,
            "W":     best_W,
            "W_scale_factor": W_scale_factor,
            "params": {"k": k_opt, "xf": best_L},
            "misfit": misfit_f,
            "x_ref_matched": x_ref_f,
            "y_ref_matched": y_ref_f,
        }

    def solve_top_candidates(self, x_fact, y_fact, **kwargs):
        """Алиас для совместимости — вызывает solve, возвращает список из одного результата."""
        r = self.solve(x_fact, y_fact, **kwargs)
        return [r]


# ─────────────────────────────────────────────────────────────────────────────
# Транслятор словарной библиотеки в VectorizedLibrary
# ─────────────────────────────────────────────────────────────────────────────

def build_vectorized_library(
    skin_library: Dict,
    x_grid_size: int = 200,
) -> VectorizedLibrary:
    """
    Создаёт VectorizedLibrary из стандартного словарного skin_library.

    Это единственная точка контакта с legacy-форматом хранения библиотеки.
    После трансляции модуль solver_new не нужен для выполнения большинства шагов.

    Args:
        skin_library: dict {skin_value: [samples]} из ReferenceRepository
        x_grid_size: количество точек в общей лог-сетке (рекомендуется 200)

    Returns:
        VectorizedLibrary — готовая к использованию в VectorizedReservoirSolver
    """
    logger.info(f"Сборка векторизованной библиотеки из {len(skin_library)} Skin-значений…")
    vlib = VectorizedLibrary(skin_library, x_grid_size=x_grid_size)
    logger.info(
        f"Готово: {vlib.n_samples} образцов, "
        f"n_grid={vlib.n_grid}, lib_x0_median={vlib.lib_x0_median:.4f}"
    )
    return vlib
