import numpy as np
import pandas as pd

class DimensionlessPreprocessor:
    """
    Универсальный препроцессор для подготовки данных без изменения
    интерфейсов существующих модулей.

    Поддерживает два сценария:
    1) Постобработка уже рассчитанных X,Y (например, перед визуализацией):
       используйте prepare(df, x_col="X", y_col="Y", p_col="P").
    2) Расчёт X_calc, Y_calc из размерных данных df (t, P, Q и параметры пласта):
       используйте compute_from_dimensional(...) или удобную обёртку
       prepare_dimensional(...), которые НЕ меняют внешние модули, а
       лишь возвращают подготовленный DataFrame с добавленными колонками.
    """

    def __init__(self, eps=1e-12):
        self.eps = eps  # защита от деления на 0
        self.log_diagnostics = {}
    
    # ---------------------------
    #  1. Проверка и диагностика
    # ---------------------------
    def diagnose(self, df, x_col="X", y_col="Y"):
        x, y = df[x_col].values, df[y_col].values
        diag = {}
        diag["X_range"] = (np.nanmin(x), np.nanmax(x))
        diag["Y_range"] = (np.nanmin(y), np.nanmax(y))

        def looks_loglike(arr):
            # если значения в основном отрицательные или в диапазоне [-8, 4] → вероятно логарифм
            frac_neg = np.mean(arr < 0)
            rng = np.nanmax(arr) - np.nanmin(arr)
            return (frac_neg > 0.5) or (rng < 20 and np.nanmax(arr) < 5)
        
        diag["X_loglike"] = looks_loglike(x)
        diag["Y_loglike"] = looks_loglike(y)
        self.log_diagnostics = diag
        return diag

    # ---------------------------
    #  2. Стабилизация ΔP
    # ---------------------------
    def stabilize_dp(self, p_series, smooth=True):
        p = np.asarray(p_series)
        dp = np.abs(np.diff(p, prepend=p[0]))
        dp[dp < self.eps] = self.eps
        if smooth:
            dp = pd.Series(dp).rolling(3, center=True, min_periods=1).mean().to_numpy()
        return dp

    # ---------------------------
    #  3. Преобразование к единым диапазонам
    # ---------------------------
    def normalize_xy(self, x, y):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        x_min, x_max = np.nanmin(x), np.nanmax(x)
        y_min, y_max = np.nanmin(y), np.nanmax(y)
        x_scaled = (x - x_min) / (x_max - x_min + self.eps)
        y_scaled = (y - y_min) / (y_max - y_min + self.eps)
        return x_scaled, y_scaled
    
    def convert_units(self, df):
        """
        Линейно переводим входные данные в нужные единицы.
        Не добавляет колонок, не трогает логику X/Y.
        """
        out = df.copy()
        
        # Пример конверсий
        if 'P' in out.columns:
            # кгс/см² → Па (1 кгс/см² ≈ 98066.5 Па)
            out['P'] = out['P'] * 98066.5
        if 'dP' in out.columns:
            out['dP'] = out['dP'] * 98066.5
        if 'Q' in out.columns:
            # м³/сут → м³/ч
            out['Q'] = out['Q'] / 24
        if 't' in out.columns:
            # если время в минутах → часы (пример)
            out['t'] = out['t'] / 60
        if 'W' in out.columns:
            # длина в см → м
            out['W'] = out['W'] / 100
        if 'L' in out.columns:
            out['L'] = out['L'] / 100
        if 'h' in out.columns:
            out['h'] = out['h'] / 100

        return out

    
    # ---------------------------
    #  3.1. Расчёт X_calc/Y_calc из размерных данных
    # ---------------------------
    def compute_from_dimensional(self,
                                 df,
                                 *,
                                 time_col="t",
                                 pressure_col="P",
                                 flow_col="Q",
                                 well_params: dict | None = None,
                                 x_mode: str = "constant",
                                 delta_p_mode: str = "initial"):
        """
        Возвращает КОПИЮ df с добавленными колонками:
        - X_calc, Y_calc: рассчитанные безразмерные параметры на основе
          convert_to_dimensionless_curves (из helpers.dimensionless_analysis)
        - P (если отсутствует): скопированная колонка давления для диагностики
        Ничего не меняет снаружи; безопасно к NaN/Inf.
        """
        out = df.copy()
        try:
            import pandas as _pd
            from helpers.dimensionless_analysis import convert_to_dimensionless_curves
            t = _pd.Series(out[time_col])
            p = _pd.Series(out[pressure_col])
            q = _pd.Series(out[flow_col])
            dim = convert_to_dimensionless_curves(
                time=t,
                pressure=p,
                flow_rate=q,
                well_params=well_params or {},
                x_mode=x_mode,
                delta_p_mode=delta_p_mode
            )
            out["X_calc"] = np.asarray(dim.X, dtype=float)
            out["Y_calc"] = np.asarray(dim.Y, dtype=float)
            if "P" not in out.columns:
                out["P"] = np.asarray(p, dtype=float)
        except Exception:
            # В случае ошибки — возвращаем копию без добавлений
            return out
        return out

    # ---------------------------
    #  4. Подготовка данных
    # ---------------------------
    def prepare(self, df, x_col="X", y_col="Y", p_col="P", log_for_plot=True):
        """
        Основной метод.
        Возвращает DataFrame с колонками:
        - X_raw, Y_raw
        - X_scaled, Y_scaled
        - logX, logY (только для построения)
        """
        result = df.copy()
        diag = self.diagnose(df, x_col, y_col)

        # стабилизация ΔP
        if p_col in df.columns:
            result["dP_stab"] = self.stabilize_dp(df[p_col])
        else:
            result["dP_stab"] = np.nan

        # нормализация
        result["X_scaled"], result["Y_scaled"] = self.normalize_xy(result[x_col], result[y_col])

        # логарифмирование только для визуализации
        if log_for_plot:
            if not diag["X_loglike"]:
                result["logX"] = np.log10(np.clip(result[x_col], self.eps, None))
            else:
                result["logX"] = result[x_col]  # уже логарифмировано

            if not diag["Y_loglike"]:
                result["logY"] = np.log10(np.clip(result[y_col], self.eps, None))
            else:
                result["logY"] = result[y_col]
        else:
            result["logX"] = result["X_scaled"]
            result["logY"] = result["Y_scaled"]

        return result

    # ---------------------------
    #  4.1. Комбинированная обёртка для размерных данных
    # ---------------------------
    def prepare_dimensional(self,
                            df,
                            *,
                            time_col="t",
                            pressure_col="P",
                            flow_col="Q",
                            well_params: dict | None = None,
                            x_mode: str = "darcy",
                            delta_p_mode: str = "initial",
                            log_for_plot: bool = True):
        """
        1) Считает X_calc, Y_calc по размерным данным (не меняет внешние классы);
        2) Добавляет масштабированные/логарифмические копии для безопасной визуализации.
        Возвращает НОВЫЙ DataFrame.
        """
        
        df = self.convert_units(df)
        
        tmp = self.compute_from_dimensional(
            df,
            time_col=time_col,
            pressure_col=pressure_col,
            flow_col=flow_col,
            well_params=well_params,
            x_mode=x_mode,
            delta_p_mode=delta_p_mode,
        )
        # Если расчёт не удался — вернём результат diagnose/prepare на исходных X,Y при их наличии
        x_col = "X_calc" if "X_calc" in tmp.columns else ("X" if "X" in tmp.columns else None)
        y_col = "Y_calc" if "Y_calc" in tmp.columns else ("Y" if "Y" in tmp.columns else None)
        if x_col and y_col:
            return self.prepare(tmp, x_col=x_col, y_col=y_col, p_col=(pressure_col if pressure_col in tmp.columns else "P"), log_for_plot=log_for_plot)
        return tmp

    # ---------------------------
    # 5. Вывод диагностики
    # ---------------------------
    def print_diagnostics(self):
        diag = self.log_diagnostics
        if not diag:
            print("Диагностика ещё не выполнялась")
            return
        print("Диагностика данных:")
        for k, v in diag.items():
            print(f"  {k}: {v}")
        if diag["X_loglike"] or diag["Y_loglike"]:
            print("Обнаружены признаки уже логарифмированных данных — повторное log10 не нужно.")
        else:
            print("ыДанные в физических единицах — логарифмирование только при визуализации.")
