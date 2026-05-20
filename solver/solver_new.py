# solver/solver_new.py

import numpy as np
import logging
from scipy.interpolate import interp1d

from .misfit import misfit_shape
from .derivative import compute_derivative
from .beam_search import select_top_k

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────

def _interp_curve(x, y, x_grid):
    """Интерполяция (x, y) на x_grid. Возвращает массив с nan вне диапазона."""
    try:
        f = interp1d(x, y, bounds_error=False, fill_value=np.nan)
        return f(x_grid)
    except Exception:
        return np.full_like(x_grid, np.nan, dtype=float)


def _blend_curves(y1, y2, alpha):
    """
    Линейная смесь двух кривых: alpha=0 → y1, alpha=1 → y2.
    nan-точки одной кривой заполняются из другой.
    """
    out = (1.0 - alpha) * y1 + alpha * y2
    out = np.where(np.isnan(y1), y2, out)
    out = np.where(np.isnan(y2), y1, out)
    return out


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


def _h_weight(h_sample, h_known):
    """
    Мягкий весовой коэффициент по близости h.
    weight = 1 / (1 + |Δh| / h_known), допуск ±50%.
    """
    if h_known is None or h_known <= 0:
        return 1.0
    return 1.0 / (1.0 + abs(h_sample - h_known) / h_known)


# ─────────────────────────────────────────────────────────────
# Ключевая функция: выравнивание кривых перед сравнением
# ─────────────────────────────────────────────────────────────

def _all_ref_x_median(skin_library):
    """
    Медиана первых точек X по всей библиотеке.
    Используется как верхняя граница stretch.
    Вычисляется один раз и кэшируется в ReservoirSolver.
    """
    first_x = []
    for samples in skin_library.values():
        for s in samples:
            x = s.get("x")
            if x is None:
                x = s["dynamic"]["X"].to_numpy(dtype=float)
                s["x"] = x
            if len(x) > 0 and x[0] > 0:
                first_x.append(x[0])
    return float(np.median(first_x)) if first_x else 1.0


def align_fact_to_ref(x_fact, y_fact, x_ref, y_ref,
                      stretch_max=None):
    """
    Совмещение фактической кривой с референсной.

    ШАГ 1 — якорный сдвиг (без потери формы):
        Совмещаем первые точки по X:
            shift_x = x_ref[0] / x_fact[0]
            x_anchored = x_fact * shift_x

        Первые точки — минимальные X (данные отсортированы по времени/elemIdx).
        Это эквивалентно сдвигу в log-пространстве — форма не меняется.

    ШАГ 2 — растяжение по X (подгонка масштаба):
        После якорного сдвига кривые начинаются в одной точке,
        но могут иметь разный "разбег" по X. Ищем stretch ∈ (0, stretch_max]:
            x_stretched = x_anchored * stretch

        stretch_max = median(X_ref_first_points всей библиотеки) / x_ref[0]
        Это естественный предел: не растягиваем факт дальше медианы библиотеки.

        Оптимизация: грубый перебор n_coarse точек → Nelder-Mead уточнение.
        Целевая функция: misfit_shape(dY/dX) на совмещённых кривых.

    Y не трогаем — только X.

    Returns:
        x_aligned  : факт после сдвига + растяжения
        y_aligned  : факт Y без изменений
        shift_x    : якорный коэффициент (x_ref[0] / x_fact[0])
        stretch    : оптимальный коэффициент растяжения
    """
    # --- ШАГ 1: якорный сдвиг по первой точке ---
    x_fact_0 = x_fact[x_fact > 0][0]
    x_ref_0  = x_ref[x_ref > 0][0]

    if x_fact_0 <= 0 or x_ref_0 <= 0:
        return x_fact, y_fact, 1.0, 1.0

    shift_x = x_ref_0 / x_fact_0
    x_anchored = x_fact * shift_x

    # --- ШАГ 2: растяжение УБРАНО ---
    # Оставляем только anchor shift (совмещение первых точек)
    # stretch = 1.0 (без растяжения/сжатия)
    return x_anchored, y_fact, shift_x, 1.0


# ─────────────────────────────────────────────────────────────
# ReservoirSolver
# ─────────────────────────────────────────────────────────────

class ReservoirSolver:
    """
    Ступенчатый подбор параметров трещины по совпадению формы dY/dX.

    Выравнивание кривых перед каждым misfit:
        1. Якорный сдвиг по первой точке X:
               shift_x = x_ref[0] / x_fact[0]
           Совмещает начала кривых без изменения формы.
        2. Растяжение по X в диапазоне (0, stretch_max]:
               x_aligned = x_fact * shift_x * stretch
           stretch_max = median(x[0] всей библиотеки) / x_ref[0].
           Ищется грубым перебором + minimize_scalar.
           Y не трогаем.

    Шаги:
        0: фильтрация по W + N
        1: select_skin   — beam search, h-взвешивание
        2: select_N      — если N не задан
        3: select_aL     — перебор a/L
        4: select_L      — перебор L + интерполяция между соседями
    """

    def __init__(self, skin_library, progress_callback=None):
        self.skin_library = skin_library
        self.progress_callback = progress_callback

        self.derivative_mode = "linear"
        self.metric_type = "integral"

        self._x_grid = None
        self._y_fact = None
        self._x_fact_raw = None
        self._y_fact_raw = None
        self._sample_misfit_cache = {}

        # Медиана первых X по всей библиотеке — верхняя граница stretch.
        # Вычисляется один раз при инициализации.
        self._lib_x0_median = _all_ref_x_median(skin_library)
        logger.info(f"Медиана первых X библиотеки: {self._lib_x0_median:.4f}")

    # ------------------------------------------------------------------
    # Шаг 0
    # ------------------------------------------------------------------

    def _prepare(self, x_fact, y_fact, n_points=200):
        """Интерполирует входную кривую на равномерную лог-сетку."""
        mask = (x_fact > 0) & (y_fact > 0) & np.isfinite(x_fact) & np.isfinite(y_fact)
        x_fact = x_fact[mask]
        y_fact = y_fact[mask]

        # Сырые данные сохраняем для align_fact_to_ref
        self._x_fact_raw = x_fact
        self._y_fact_raw = y_fact
        self._sample_misfit_cache.clear()

        x_grid = np.logspace(
            np.log10(x_fact.min()), np.log10(x_fact.max()), n_points
        )
        y_interp = _interp_curve(x_fact, y_fact, x_grid)
        valid = ~np.isnan(y_interp)

        self._x_grid = x_grid[valid]
        self._y_fact = y_interp[valid]

        # Предпосчитываем производную факта один раз — для ускорения
        _, self._alpha_fact = compute_derivative(
            self._x_grid, self._y_fact, self.derivative_mode
        )
        logger.info(f"Производная факта предпосчитана: {len(self._alpha_fact)} точек")

        logger.info(
            f"Подготовка: {len(x_fact)} → {len(self._x_grid)} точек, "
            f"X=[{self._x_grid[0]:.4f}, {self._x_grid[-1]:.4f}], "
            f"Y=[{self._y_fact.min():.4e}, {self._y_fact.max():.4e}]"
        )

    def _filter_library(self, W_fixed, N_fixed=None):
        """Жёсткая фильтрация по W (0/None = все) + опциональная по N."""
        ignore_W = (W_fixed is None or W_fixed == 0)
        result = []
        for skin_val, samples in self.skin_library.items():
            for s in samples:
                if not ignore_W and s["W"] != W_fixed:
                    continue
                if N_fixed is not None and s["N"] != N_fixed:
                    continue
                result.append({**s, "skin": skin_val})

        logger.info(
            f"Фильтрация W={'any' if ignore_W else W_fixed}"
            + (f", N={N_fixed}" if N_fixed is not None else "")
            + f": {len(result)} образцов"
        )
        return result

    # ------------------------------------------------------------------
    # Базовый misfit с выравниванием
    # ------------------------------------------------------------------

    def _sample_misfit(self, sample):
        """
        Misfit формы с предварительным выравниванием.

        1. align_fact_to_ref:
             - якорный сдвиг: shift_x = x_ref[0] / x_fact[0]
             - растяжение stretch ∈ (0, stretch_max] по minimize_scalar
             stretch_max = self._lib_x0_median / x_ref[0]
        2. misfit_shape(dY/dX, linear) на совмещённых кривых
        3. Штраф за малое перекрытие X

        Возвращает (F_penalized, shift_x, stretch).
        """
        cache_key = (
            sample.get("skin"),
            sample.get("N"),
            sample.get("W"),
            sample.get("L"),
            sample.get("a/L"),
            sample.get("h"),
        )
        cached = self._sample_misfit_cache.get(cache_key)
        if cached is not None:
            return cached

        x_ref = sample.get("x")
        y_ref = sample.get("y")
        if x_ref is None or y_ref is None:
            x_ref = sample["dynamic"]["X"].values.astype(float)
            y_ref = sample["dynamic"]["Y"].values.astype(float)
            sample["x"] = x_ref
            sample["y"] = y_ref

        # stretch_max для этого референса: медиана библиотеки / первая точка этого ref
        try:
            x_ref_0 = x_ref[x_ref > 0][0]
        except IndexError:
            # Нет положительных X в референсе
            logger.warning(f"Референс {sample.get('skin', '?')}/{sample.get('N', '?')} не имеет положительных X")
            result = (np.inf, 1.0, 1.0)
            self._sample_misfit_cache[cache_key] = result
            return result
        
        stretch_max = self._lib_x0_median / x_ref_0 if x_ref_0 > 0 else 1.0
        stretch_max = max(stretch_max, 1.0)  # минимум 1 — без сжатия ниже якорной точки

        x_al, y_al, shift_x, stretch = align_fact_to_ref(
            self._x_fact_raw, self._y_fact_raw,
            x_ref, y_ref,
            stretch_max=stretch_max,
        )

        # Перекрытие после выравнивания
        x_al_pos = x_al[x_al > 0]
        x_ref_pos = x_ref[x_ref > 0]
        if len(x_al_pos) == 0 or len(x_ref_pos) == 0:
            logger.debug(f"Нет положительных X для {sample.get('skin', '?')}/{sample.get('N', '?')}")
            result = (np.inf, shift_x, stretch)
            self._sample_misfit_cache[cache_key] = result
            return result

        xmin = max(x_al_pos.min(), x_ref_pos.min())
        xmax = min(x_al_pos.max(), x_ref_pos.max())
        span = x_al_pos.max() - x_al_pos.min()
        overlap = (xmax - xmin) / span if span > 0 else 0.0

        if overlap < 0.05:
            # Логарифмируем только для отладки - не блокируем
            logger.debug(f"Малое перекрытие {overlap:.2%} для {sample.get('skin', '?')}/{sample.get('N', '?')}: "
                        f"x_al=[{x_al_pos.min():.4f}, {x_al_pos.max():.4f}], "
                        f"x_ref=[{x_ref_pos.min():.4f}, {x_ref_pos.max():.4f}]")

        F = misfit_shape(
            x_al, y_al, x_ref, y_ref,
            derivative_mode=self.derivative_mode,
            metric_type=self.metric_type,
        )

        # Если F inf из-за проблем с производной - пробуем вернуть хотя бы что-то
        if not np.isfinite(F):
            logger.debug(f"misfit_shape вернул {F} для {sample.get('skin', '?')}/{sample.get('N', '?')}")
            # Возвращаем с штрафом, но не inf - чтобы хоть что-то выбрать
            F = 1e10

        result = (F / max(overlap, 0.1), shift_x, stretch)
        self._sample_misfit_cache[cache_key] = result
        return result

    # ------------------------------------------------------------------
    # Шаги 1–4 (аналогичны предыдущей версии, но с _sample_misfit v2)
    # ------------------------------------------------------------------

    def select_skin(self, samples, h_known=None, beam=5):
        skin_scores = {}
        skin_scales = {}

        for s in samples:
            skin = s["skin"]
            F, sx, sy = self._sample_misfit(s)
            F_w = F / _h_weight(s["h"], h_known)
            if skin not in skin_scores or F_w < skin_scores[skin]:
                skin_scores[skin] = F_w
                skin_scales[skin] = (sx, sy)

        top_skins = select_top_k(skin_scores, beam)
        self._skin_scales = skin_scales

        logger.info(f"Шаг 1 — Skin. Проверено: {len(skin_scores)} значений (ВСЕ кривые)")
        # Логируем ВСЕ значения Skin (перебор всех кривых по форме)
        for sk in sorted(skin_scores.keys()):
            sx, sy = skin_scales[sk]
            logger.info(
                f"  Skin={sk:.3f} → misfit={skin_scores[sk]:.6f}, "
                f"scale_x={sx:.4f}, scale_y={sy:.4f}"
            )
        logger.info(f"Топ-{len(top_skins)} для дальнейшего отбора: {top_skins}")
        return top_skins, skin_scores

    def select_N(self, samples, top_skins, beam=5):
        relevant = [s for s in samples if s["skin"] in top_skins]
        sn_scores = {}
        sn_scales = {}

        for s in relevant:
            key = (s["skin"], s["N"])
            F, sx, sy = self._sample_misfit(s)
            if key not in sn_scores or F < sn_scores[key]:
                sn_scores[key] = F
                sn_scales[key] = (sx, sy)

        best_key = min(sn_scores, key=sn_scores.get)
        best_skin, best_N = best_key
        self._sn_scales = sn_scales

        logger.info(f"Шаг 2 — N. Проверено: {len(sn_scores)} комбинаций")
        for (sk, n), f in sorted(sn_scores.items(), key=lambda x: x[1])[:5]:
            logger.info(f"  Skin={sk:.3f}, N={n} → misfit={f:.6f}")
        return best_skin, best_N, sn_scores

    def select_aL(self, samples, skin, N, beam=5):
        relevant = [s for s in samples
                    if s["skin"] == skin and s["N"] == N]
        al_scores = {}

        for s in relevant:
            al = s["a/L"]
            F, _, _ = self._sample_misfit(s)
            if al not in al_scores or F < al_scores[al]:
                al_scores[al] = F

        top_aL = select_top_k(al_scores, beam)

        logger.info(
            f"Шаг 3 — a/L при Skin={skin:.3f}, N={N}. "
            f"Проверено: {len(al_scores)} значений"
        )
        for al in top_aL:
            logger.info(f"  a/L={al:.4f} → misfit={al_scores[al]:.6f}")
        return top_aL, al_scores

    def select_L(
        self,
        samples,
        skin,
        N,
        top_aL,
        xf_bounds,
    ):
        relevant = [s for s in samples
                    if s["skin"] == skin and s["N"] == N
                    and s["a/L"] in top_aL]

        L_min, L_max = xf_bounds
        L_dict = {}
        for s in relevant:
            L = s["L"]
            if not (L_min <= L <= L_max):
                continue
            L_dict.setdefault(L, []).append(s)

        L_values = sorted(L_dict.keys())
        if not L_values:
            return None, None, None, None, 1.0, 1.0, np.inf

        L_scores, L_best_s, L_best_sc = {}, {}, {}
        for L in L_values:
            best_F, best_s, best_sx, best_sy = np.inf, None, 1.0, 1.0
            first_s = None  # Запоминаем первый образец для fallback
            for s in L_dict[L]:
                if first_s is None:
                    first_s = s
                F, sx, sy = self._sample_misfit(s)
                if F < best_F:
                    best_F, best_s, best_sx, best_sy = F, s, sx, sy
            # Если best_s остался None (все вернули inf) - используем первый
            if best_s is None and first_s is not None:
                best_s = first_s
                logger.warning(f"L={L}: все образцы вернули inf, использую первый попавшийся")
            L_scores[L] = best_F
            L_best_s[L] = best_s
            L_best_sc[L] = (best_sx, best_sy)

        # Фильтруем L с валидными образцами
        valid_L = [L for L in L_values if L_best_s[L] is not None]
        if not valid_L:
            logger.error("Нет ни одного валидного L!")
            return None, None, None, None, 1.0, 1.0, np.inf
        
        sorted_L = sorted(valid_L, key=lambda L: L_scores[L])
        best_L = sorted_L[0]
        best_F = L_scores[best_L]
        best_sx, best_sy = L_best_sc[best_L]

        logger.info(f"Шаг 4 — L. Проверено: {len(L_values)} значений")
        for L in sorted_L[:5]:
            logger.info(f"  L={L:.2f} → misfit={L_scores[L]:.6f}")

        # Интерполяция между соседями
        best_idx = L_values.index(best_L)
        neighbours = []
        if best_idx > 0:
            nb = L_values[best_idx - 1]
            neighbours.append((nb, L_scores[nb], L_best_s[nb], L_best_sc[nb]))
        if best_idx < len(L_values) - 1:
            nb = L_values[best_idx + 1]
            neighbours.append((nb, L_scores[nb], L_best_s[nb], L_best_sc[nb]))

        if neighbours:
            L_nb, F_nb, s_nb, (sx_nb, sy_nb) = min(neighbours, key=lambda t: t[1])
            alpha = _choose_alpha(best_F, F_nb)

            if 0.0 < alpha < 1.0:
                x1 = L_best_s[best_L].get("x")
                y1 = L_best_s[best_L].get("y")
                x2 = s_nb.get("x")
                y2 = s_nb.get("y")

                xb = np.logspace(
                    np.log10(max(x1.min(), x2.min())),
                    np.log10(min(x1.max(), x2.max())), 300
                )
                yb = _blend_curves(_interp_curve(x1, y1, xb),
                                   _interp_curve(x2, y2, xb), alpha)

                x_al, y_al, sx_bl, sy_bl = align_fact_to_ref(
                    self._x_fact_raw, self._y_fact_raw, xb, yb
                )
                xmin = max(x_al[x_al > 0].min(), xb[xb > 0].min())
                xmax = min(x_al[x_al > 0].max(), xb[xb > 0].max())
                span = x_al[x_al > 0].max() - x_al[x_al > 0].min()
                overlap = (xmax - xmin) / span if span > 0 else 0.0
                F_bl = misfit_shape(x_al, y_al, xb, yb,
                                    derivative_mode=self.derivative_mode,
                                    metric_type=self.metric_type)
                F_bl = F_bl / max(overlap, 0.1)

                L_bl = (1.0 - alpha) * best_L + alpha * L_nb
                aL_bl = ((1.0 - alpha) * L_best_s[best_L]["a/L"]
                         + alpha * s_nb["a/L"])

                logger.info(
                    f"  Интерполяция L={best_L:.1f}+{L_nb:.1f}, "
                    f"alpha={alpha:.2f} → L={L_bl:.2f}, F={F_bl:.6f}"
                )

                if (
                    F_bl <= best_F
                    and L_min <= L_bl <= L_max
                ):
                    return L_bl, aL_bl, xb, yb, sx_bl, sy_bl, F_bl

        # Проверяем, что best_s существует
        if L_best_s[best_L] is None:
            logger.warning(f"Не найден валидный образец для L={best_L}")
            # Возвращаем None вместо падения
            return None, None, None, None, None, None, np.inf
        
        x_b = L_best_s[best_L].get("x")
        y_b = L_best_s[best_L].get("y")
        return best_L, L_best_s[best_L]["a/L"], x_b, y_b, best_sx, best_sy, best_F

    # ------------------------------------------------------------------
    # Шаг 5: аналитическое восстановление k и L
    # ------------------------------------------------------------------

    def recover_k_L(self, scale_x, scale_y, k_init, L_init, k_bounds, L_bounds):
        """
        Восстановление физических параметров из масштабных коэффициентов.

        Из формул X = k*f(...) и Y = g(...)/L:
            scale_x = X_ref_median / X_fact_median = k_real / k_init
            scale_y = Y_ref_median / Y_fact_median = L_init / L_real

            k_real = k_init * scale_x
            L_real = L_init / scale_y
        """
        k_real = float(np.clip(k_init * scale_x, k_bounds[0], k_bounds[1]))
        L_real = float(np.clip(
            L_init / scale_y if scale_y > 0 else L_init,
            L_bounds[0], L_bounds[1]
        ))
        logger.info(
            f"Шаг 5: scale_x={scale_x:.4f}, scale_y={scale_y:.4f} "
            f"→ k={k_real:.6f} мД, L={L_real:.4f} м"
        )
        return k_real, L_real

    # ------------------------------------------------------------------
    # Шаг 5: восстановление k из горизонтального сдвига по X
    # ------------------------------------------------------------------

    def recover_k(self, best_sample, k_ref=5.0, k_bounds=(1e-5, 100)):
        """
        Восстановление k из соотношения медиан X факта и референса.

        Физика:
            X = 0.00864 * k * h * |dP| / (mu * B * Q)
            X ∝ k при фиксированных статических параметрах.

            Библиотека посчитана при k_ref=5:
                X_ref = 0.00864 * k_ref * h * |dP| / (mu * B * Q)
                X_fact = 0.00864 * k_real * h * |dP| / (mu * B * Q)

            →  X_fact / X_ref = k_real / k_ref
            →  k_real = k_ref * median(X_fact) / median(X_ref)

        Медиана робастна к выбросам на краях кривой.
        """
        x_ref  = best_sample.get("x")
        x_ref  = x_ref[x_ref > 0]
        x_fact = self._x_fact_raw[self._x_fact_raw > 0]

        if len(x_ref) == 0 or len(x_fact) == 0:
            logger.warning("recover_k: нет положительных X, возвращаю k_ref")
            return k_ref

        med_fact = np.median(x_fact)
        med_ref  = np.median(x_ref)

        if med_ref == 0:
            logger.warning("recover_k: медиана X_ref = 0, возвращаю k_ref")
            return k_ref

        k_real = k_ref * (med_fact / med_ref)
        k_real = float(np.clip(k_real, k_bounds[0], k_bounds[1]))

        logger.info(
            f"Шаг 5 — k: median(X_fact)={med_fact:.4f}, "
            f"median(X_ref)={med_ref:.4f}, "
            f"k_ref={k_ref} → k_real={k_real:.6f} мД"
        )
        return k_real

    # ------------------------------------------------------------------
    # Главный метод
    # ------------------------------------------------------------------

    def solve(self, x_fact, y_fact,
              W_fixed=None, N_fixed=None, h_known=None,
              k_bounds=(1e-5, 10), xf_bounds=(1e-3, 100),
              beam=5):
        """
        Полный ступенчатый подбор.
        Параметры результата берутся напрямую из найденной кривой библиотеки —
        так же как Skin подбирается по форме, так же L, a/L, N из совпадения.
        k пока возвращается как None — восстановление через Y отдельным шагом.
        """
        logger.info("=" * 60)
        logger.info("НАЧАЛО ОПТИМИЗАЦИИ")
        logger.info(f"  W={W_fixed}, N={N_fixed}, h={h_known}")

        self._prepare(x_fact, y_fact)
        samples = self._filter_library(W_fixed, N_fixed)

        if not samples:
            raise ValueError(f"Библиотека пуста: W={W_fixed}, N={N_fixed}")

        logger.info("\n--- Шаг 1: Skin ---")
        top_skins, _ = self.select_skin(samples, h_known=h_known, beam=beam)

        if N_fixed is not None:
            best_skin, best_N = top_skins[0], N_fixed
            logger.info(f"\n--- Шаг 2: N зафиксирован={N_fixed} ---")
        else:
            logger.info("\n--- Шаг 2: N (подбор) ---")
            best_skin, best_N, _ = self.select_N(samples, top_skins, beam=beam)

        logger.info(f"  → Skin={best_skin:.3f}, N={best_N}")

        logger.info("\n--- Шаг 3: a/L ---")
        top_aL, _ = self.select_aL(samples, best_skin, best_N, beam=beam)

        logger.info("\n--- Шаг 4: L ---")
        best_L, best_aL, x_ref_f, y_ref_f, _, _, misfit_f = self.select_L(
            samples, best_skin, best_N, top_aL
        )

        if x_ref_f is None:
            # Пытаемся найти хоть какой-то образец из библиотеки
            logger.warning("x_ref_f is None - пробуем получить кривую из выборки")
            # Найдём первый попавшийся образец для данных skin/N
            for s in samples:
                if s.get('skin') == best_skin and s.get('N') == best_N:
                    x_ref_f = s["dynamic"]["X"].values.astype(float)
                    y_ref_f = s["dynamic"]["Y"].values.astype(float)
                    best_L = s.get('L', 50.0)
                    best_aL = s.get('a/L', 1.0)
                    misfit_f = np.inf
                    logger.warning(f"Использую fallback: L={best_L}, a/L={best_aL}")
                    break
            if x_ref_f is None:
                raise ValueError("Не удалось подобрать L - нет подходящих образцов в библиотеке.")

        # Шаг 5: k из горизонтального сдвига X
        logger.info("\n--- Шаг 5: k ---")
        best_sample_for_k = None
        for s in samples:
            if (s.get("skin") == best_skin
                    and s.get("N") == best_N
                    and s.get("L") == best_L
                    and s.get("a/L") == best_aL):
                best_sample_for_k = s
                break
        # Fallback: если точного совпадения нет (был blend), берём ближайший по L
        if best_sample_for_k is None:
            candidates = [s for s in samples
                          if s.get("skin") == best_skin and s.get("N") == best_N]
            if candidates:
                best_sample_for_k = min(
                    candidates,
                    key=lambda s: abs(s.get("L", 0) - best_L)
                )

        k_opt = self.recover_k(
            best_sample_for_k,
            k_ref=5.0,
            k_bounds=k_bounds,
        ) if best_sample_for_k is not None else None

        # Получаем дополнительные параметры из лучшей кривой
        best_h = None
        best_W = None
        for s in samples:
            if s.get('skin') == best_skin and s.get('N') == best_N:
                if s.get('L') == best_L and s.get('a/L') == best_aL:
                    best_h = s.get('h')
                    best_W = s.get('W')
                    break

        logger.info("\n" + "=" * 60)
        logger.info("РЕЗУЛЬТАТ (параметры найденной кривой):")
        logger.info(f"  Skin (S)   = {best_skin:.4f}")
        logger.info(f"  N (число трещин) = {best_N}")
        logger.info(f"  L (полудлина) = {best_L:.4f} м")
        logger.info(f"  a/L         = {best_aL:.4f}")
        logger.info(f"  k           = {k_opt:.6f} мД" if k_opt is not None else "  k           = N/A")
        if best_h is not None:
            logger.info(f"  h (толщина пласта) = {best_h:.4f} м")
        if best_W is not None:
            logger.info(f"  W (ширина трещины) = {best_W:.4f} м")
        logger.info(f"  Misfit     = {misfit_f:.6f}")
        logger.info("=" * 60)

        return {
            "skin":  best_skin,
            "N":     best_N,
            "L":     best_L,
            "aL":    best_aL,
            "h":     best_h,
            "W":     best_W,
            "params": {"k": k_opt, "xf": best_L},
            "misfit": misfit_f,
            "x_ref_matched": x_ref_f,
            "y_ref_matched": y_ref_f,
        }
    
    def solve_top_candidates(
        self,
        x_fact,
        y_fact,
        W_fixed=None,
        N_fixed=None,
        h_known=None,
        k_bounds=(1e-5,100),
        xf_bounds=(1e-3,100),
        beam=5
    ):
        """
        Возвращает top beam решений вместо одного.
        """

        self._prepare(x_fact,y_fact)

        samples=self._filter_library(
            W_fixed,
            N_fixed
        )

        top_skins,_ = self.select_skin(
            samples,
            h_known=h_known,
            beam=beam
        )

        results=[]

        for skin in top_skins:

            if N_fixed is not None:
                N= N_fixed
            else:
                _,N,_ = self.select_N(
                    samples,
                    [skin],
                    beam=beam
                )

            top_aL,_ = self.select_aL(
                samples,
                skin,
                N,
                beam=beam
            )

            L,aL,_,_,_,_,misfit = self.select_L(
                samples,
                skin,
                N,
                top_aL,
                xf_bounds=xf_bounds,
            )

            if L is None:
                continue


            best_sample=None

            for s in samples:
                if (
                s["skin"]==skin
                and s["N"]==N
                ):
                    best_sample=s
                    break


            k=self.recover_k(
                best_sample,
                k_ref=5.0,
                k_bounds=k_bounds
            )

            results.append(
                {
                "skin":skin,
                "N":N,
                "L":L,
                "aL":aL,
                "k":k,
                "misfit":misfit
                }
            )


        results.sort(
            key=lambda x:x["misfit"]
        )

        return results[:beam]
