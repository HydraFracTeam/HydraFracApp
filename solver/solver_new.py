import numpy as np
import logging

from .misfit import misfit, get_scale_factors
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

        # Используем интегральную метрику и линейную производную
        self.derivative_modes = ["linear"]
        self.metric_types = ["integral"]
        
        # Кэш для интерполированной входной кривой
        self._x_interp = None
        self._y_interp = None

    # -----------------------------
    # INPUT CURVE PREPARATION
    # -----------------------------
    
    def _prepare_input_curve(self, x_fact, y_fact, target_grid=None):
        """
        Однократная подготовка входной кривой.
        
        Интерполирует входную кривую на сетку (логарифмическую по умолчанию).
        
        Args:
            x_fact (np.ndarray): X координаты входной кривой
            y_fact (np.ndarray): Y координаты входной кривой
            target_grid (np.ndarray, optional): Целевая сетка
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: (x_grid, y_interp)
        """
        x_fact = np.asarray(x_fact)
        y_fact = np.asarray(y_fact)
        
        # Проверяем кэш
        if (self._x_interp is not None):
            return self._x_interp, self._y_interp
        
        # Если передана целевая сетка - используем её
        if target_grid is not None:
            x_grid = target_grid
        else:
            # Создаем стандартную логарифмическую сетку
            x_min = max(np.min(x_fact), 1e-10)
            x_max = np.max(x_fact)
            x_grid = np.logspace(np.log10(x_min), np.log10(x_max), 200)
        
        # Интерполируем входную кривую на сетку
        try:
            y_interp = interpolate_input_curve(x_fact, y_fact, x_grid)
            
            # Фильтруем nan
            valid_mask = ~np.isnan(y_interp)
            if np.sum(valid_mask) < 10:
                logger.warning("Мало точек после интерполяции")
                return x_fact, y_fact
            
            x_grid = x_grid[valid_mask]
            y_interp = y_interp[valid_mask]
            
        except Exception as e:
            logger.warning(f"Ошибка интерполяции: {e}")
            return x_fact, y_fact
        
        # Сохраняем для кэширования
        self._x_interp = x_grid
        self._y_interp = y_interp
        
        return x_grid, y_interp

    # -----------------------------
    # MISFIT CALCULATION
    # -----------------------------

    def calculate_misfit(self, x_ref, y_ref):
        """
        Расчет невязки между интерполированной фактической и референсной кривыми.
        При этом референсная кривая масштабируется к диапазону фактической.
        
        Args:
            x_ref (np.ndarray): X координаты референсной кривой
            y_ref (np.ndarray): Y координаты референсной кривой
            
        Returns:
            float: Значение ошибки
        """
        if self._x_interp is None or self._y_interp is None:
            raise ValueError("Входная кривая не подготовлена")
        
        # Используем сетку входной кривой
        x_common = self._x_interp
        y_fact_common = self._y_interp
        
        # Интерполируем референс на сетку входной кривой
        try:
            y_ref_interp = interpolate_input_curve(x_ref, y_ref, x_common)
            
            valid_mask = ~np.isnan(y_ref_interp)
            if np.sum(valid_mask) < 10:
                return np.inf
            
            x_common = x_common[valid_mask]
            y_fact_common = y_fact_common[valid_mask]
            y_ref_common = y_ref_interp[valid_mask]
            
        except ValueError as e:
            logger.debug(f"Ошибка интерполяции референса: {e}")
            return np.inf

        # Вычисляем невязку с масштабированием референса к факту
        for d in self.derivative_modes:
            for m in self.metric_types:
                F = misfit(
                    x_common, y_fact_common,
                    x_common, y_ref_common,
                    d, m,
                    200,
                    scale_ref=True  # Масштабируем референс к факту
                )
                return F
        
        return np.inf

    # -----------------------------
    # STEP 1 — SKIN (с фиксированным N)
    # -----------------------------

    def select_skin(self, beam=3, N_fixed=None):
        """
        Выбор лучших Skin-факторов.
        
        Алгоритм:
        1. Фильтруем по N (фиксированное значение от пользователя)
        2. Для каждого Skin: выбираем образец с медианными параметрами (h, W, L, a/L)
        3. Сравниваем кривые по ошибке
        
        Args:
            beam (int): Количество лучших кандидатов
            N_fixed (int): Фиксированное количество трещин
            
        Returns:
            Tuple[List[float], Dict[float, float]]: (top-k скинов, {skin: ошибка})
        """
        scores = {}

        for skin, samples in self.skin_library.items():
            
            # ШАГ 1: Фильтрация по N
            if N_fixed is not None:
                filtered = [s for s in samples if s["N"] == N_fixed]
                if not filtered:
                    # Ближайший N
                    available_N = list(set(s["N"] for s in samples))
                    closest_N = min(available_N, key=lambda n: abs(n - N_fixed))
                    filtered = [s for s in samples if s["N"] == closest_N]
            else:
                filtered = samples
            
            if not filtered:
                continue
            
            # ШАГ 2: Медианные параметры (h, W, L, a/L)
            h_vals = [s["h"] for s in filtered]
            w_vals = [s["W"] for s in filtered]
            l_vals = [s["L"] for s in filtered]
            al_vals = [s["a/L"] for s in filtered]
            
            h_med = np.median(h_vals)
            w_med = np.median(w_vals)
            l_med = np.median(l_vals)
            al_med = np.median(al_vals)
            
            # ШАГ 3: Выбираем образец ближайший к медиане
            best_sample = min(filtered, 
                key=lambda s: abs(s["h"] - h_med) + abs(s["W"] - w_med) + 
                              abs(s["L"] - l_med) + abs(s["a/L"] - al_med))
            
            x_ref = best_sample["dynamic"]["X"].values
            y_ref = best_sample["dynamic"]["Y"].values

            F = self.calculate_misfit(x_ref, y_ref)
            scores[skin] = F
            logger.debug(f"Skin={skin:.2f}, N={best_sample['N']}: misfit={F:.6f}")

        return select_top_k(scores, beam), scores

    # -----------------------------
    # MAIN SOLVER
    # -----------------------------

    def solve(self, x_fact, y_fact, N_fixed=None):
        """
        Главный метод запуска оптимизации.
        
        Алгоритм:
        1. Подготовка входной кривой (интерполяция)
        2. Выбор Skin-фактора (при фиксированном N)
        3. Возврат результата
        
        Args:
            x_fact (np.ndarray): X координаты входных данных
            y_fact (np.ndarray): Y координаты входных данных
            N_fixed (int): Фиксированное количество трещин (ОБЯЗАТЕЛЬНО)
            
        Returns:
            Dict: {
                'skin': оптимальный Skin-фактор,
                'N': количество трещин (то что передали),
                'params': {'k': 1.0, 'xf': 1.0},  # пока не оптимизируем
                'misfit': значение ошибки
            }
        """
        
        logger.info("=" * 60)
        logger.info("НАЧАЛО ОПТИМИЗАЦИИ")
        logger.info("=" * 60)
        logger.info(f"Входные данные: {len(x_fact)} точек")
        logger.info(f"Диапазон X: [{np.min(x_fact):.6f}, {np.max(x_fact):.6f}]")
        logger.info(f"Диапазон Y: [{np.min(y_fact):.6f}, {np.max(y_fact):.6f}]")
        logger.info(f"N (фиксировано): {N_fixed}")
        
        # ШАГ 0: Подготовка входной кривой
        logger.info("\n--- ШАГ 0: Интерполяция входной кривой ---")
        x_grid, y_interp = self._prepare_input_curve(x_fact, y_fact)
        logger.info(f"Интерполировано на {len(x_grid)} точек")
        
        # ШАГ 1: Выбор Skin
        logger.info("\n--- ШАГ 1: Выбор Skin-фактора ---")
        skins, skin_scores = self.select_skin(beam=3, N_fixed=N_fixed)
        
        logger.info(f"Проверено {len(skin_scores)} значений Skin")
        logger.info(f"Топ-{len(skins)}: {skins}")
        
        sorted_scores = sorted(skin_scores.items(), key=lambda x: x[1])
        logger.info("Лучшие Skin-факторы:")
        for skin, score in sorted_scores[:5]:
            logger.info(f"  Skin={skin:.2f} -> ОШИБКА={score:.6f}")
        
        # Лучший скин
        best_skin = skins[0]
        best_score = skin_scores[best_skin]
        
        logger.info("\n" + "=" * 60)
        logger.info("РЕЗУЛЬТАТ:")
        logger.info(f"  Skin = {best_skin:.4f}")
        logger.info(f"  N = {N_fixed}")
        logger.info(f"  Ошибка = {best_score:.6f}")
        logger.info("=" * 60)

        return {
            "skin": best_skin,
            "N": N_fixed,
            "params": {"k": 1.0, "xf": 1.0},
            "misfit": best_score
        }
