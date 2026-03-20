import numpy as np
import logging
from scipy.optimize import minimize
from scipy.interpolate import interp1d

from .misfit import misfit_shape
from .beam_search import select_top_k
from .interpolation import interpolate_to_grid

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────

def _interp_curve(x, y, x_grid):
    """Интерполяция кривой (x, y) на x_grid. Возвращает y или nan-массив."""
    try:
        f = interp1d(x, y, bounds_error=False, fill_value=np.nan)
        return f(x_grid)
    except Exception:
        return np.full_like(x_grid, np.nan)


def _blend_curves(y1, y2, alpha):
    """
    Линейная смесь двух кривых на одной сетке.
    alpha=0.0 → y1, alpha=1.0 → y2.
    nan-точки одной кривой заполняются из другой.
    """
    out = alpha * y2 + (1.0 - alpha) * y1
    # там где y1 nan но y2 есть — берём y2 и наоборот
    out = np.where(np.isnan(y1), y2, out)
    out = np.where(np.isnan(y2), y1, out)
    return out


def _choose_alpha(f1, f2):
    """
    Определяет коэффициент смешивания двух кривых по их ошибкам.

    Правило:
      |f1 - f2| / max(f1, f2) < 0.30  → берём ближайшую (alpha=0 или 1)
      0.30 – 0.40                      → линейная интерполяция alpha
      > 0.40                            → середина (alpha=0.5)

    Возвращает alpha: 0.0 = только f1, 1.0 = только f2.
    """
    if not (np.isfinite(f1) and np.isfinite(f2)):
        return 0.0 if np.isfinite(f1) else 1.0

    denom = max(f1, f2)
    if denom == 0:
        return 0.0

    rel = abs(f1 - f2) / denom

    if rel < 0.30:
        # берём ближайшую
        return 0.0 if f1 <= f2 else 1.0
    elif rel > 0.40:
        # берём середину
        return 0.5
    else:
        # линейная интерполяция: rel=0.30 → alpha=0, rel=0.40 → alpha=0.5
        t = (rel - 0.30) / 0.10          # 0..1
        return t * 0.5


def _h_weight(h_sample, h_known):
    """
    Вес образца по близости h к известному значению.
    Допуск ±50% от h_known.
    weight = 1 / (1 + |Δh| / h_known), диапазон (0, 1].
    При |Δh| > 0.5 * h_known вес < 0.67 — образец депrioritized но не исключён.
    """
    if h_known is None or h_known <= 0:
        return 1.0
    return 1.0 / (1.0 + abs(h_sample - h_known) / h_known)


def _weighted_misfit(F, h_sample, h_known):
    """Misfit взвешенный по h-близости (меньше = лучше)."""
    w = _h_weight(h_sample, h_known)
    # weight < 1 → штраф: делим на weight чтобы увеличить misfit при плохом h
    return F / w if w > 0 else np.inf


# ─────────────────────────────────────────────────────────────
# ReservoirSolver
# ─────────────────────────────────────────────────────────────

class ReservoirSolver:
    """
    Ступенчатый подбор параметров трещины по совпадению формы кривой dY/dX.

    Алгоритм:
      Шаг 0: фильтрация библиотеки по W (жёсткая) + N если задан
      Шаг 1: select_skin   — перебор Skin, h-взвешивание, beam search
      Шаг 2: select_N      — если N не задан, перебор N по top-beam Skin
      Шаг 3: select_aL     — перебор a/L по фиксированным (Skin, N)
      Шаг 4: select_L      — перебор L, интерполяция между соседями
      Шаг 5: recover_k     — аналитически из уровня Y (без оптимизации)

    Параметры результата — это параметры найденной кривой,
    не регрессия чисел. k — единственный аналитический результат.
    """

    def __init__(self, skin_library, progress_callback=None):
        self.skin_library = skin_library
        self.progress_callback = progress_callback

        # Фиксированные режимы: линейная производная для безразмерных X-Y.
        # loglog избыточен — X и Y уже безразмерны, двойная трансформация
        # давит детали переходных режимов.
        self.derivative_mode = "linear"
        self.metric_type = "integral"

        # Кэш подготовленной входной кривой
        self._x_grid = None
        self._y_fact = None

    # ------------------------------------------------------------------
    # Шаг 0: подготовка и фильтрация
    # ------------------------------------------------------------------

    def _prepare(self, x_fact, y_fact, n_points=200):
        """
        Интерполирует входную кривую на равномерную лог-сетку.
        Результат кэшируется — повторные вызовы бесплатны.
        """
        mask = (x_fact > 0) & (y_fact > 0) & np.isfinite(x_fact) & np.isfinite(y_fact)
        x_fact = x_fact[mask]
        y_fact = y_fact[mask]

        x_grid = np.logspace(
            np.log10(x_fact.min()),
            np.log10(x_fact.max()),
            n_points
        )
        y_interp = _interp_curve(x_fact, y_fact, x_grid)

        valid = ~np.isnan(y_interp)
        self._x_grid = x_grid[valid]
        self._y_fact = y_interp[valid]

        logger.info(f"Подготовка: {len(x_fact)} → {len(self._x_grid)} точек, "
                    f"X=[{self._x_grid[0]:.4f}, {self._x_grid[-1]:.4f}]")

    def _filter_library(self, W_fixed, N_fixed=None, ignore_W=False):
        """
        Шаг 0: жёсткая фильтрация по W, опциональная по N.

        Args:
            W_fixed: значение W для фильтрации
            N_fixed: значение N для фильтрации (None = не фильтровать)
            ignore_W: если True — игнорировать фильтр по W (использовать все образцы)

        Returns:
            Список образцов (samples) прошедших фильтр.
            Каждый образец — dict с ключами: dynamic, h, N, W, L, a/L.
        """
        result = []
        for skin_val, samples in self.skin_library.items():
            for s in samples:
                # жёсткий фильтр по W (если не игнорируем)
                if not ignore_W and s["W"] != W_fixed:
                    continue
                # опциональный фильтр по N
                if N_fixed is not None and s["N"] != N_fixed:
                    continue
                # добавляем skin в сам образец для удобства
                result.append({**s, "skin": skin_val})

        filter_desc = "W=any" if ignore_W else f"W={W_fixed}"
        logger.info(f"После фильтрации {filter_desc}"
                    + (f", N={N_fixed}" if N_fixed is not None else "")
                    + f": {len(result)} образцов")
        return result

    # ------------------------------------------------------------------
    # Базовый misfit образца относительно кэшированного факта
    # ------------------------------------------------------------------

    def _sample_misfit(self, sample):
        """
        Вычисляет misfit_shape между кэшированной фактической кривой
        и кривой из образца.

        Сравниваем dY/dX (linear) с нормировкой по медиане.
        Нормировка убирает влияние масштаба Y (k неизвестен) —
        сравниваем только форму.
        """
        x_ref = sample["dynamic"]["X"].values.astype(float)
        y_ref = sample["dynamic"]["Y"].values.astype(float)
        return misfit_shape(
            self._x_grid, self._y_fact,
            x_ref, y_ref,
            derivative_mode=self.derivative_mode,
            metric_type=self.metric_type,
        )

    def _sample_misfit_xy(self, x_ref, y_ref):
        """То же, но принимает массивы напрямую (для blended кривых)."""
        return misfit_shape(
            self._x_grid, self._y_fact,
            x_ref, y_ref,
            derivative_mode=self.derivative_mode,
            metric_type=self.metric_type,
        )

    # ------------------------------------------------------------------
    # Шаг 1: select_skin
    # ------------------------------------------------------------------

    def select_skin(self, samples, h_known=None, beam=3):
        """
        Перебор всех Skin в отфильтрованных образцах.

        Для каждого Skin: считаем misfit по ВСЕМ образцам с данным Skin
        (не только медианному — иначе случайно фиксируем L, a/L до подбора).
        h_known задаёт мягкий приоритет через взвешивание misfit.
        Берём минимальный взвешенный misfit как score Skin.

        Возвращает (top_skins, scores_dict).
        """
        skin_scores = {}

        for s in samples:
            skin = s["skin"]
            F = self._sample_misfit(s)
            F_w = _weighted_misfit(F, s["h"], h_known)

            if skin not in skin_scores or F_w < skin_scores[skin]:
                skin_scores[skin] = F_w

        top_skins = select_top_k(skin_scores, beam)

        logger.info(f"Шаг 1 — Skin. Проверено: {len(skin_scores)} значений")
        for sk in top_skins:
            logger.info(f"  Skin={sk:.3f} → misfit={skin_scores[sk]:.6f}")

        return top_skins, skin_scores

    # ------------------------------------------------------------------
    # Шаг 2: select_N  (только если N не задан)
    # ------------------------------------------------------------------

    def select_N(self, samples, top_skins, beam=3):
        """
        Перебор N для top_skins.

        Аналогично select_skin: для каждой пары (Skin, N) берём минимальный
        misfit по всем образцам с этой парой (варьируем L, a/L свободно).

        Возвращает (best_skin, best_N, scores_dict).
        """
        # фильтруем образцы по top_skins
        relevant = [s for s in samples if s["skin"] in top_skins]

        sn_scores = {}
        for s in relevant:
            key = (s["skin"], s["N"])
            F = self._sample_misfit(s)
            if key not in sn_scores or F < sn_scores[key]:
                sn_scores[key] = F

        best_key = min(sn_scores, key=sn_scores.get)
        best_skin, best_N = best_key

        logger.info(f"Шаг 2 — N. Проверено: {len(sn_scores)} комбинаций (Skin, N)")
        for (sk, n), f in sorted(sn_scores.items(), key=lambda x: x[1])[:5]:
            logger.info(f"  Skin={sk:.3f}, N={n} → misfit={f:.6f}")

        return best_skin, best_N, sn_scores

    # ------------------------------------------------------------------
    # Шаг 3: select_aL
    # ------------------------------------------------------------------

    def select_aL(self, samples, skin, N, beam=3):
        """
        Перебор a/L при зафиксированных (Skin, N).

        Для каждого a/L: минимальный misfit по всем L (L варьируется свободно).
        Возвращает (top_aL_values, scores_dict).
        """
        relevant = [s for s in samples
                    if s["skin"] == skin and s["N"] == N]

        al_scores = {}
        for s in relevant:
            al = s["a/L"]
            F = self._sample_misfit(s)
            if al not in al_scores or F < al_scores[al]:
                al_scores[al] = F

        top_aL = select_top_k(al_scores, beam)

        logger.info(f"Шаг 3 — a/L при Skin={skin:.3f}, N={N}. "
                    f"Проверено: {len(al_scores)} значений")
        for al in top_aL:
            logger.info(f"  a/L={al:.4f} → misfit={al_scores[al]:.6f}")

        return top_aL, al_scores

    # ------------------------------------------------------------------
    # Шаг 4: select_L  с интерполяцией между соседями
    # ------------------------------------------------------------------

    def select_L(self, samples, skin, N, top_aL):
        """
        Перебор L при зафиксированных (Skin, N, a/L из top_aL).

        Для каждого L усредняем по top_aL (или берём лучшее).
        Затем проверяем двух соседей по L и применяем правило интерполяции:
          - разность ошибок < 30%  → берём ближайшую кривую
          - разность 30–40%        → линейная интерполяция alpha
          - разность > 40%         → середина (alpha=0.5)

        Возвращает (best_L, best_aL, y_ref_final, score_final).
        """
        relevant = [s for s in samples
                    if s["skin"] == skin and s["N"] == N
                    and s["a/L"] in top_aL]

        # Группируем по L
        L_dict = {}   # L → список образцов
        for s in relevant:
            L = s["L"]
            L_dict.setdefault(L, []).append(s)

        L_values = sorted(L_dict.keys())

        if not L_values:
            logger.warning("Нет образцов для select_L")
            return None, None, None, np.inf

        # Для каждого L: минимальный misfit по top_aL образцам
        L_scores = {}   # L → (misfit, best_sample)
        for L in L_values:
            best_F = np.inf
            best_s = None
            for s in L_dict[L]:
                F = self._sample_misfit(s)
                if F < best_F:
                    best_F = F
                    best_s = s
            L_scores[L] = (best_F, best_s)

        # Сортируем по misfit
        sorted_L = sorted(L_scores.keys(), key=lambda L: L_scores[L][0])
        best_L = sorted_L[0]
        best_F, best_s = L_scores[best_L]

        # Проверяем, что нашли хоть какой-то образец
        if best_s is None or np.isinf(best_F):
            logger.warning(
                f"Не удалось подобрать кривую: все misfit бесконечны. "
                f"Проверьте диапазон X данных."
            )
            return None, None, None, np.inf

        logger.info(f"Шаг 4 — L при Skin={skin:.3f}, N={best_s['N']}. "
                    f"Проверено: {len(L_values)} значений L")
        for L in sorted_L[:5]:
            f, _ = L_scores[L]
            logger.info(f"  L={L:.2f} → misfit={f:.6f}")

        # --- Интерполяция между соседями ---
        best_idx = L_values.index(best_L)

        # Проверяем двух соседей
        neighbour_candidates = []
        if best_idx > 0:
            L_nb = L_values[best_idx - 1]
            F_nb, s_nb = L_scores[L_nb]
            neighbour_candidates.append((L_nb, F_nb, s_nb))
        if best_idx < len(L_values) - 1:
            L_nb = L_values[best_idx + 1]
            F_nb, s_nb = L_scores[L_nb]
            neighbour_candidates.append((L_nb, F_nb, s_nb))

        # Берём ближайшего соседа по misfit
        if neighbour_candidates:
            L_nb, F_nb, s_nb = min(neighbour_candidates, key=lambda t: t[1])
            alpha = _choose_alpha(best_F, F_nb)

            if 0.0 < alpha < 1.0:
                # Смешиваем кривые на общей сетке
                x_ref1 = best_s["dynamic"]["X"].values.astype(float)
                y_ref1 = best_s["dynamic"]["Y"].values.astype(float)
                x_ref2 = s_nb["dynamic"]["X"].values.astype(float)
                y_ref2 = s_nb["dynamic"]["Y"].values.astype(float)

                # Общая сетка — объединение диапазонов
                x_min = max(x_ref1.min(), x_ref2.min())
                x_max = min(x_ref1.max(), x_ref2.max())
                x_blend = np.logspace(np.log10(x_min), np.log10(x_max), 300)

                y1_on_blend = _interp_curve(x_ref1, y_ref1, x_blend)
                y2_on_blend = _interp_curve(x_ref2, y_ref2, x_blend)
                y_blend = _blend_curves(y1_on_blend, y2_on_blend, alpha)

                F_blend = self._sample_misfit_xy(x_blend, y_blend)

                # Интерполированный L
                L_blend = (1.0 - alpha) * best_L + alpha * L_nb

                logger.info(f"  Интерполяция: L={best_L:.2f}(F={best_F:.4f}) + "
                            f"L={L_nb:.2f}(F={F_nb:.4f}), alpha={alpha:.2f} "
                            f"→ L_blend={L_blend:.2f}, F_blend={F_blend:.6f}")

                if F_blend < best_F:
                    return (L_blend,
                            (1.0 - alpha) * best_s["a/L"] + alpha * s_nb["a/L"],
                            y_blend,
                            F_blend)
                # иначе интерполяция не улучшила — возвращаем лучшую
            else:
                logger.info(f"  Сосед L={L_nb:.2f} отклонён (alpha={alpha:.2f}), "
                            f"берём L={best_L:.2f}")

        # Возвращаем лучшую без интерполяции
        x_best = best_s["dynamic"]["X"].values.astype(float)
        y_best = best_s["dynamic"]["Y"].values.astype(float)
        return best_L, best_s["a/L"], y_best, best_F

    # ------------------------------------------------------------------
    # Шаг 5: recover_k  (аналитика)
    # ------------------------------------------------------------------

    def recover_k(self, x_ref, y_ref):
        """
        Аналитическое восстановление k из уровня Y.

        После того как форма кривой (Skin, N, L, a/L) найдена,
        k — это просто вертикальный сдвиг в log-пространстве:

            log Y_fact ≈ log k + log Y_ref(x)
            log k = median( log Y_fact_aligned - log Y_ref_aligned )

        Медиана робастна к выбросам на краях кривой.
        Нет итераций, нет оптимизации.

        Для корректного сравнения сначала выравниваем обе кривые
        на общую сетку пересечения диапазонов.
        """
        x_min = max(self._x_grid.min(), x_ref[x_ref > 0].min())
        x_max = min(self._x_grid.max(), x_ref[x_ref > 0].max())

        if x_min >= x_max:
            logger.warning("recover_k: нет перекрытия X, k=1.0")
            return 1.0

        x_common = np.logspace(np.log10(x_min), np.log10(x_max), 200)

        yf = _interp_curve(self._x_grid, self._y_fact, x_common)
        yr = _interp_curve(x_ref, y_ref, x_common)

        mask = (yf > 0) & (yr > 0) & np.isfinite(yf) & np.isfinite(yr)
        if mask.sum() < 10:
            logger.warning("recover_k: мало точек для оценки k, k=1.0")
            return 1.0

        log_k = np.median(np.log(yf[mask]) - np.log(yr[mask]))
        k = float(np.exp(log_k))

        logger.info(f"Шаг 5 — k: log_k={log_k:.4f} → k={k:.6f}")
        return k

    # ------------------------------------------------------------------
    # Главный метод
    # ------------------------------------------------------------------

    def solve(self, x_fact, y_fact,
              W_fixed=None,
              N_fixed=None,
              h_known=None,
              k_bounds=(1e-5, 10),
              xf_bounds=(1e-3, 100),
              beam=3):
        """
        Полный ступенчатый подбор.

        Фоллбэк-логика: если W_fixed=0/None или нет образцов с указанным W,
        то W игнорируется и подбор идёт только по форме кривой (skin, N, L, a/L).

        Args:
            x_fact, y_fact  : безразмерные входные кривые
            W_fixed         : длина скважины (если 0 или None — игнорируется)
            N_fixed         : число трещин (если None — подбирается на шаге 2)
            h_known         : толщина пласта (мягкий приоритет, ±50%)
            k_bounds        : границы k для clip результата
            xf_bounds       : границы L для clip результата
            beam            : ширина beam search

        Returns:
            dict: skin, N, L, aL, k, misfit, y_ref_matched
        """
        logger.info("=" * 60)
        logger.info("НАЧАЛО ОПТИМИЗАЦИИ (ступенчатый подбор кривой)")
        logger.info("=" * 60)
        logger.info(f"  W={W_fixed}, N_fixed={N_fixed}, h_known={h_known}")
        logger.info(f"  Точек: {len(x_fact)}, "
                    f"X=[{np.min(x_fact):.4f}, {np.max(x_fact):.4f}], "
                    f"Y=[{np.min(y_fact):.4f}, {np.max(y_fact):.4f}]")

        # Шаг 0
        logger.info("\n--- Шаг 0: подготовка + фильтрация ---")
        self._prepare(x_fact, y_fact)
        
        # Определяем, нужно ли игнорировать W:
        # - если W_fixed = 0 или None → игнорируем W
        # - если после фильтрации по W нет образцов → fallback без W
        ignore_W = (W_fixed is None or W_fixed == 0)
        
        samples = self._filter_library(W_fixed, N_fixed, ignore_W=ignore_W)

        # Fallback: если нет образцов с указанным W, пробуем без фильтра по W
        if not samples and not ignore_W:
            logger.warning(
                f"Нет образцов с W={W_fixed}. "
                f"Переход к подбору по форме (игнорируем W)"
            )
            samples = self._filter_library(W_fixed, N_fixed, ignore_W=True)

        if not samples:
            raise ValueError(
                f"Библиотека пуста после всех фильтраций. "
                f"Проверьте наличие референсных кривых в базе."
            )

        # Шаг 1: Skin
        logger.info("\n--- Шаг 1: Skin ---")
        top_skins, skin_scores = self.select_skin(samples, h_known=h_known, beam=beam)

        # Шаг 2: N (если не задан)
        if N_fixed is not None:
            best_skin = top_skins[0]
            best_N = N_fixed
            logger.info(f"\n--- Шаг 2: N зафиксирован = {N_fixed} ---")
        else:
            logger.info("\n--- Шаг 2: N (подбор) ---")
            best_skin, best_N, _ = self.select_N(samples, top_skins, beam=beam)

        logger.info(f"  → Skin={best_skin:.3f}, N={best_N}")

        # Шаг 3: a/L
        logger.info("\n--- Шаг 3: a/L ---")
        top_aL, _ = self.select_aL(samples, best_skin, best_N, beam=beam)

        # Шаг 4: L (с интерполяцией)
        logger.info("\n--- Шаг 4: L ---")
        best_L, best_aL, y_ref_final, misfit_final = self.select_L(
            samples, best_skin, best_N, top_aL
        )

        if y_ref_final is None or np.isinf(misfit_final):
            raise ValueError(
                f"Не удалось подобрать кривую: все образцы имеют бесконечную ошибку. "
                f"Возможно, диапазон X данных не перекрывается с референсными кривыми."
            )

        # Шаг 5: k
        logger.info("\n--- Шаг 5: k (аналитика) ---")

        # Определяем x_ref для recover_k:
        # если была интерполяция между кривыми, y_ref_final уже на blend-сетке,
        # используем self._x_grid как приближение
        relevant_L = [s for s in samples
                      if s["skin"] == best_skin and s["N"] == best_N
                      and abs(s["L"] - best_L) < 1e-6]
        if relevant_L:
            x_ref_for_k = relevant_L[0]["dynamic"]["X"].values.astype(float)
            y_ref_for_k = relevant_L[0]["dynamic"]["Y"].values.astype(float)
        else:
            # интерполированная кривая — используем self._x_grid
            x_ref_for_k = self._x_grid
            y_ref_for_k = y_ref_final

        k_opt = self.recover_k(x_ref_for_k, y_ref_for_k)
        k_opt = float(np.clip(k_opt, k_bounds[0], k_bounds[1]))

        logger.info("\n" + "=" * 60)
        logger.info("РЕЗУЛЬТАТ:")
        logger.info(f"  Skin  = {best_skin:.4f}")
        logger.info(f"  N     = {best_N}")
        logger.info(f"  L     = {best_L:.4f} м")
        logger.info(f"  a/L   = {best_aL:.4f}")
        logger.info(f"  k     = {k_opt:.6f} мД")
        logger.info(f"  misfit= {misfit_final:.6f}")
        logger.info("=" * 60)

        return {
            "skin":    best_skin,
            "N":       best_N,
            "L":       best_L,
            "aL":      best_aL,
            "params":  {"k": k_opt, "xf": best_L},
            "misfit":  misfit_final,
            "y_ref_matched": y_ref_final,
        }
