import numpy as np
import logging

from .misfit import misfit
from .beam_search import select_top_k
from .bayes_opt import bayesian_fit
from .interpolation import interpolate_input_curve

logger = logging.getLogger(__name__)


class ReservoirSolver:

    def __init__(self, skin_library, progress_callback=None):
        """
        Конструктор ReservoirSolver.
        
        Args:
            skin_library (Dict): Библиотека эталонных кривых, сгруппированная по Skin:
                {skin_value: [samples]}, где sample содержит:
                    - 'dynamic': DataFrame с X, Y
                    - 'h', 'N', 'W', 'L', 'a/L': параметры
            progress_callback (callable, optional): Функция обратного вызова для прогресса
        """

        self.skin_library = skin_library
        self.progress_callback = progress_callback

        self.derivative_modes = ["linear", "loglog"]
        # По умолчанию используем только интегральную метрику
        self.metric_types = ["integral"]
        
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
        
        Интерполирует входную кривую на сетку (логарифмическую по умолчанию).
        Результат сохраняется для повторного использования (кэширование).
        
        Args:
            x_fact (np.ndarray): X координаты входной кривой
            y_fact (np.ndarray): Y координаты входной кривой
            target_grid (np.ndarray, optional): Целевая сетка. Если None, создается логарифмическая (200 точек)
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: (x_grid, y_interp) - интерполированная кривая
        """
        """
        Однократная подготовка входной кривой.
        
        Интерполирует входную кривую на сетку референсных кривых.
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
        
        # Если передана целевая сетка - используем её
        if target_grid is not None:
            x_grid = target_grid
        else:
            # Создаем стандартную логарифмическую сетку
            x_min = np.max([np.min(x_fact), 1e-10])  # Избегаем нуля
            x_max = np.max(x_fact)
            x_grid = np.logspace(np.log10(x_min), np.log10(x_max), 200)
        
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
        
        БЕЗ НОРМАЛИЗАЦИИ - только приведение к общей сетке.
        
        Args:
            x_ref (np.ndarray): X координаты референсной кривой
            y_ref (np.ndarray): Y координаты референсной кривой
            
        Returns:
            float: Медианное значение ошибки по всем метрикам и производным
        """
        if self._x_interp is None or self._y_interp is None:
            raise ValueError("Входная кривая не подготовлена. Вызовите _prepare_input_curve()")
        
        scores = []
        
        # Приводим входную кривую к сетке референса (self._x_interp уже на нужной сетке)
        # Но для честного сравнения - интерполируем обе на общую сетку
        
        # Используем сетку входной кривой
        x_common = self._x_interp
        y_fact_common = self._y_interp
        
        # Интерполируем референс на сетку входной кривой
        try:
            y_ref_interp = interpolate_input_curve(x_ref, y_ref, x_common)
            
            # Фильтруем nan
            valid_mask = ~np.isnan(y_ref_interp)
            if np.sum(valid_mask) < 10:
                logger.debug(f"  Мало точек после интерполяции референса: {np.sum(valid_mask)}")
                return np.inf
            
            x_common = x_common[valid_mask]
            y_fact_common = y_fact_common[valid_mask]
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
    # STEP 1 — SKIN (с учётом фиксированного N)
    # -----------------------------

    def select_skin(self, beam=3, N_fixed=None):
        """
        Выбор лучших Skin-факторов методом Beam Search.
        
        Алгоритм:
        1. Если задан N_fixed - сначала фильтруем по N
        2. Для каждого Skin берём медианные значения других параметров (h, W, L, a/L)
        3. Из кривых с медианными параметрами выбираем лучшую для каждого Skin
        
        Args:
            beam (int): Количество лучших кандидатов для отбора (по умолчанию 3)
            N_fixed (int, optional): Фиксированное количество трещин для фильтрации
            
        Returns:
            Tuple[List[float], Dict[float, float]]: 
                - список top-k Skin значений
                - словарь {skin: ошибка}
        """
        
        scores = {}

        for skin, samples in self.skin_library.items():
            
            # ШАГ 1: Фильтрация по N если задан
            if N_fixed is not None:
                filtered_samples = [s for s in samples if s["N"] == N_fixed]
                if not filtered_samples:
                    # Если точного N нет - ищем ближайший
                    available_N = list(set(s["N"] for s in samples))
                    closest_N = min(available_N, key=lambda n: abs(n - N_fixed))
                    filtered_samples = [s for s in samples if s["N"] == closest_N]
            else:
                filtered_samples = samples
            
            if not filtered_samples:
                continue
            
            # ШАГ 2: Находим медианные значения параметров (h, W, L, a/L)
            h_vals = [s["h"] for s in filtered_samples]
            w_vals = [s["W"] for s in filtered_samples]
            l_vals = [s["L"] for s in filtered_samples]
            al_vals = [s["a/L"] for s in filtered_samples]
            
            h_median = np.median(h_vals)
            w_median = np.median(w_vals)
            l_median = np.median(l_vals)
            al_median = np.median(al_vals)
            
            # ШАГ 3: Находим образец ближайший к медиане
            best_sample = None
            best_diff = np.inf
            
            for sample in filtered_samples:
                diff = (abs(sample["h"] - h_median) + 
                        abs(sample["W"] - w_median) + 
                        abs(sample["L"] - l_median) + 
                        abs(sample["a/L"] - al_median))
                if diff < best_diff:
                    best_diff = diff
                    best_sample = sample
            
            if best_sample is not None:
                x_ref = best_sample["dynamic"]["X"].values
                y_ref = best_sample["dynamic"]["Y"].values

                F = self.ensemble_misfit(x_ref, y_ref)
                scores[skin] = F

        return select_top_k(scores, beam), scores

    # -----------------------------
    # STEP 2 — N (количество трещин)
    # -----------------------------

    def select_N(self, skins, N_fixed=None):
        """
        Выбор оптимального N для выбранных Skin-кандидатов.
        
        Args:
            skins (List[float]): Список Skin-кандидатов из этапа 1
            N_fixed (int, optional): Фиксированное значение N. Если указано, используется оно.
            
        Returns:
            Tuple[Tuple[float, int], Dict[Tuple[float, int], float]]:
                - (best_skin, best_N)
                - словарь ошибок {(skin, N): ошибка}
        """
        
        # Если N задан - используем его напрямую без перебора
        if N_fixed is not None:
            scores = {}
            for skin in skins:
                # Ищем ближайший N в библиотеке для данного skin
                available_N = list(set(s["N"] for s in self.skin_library[skin]))
                if N_fixed in available_N:
                    # Находим лучший sample с заданным N
                    for sample in self.skin_library[skin]:
                        if sample["N"] == N_fixed:
                            x_ref = sample["dynamic"]["X"].values
                            y_ref = sample["dynamic"]["Y"].values
                            F = self.ensemble_misfit(x_ref, y_ref)
                            scores[(skin, N_fixed)] = F
                            break
                else:
                    # Если N нет в библиотеке - используем ближайший
                    closest_N = min(available_N, key=lambda n: abs(n - N_fixed))
                    for sample in self.skin_library[skin]:
                        if sample["N"] == closest_N:
                            x_ref = sample["dynamic"]["X"].values
                            y_ref = sample["dynamic"]["Y"].values
                            F = self.ensemble_misfit(x_ref, y_ref)
                            scores[(skin, closest_N)] = F
                            break
            
            if not scores:
                # Fallback - просто берем первый skin и первый N
                best_skin = skins[0]
                best_N = list(set(s["N"] for s in self.skin_library[best_skin]))[0]
                return (best_skin, best_N), {}
            
            best = min(scores, key=scores.get)
            return best, scores
        
        # Оригинальный код - перебор всех N
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
        """
        Байесовская оптимизация непрерывных параметров k и xf.
        
        Args:
            sample (Dict): Выбранная эталонная кривая из библиотеки
            k_bounds (Tuple[float, float]): Границы проницаемости (мин, макс) в мД
            xf_bounds (Tuple[float, float]): Границы полудлины трещины (мин, макс) в м
            
        Returns:
            Tuple[Dict[str, float], float]: 
                - params с ключами 'k' и 'xf'
                - best_score - лучшее значение ошибки
        """

        x_ref = sample["dynamic"]["X"].values
        y_ref = sample["dynamic"]["Y"].values
        
        logger.info(f"  Оптимизация непрерывных параметров:")
        logger.info(f"    Границы: k in [{k_bounds[0]:.6f}, {k_bounds[1]:.6f}], xf in [{xf_bounds[0]:.4f}, {xf_bounds[1]:.4f}]")

        def objective(params):
            k, xf = params

            # Модифицируем эталонную кривую: масштабируем по Y с помощью k
            y_mod = y_ref * k * (1 + 0.1 * np.log10(xf + 1))

            # Считаем ошибку напрямую - без нормализации
            error = self.ensemble_misfit(x_ref, y_mod)
            
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

    def solve(self, x_fact, y_fact, k_bounds=(1e-5, 10), xf_bounds=(1e-3, 100), N_fixed=None):
        """
        Главный метод запуска оптимизации.
        
        Выполняет полный цикл оптимизации:
        1. Подготовка входной кривой
        2. Выбор Skin-фактора (Beam Search)
        3. Выбор N (количество трещин) - если задан, используется фиксированное значение
        4. Байесовская оптимизация k и xf
        
        Args:
            x_fact (np.ndarray): X координаты входных данных (фактические)
            y_fact (np.ndarray): Y координаты входных данных (фактические)
            k_bounds (Tuple[float, float]): Границы проницаемости (мин, макс) в мД
            xf_bounds (Tuple[float, float]): Границы полудлины трещины (мин, макс) в м
            N_fixed (int, optional): Фиксированное количество трещин. Если None - подбирается автоматически.
            
        Returns:
            Dict: Результат оптимизации с ключами:
                - 'skin': оптимальный Skin-фактор
                - 'N': оптимальное количество трещин
                - 'params': {'k': ..., 'xf': ...}
                - 'misfit': значение ошибки
        """
        
        logger.info("=" * 60)
        logger.info("НАЧАЛО ОПТИМИЗАЦИИ")
        logger.info("=" * 60)
        logger.info(f"Входные данные: {len(x_fact)} точек")
        logger.info(f"Диапазон X фактических: [{np.min(x_fact):.6f}, {np.max(x_fact):.6f}]")
        logger.info(f"Диапазон Y фактических: [{np.min(y_fact):.6f}, {np.max(y_fact):.6f}]")
        if N_fixed is not None:
            logger.info(f"Фиксированное N: {N_fixed}")
        
        # ШАГ 0: Подготовка входной кривой (однократная интерполяция)
        logger.info("\n--- ШАГ 0: Подготовка входной кривой (интерполяция) ---")
        self._prepare_input_curve(x_fact, y_fact)

        # Step 1: Select Skin (with N_fixed filter)
        logger.info("\n--- ШАГ 1: Выбор Skin-фактора (Beam Search) ---")
        skins, skin_scores = self.select_skin(beam=3, N_fixed=N_fixed)
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

        # Step 2: Select N (or use fixed N)
        logger.info("\n--- ШАГ 2: Выбор N (количества трещин) ---")
        (best_skin, best_N), scores_N = self.select_N(skins, N_fixed=N_fixed)
        
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
