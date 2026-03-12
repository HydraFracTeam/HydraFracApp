import numpy as np
import logging

from .misfit import misfit
from .beam_search import select_top_k
from .bayes_opt import bayesian_fit
from .interpolation import interpolate_input_curve

logger = logging.getLogger(__name__)


class ReservoirSolver:

    def __init__(self, skin_library, progress_callback=None):

        self.skin_library = skin_library
        self.progress_callback = progress_callback

        self.derivative_modes = ["linear", "loglog"]
        self.metric_types = ["L2", "L1", "integral"]
        
        # Кэш для интерполированной входной кривой
        self._x_interp = None
        self._y_interp = None
        self._x_fact_orig = None
        self._y_fact_orig = None

    # -----------------------------
    # INPUT CURVE PREPARATION
    # -----------------------------
    
    def _prepare_input_curve(self, x_fact, y_fact, target_grid=None):
        """
        Однократная подготовка входной кривой.
        
        Интерполирует входную кривую на стандартную сетку (логарифмическую).
        Результат сохраняется для повторного использования.
        
        Args:
            x_fact: X координаты входной кривой
            y_fact: Y координаты входной кривой
            target_grid: Целевая сетка (если None, создается логарифмическая)
            
        Returns:
            x_grid, y_interp: Интерполированная кривая
        """
        x_fact = np.asarray(x_fact)
        y_fact = np.asarray(y_fact)
        
        # Проверяем, нужна ли повторная интерполяция
        if (self._x_fact_orig is not None and 
            np.array_equal(x_fact, self._x_fact_orig) and
            self._x_interp is not None):
            logger.debug("Используем кэшированную интерполяцию")
            return self._x_interp, self._y_interp
        
        # Создаем стандартную логарифмическую сетку
        if target_grid is None:
            x_min = np.max([np.min(x_fact), 1e-10])  # Избегаем нуля
            x_max = np.max(x_fact)
            x_grid = np.logspace(np.log10(x_min), np.log10(x_max), 200)
        else:
            x_grid = target_grid
        
        # Интерполируем входную кривую на сетку
        try:
            y_interp = interpolate_input_curve(x_fact, y_fact, x_grid)
            
            # Фильтруем nan
            valid_mask = ~np.isnan(y_interp)
            if np.sum(valid_mask) < 10:
                logger.warning("Мало точек после интерполяции, используем оригинальную сетку")
                return x_fact, y_fact
            
            x_grid = x_grid[valid_mask]
            y_interp = y_interp[valid_mask]
            
        except Exception as e:
            logger.warning(f"Ошибка интерполяции: {e}, используем оригинальную сетку")
            return x_fact, y_fact
        
        # Сохраняем для кэширования
        self._x_fact_orig = x_fact.copy()
        self._y_fact_orig = y_fact.copy()
        self._x_interp = x_grid
        self._y_interp = y_interp
        
        logger.info(f"Интерполяция выполнена: {len(x_fact)} -> {len(x_grid)} точек")
        logger.info(f"  Диапазон X: [{x_grid[0]:.6f}, {x_grid[-1]:.6f}]")
        
        return x_grid, y_interp

    # -----------------------------
    # ENSEMBLE MISFIT
    # -----------------------------

    def ensemble_misfit(self, x_ref, y_ref):
        """
        Расчет невязки между интерполированной фактической и референсной кривыми.
        
        Использует предварительно интерполированную входную кривую (self._x_interp, self._y_interp).
        Референсная кривая интерполируется на ту же сетку.
        """
        if self._x_interp is None or self._y_interp is None:
            raise ValueError("Входная кривая не подготовлена. Вызовите _prepare_input_curve()")
        
        scores = []
        
        # НОРМАЛИЗАЦИЯ: приводим обе кривые к диапазону [0, 1]
        # Это решает проблему несоответствия масштабов X-Y между фактом и референсом
        x_interp_norm = (self._x_interp - np.min(self._x_interp)) / (np.max(self._x_interp) - np.min(self._x_interp))
        y_interp_norm = (self._y_interp - np.min(self._y_interp)) / (np.max(self._y_interp) - np.min(self._y_interp))
        
        x_ref_norm = (x_ref - np.min(x_ref)) / (np.max(x_ref) - np.min(x_ref))
        y_ref_norm = (y_ref - np.min(y_ref)) / (np.max(y_ref) - np.min(y_ref))
        
        # Интерполируем нормализованный референс на сетку нормализованной входной кривой
        try:
            y_ref_interp = interpolate_input_curve(x_ref_norm, y_ref_norm, x_interp_norm)
            
            # Фильтруем nan
            valid_mask = ~np.isnan(y_ref_interp)
            if np.sum(valid_mask) < 10:
                logger.debug(f"  Мало точек после интерполяции референса: {np.sum(valid_mask)}")
                return np.inf
            
            x_common = x_interp_norm[valid_mask]
            y_fact_common = y_interp_norm[valid_mask]
            y_ref_common = y_ref_interp[valid_mask]
            
        except ValueError as e:
            logger.debug(f"  Ошибка интерполяции референса: {e}")
            return np.inf

        for d in self.derivative_modes:
            for m in self.metric_types:

                F = misfit(
                    x_common, y_fact_common,
                    x_common, y_ref_common,
                    d, m,
                    200
                )

                scores.append(F)

        return np.median(scores)

    # -----------------------------
    # STEP 1 — SKIN
    # -----------------------------

    def select_skin(self, beam=3):

        scores = {}

        for skin, samples in self.skin_library.items():

            best = np.inf

            for sample in samples:

                x_ref = sample["dynamic"]["X"].values
                y_ref = sample["dynamic"]["Y"].values

                F = self.ensemble_misfit(x_ref, y_ref)

                best = min(best, F)

            scores[skin] = best

        return select_top_k(scores, beam), scores

    # -----------------------------
    # STEP 2 — N
    # -----------------------------

    def select_N(self, skins):

        scores = {}

        for skin in skins:

            for sample in self.skin_library[skin]:

                N = sample["N"]

                x_ref = sample["dynamic"]["X"].values
                y_ref = sample["dynamic"]["Y"].values

                F = self.ensemble_misfit(x_ref, y_ref)

                scores[(skin, N)] = F

        best = min(scores, key=scores.get)

        return best, scores

    # -----------------------------
    # STEP 3 — BAYES OPT
    # -----------------------------

    def optimize_continuous(self, sample, k_bounds=(1e-5, 10), xf_bounds=(1e-3, 100)):

        x_ref = sample["dynamic"]["X"].values
        y_ref = sample["dynamic"]["Y"].values
        
        logger.info(f"  Оптимизация непрерывных параметров:")
        logger.info(f"    Границы: k in [{k_bounds[0]:.6f}, {k_bounds[1]:.6f}], xf in [{xf_bounds[0]:.4f}, {xf_bounds[1]:.4f}]")
        
        # Нормализуем референс для сравнения (масштаб [0, 1])
        x_ref_norm = (x_ref - np.min(x_ref)) / (np.max(x_ref) - np.min(x_ref))
        y_ref_norm = (y_ref - np.min(y_ref)) / (np.max(y_ref) - np.min(y_ref))

        def objective(params):
            k, xf = params

            # Масштабируем референсную кривую по Y с помощью k
            # xf используется для дополнительного масштабирования формы кривой
            # Применяем нелинейное преобразование для учета влияния xf
            y_mod = y_ref_norm * k * (1 + 0.1 * np.log10(xf + 1))

            # Считаем ошибку (ensemble_misfit теперь использует внутреннюю нормализацию)
            error = self.ensemble_misfit(x_ref, y_ref)
            
            return error

        bounds = {
            "k": k_bounds,
            "xf": xf_bounds
        }
        
        # Progress callback for Bayes opt
        def bayes_progress(trial_num, params, value, best_value, best_params):
            if self.progress_callback:
                self.progress_callback("bayes", trial_num, params, value, best_value, best_params)
            
            # Log trial details
            status = "✓" if value < best_value else " "
            if np.isinf(value):
                logger.info(f"    Проба {trial_num:3d}: k={params['k']:.6f}, xf={params['xf']:.6f} -> ОШИБКА=inf (диапазоны не пересекаются)")
            else:
                logger.info(f"    Проба {trial_num:3d}: k={params['k']:.6f}, xf={params['xf']:.6f} -> ОШИБКА={value:.6f} [{status} ЛУЧШАЯ={best_value:.6f}]")

        params, score = bayesian_fit(objective, bounds, progress_callback=bayes_progress)

        return params, score

    # -----------------------------
    # MAIN SOLVER
    # -----------------------------

    def solve(self, x_fact, y_fact, k_bounds=(1e-5, 10), xf_bounds=(1e-3, 100)):
        
        logger.info("=" * 60)
        logger.info("НАЧАЛО ОПТИМИЗАЦИИ")
        logger.info("=" * 60)
        logger.info(f"Входные данные: {len(x_fact)} точек")
        logger.info(f"Диапазон X фактических: [{np.min(x_fact):.6f}, {np.max(x_fact):.6f}]")
        logger.info(f"Диапазон Y фактических: [{np.min(y_fact):.6f}, {np.max(y_fact):.6f}]")
        
        # ШАГ 0: Подготовка входной кривой (однократная интерполяция)
        logger.info("\n--- ШАГ 0: Подготовка входной кривой (интерполяция) ---")
        self._prepare_input_curve(x_fact, y_fact)

        # Step 1: Select Skin
        logger.info("\n--- ШАГ 1: Выбор Skin-фактора (Beam Search) ---")
        skins, skin_scores = self.select_skin(beam=3)
        logger.info(f"Проверено {len(skin_scores)} значений Skin")
        logger.info(f"Топ-{len(skins)} кандидатов: {skins}")
        
        # Show top 5 scores
        sorted_scores = sorted(skin_scores.items(), key=lambda x: x[1])
        logger.info("Лучшие Skin-факторы:")
        for skin, score in sorted_scores[:5]:
            if np.isinf(score):
                logger.info(f"  Skin={skin:.2f} -> ОШИБКА=inf")
            else:
                logger.info(f"  Skin={skin:.2f} -> ОШИБКА={score:.6f}")

        # Step 2: Select N
        logger.info("\n--- ШАГ 2: Выбор N (количества трещин) ---")
        (best_skin, best_N), scores_N = self.select_N(skins)
        
        logger.info(f"Выбран Skin={best_skin}, N={best_N}")
        
        # Show best N scores
        sorted_n_scores = sorted(scores_N.items(), key=lambda x: x[1])
        logger.info("Лучшие комбинации (Skin, N):")
        for (skin, n), score in sorted_n_scores[:5]:
            if np.isinf(score):
                logger.info(f"  (S={skin:.2f}, N={n}) -> ОШИБКА=inf")
            else:
                logger.info(f"  (S={skin:.2f}, N={n}) -> ОШИБКА={score:.6f}")

        candidates = [
            s for s in self.skin_library[best_skin]
            if s["N"] == best_N
        ]

        sample = candidates[0]
        
        logger.info(f"\nПараметры выбранного референса:")
        logger.info(f"  h={sample['h']}, W={sample['W']}, L={sample['L']}, a/L={sample['a/L']}")

        # Step 3: Optimize k and L (xf)
        logger.info("\n--- ШАГ 3: Байесовская оптимизация k и xf ---")
        logger.info(f"Границы: k in [{k_bounds[0]:.6f}, {k_bounds[1]:.6f}], xf in [{xf_bounds[0]:.6f}, {xf_bounds[1]:.6f}]")

        params, score = self.optimize_continuous(
            sample,
            k_bounds=k_bounds,
            xf_bounds=xf_bounds
        )

        logger.info("\n" + "=" * 60)
        logger.info("РЕЗУЛЬТАТ ОПТИМИЗАЦИИ:")
        logger.info(f"  Skin-фактор S = {best_skin:.4f}")
        logger.info(f"  Количество трещин N = {best_N}")
        logger.info(f"  Проницаемость k = {params.get('k', params.get('xf', 0)):.6f} мД")
        logger.info(f"  Полудлина трещины xf = {params.get('xf', params.get('k', 0)):.4f} м")
        logger.info(f"  Итоговая ошибка = {score:.6f}")
        logger.info("=" * 60)

        return {
            "skin": best_skin,
            "N": best_N,
            "params": params,
            "misfit": score
        }
