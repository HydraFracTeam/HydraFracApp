import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from scipy.interpolate import RBFInterpolator
from sklearn.metrics import mean_squared_error


class DimensionlessCurveInterpolator:
    """
    Интерполятор безразмерных кривых ГРП с адаптивным выбором метода.
    Интерполирует зависимость P_D(Y) по параметрам Skin, N, a/L.
    """

    def __init__(self, methods=("linear", "rbf", "gp"), constraints=None):
        """
        :param methods: список методов, которые будут тестироваться
        :param constraints: словарь физических ограничений
        """
        self.methods = methods
        self.best_method = None
        self.models = []
        self.Y_grid = None
        self.param_grid = None
        self.is_fitted = False
        self.rmse_scores = {}

        self.constraints = constraints or {
            "monotonic": True,
            "positive": True,
            "smooth": True,
            "clip_range": (0, 5.0),
        }

    def fit(self, param_grid: np.ndarray, Y_grid: np.ndarray, P_curves: np.ndarray):
        """Обучение интерполяции и автоматический выбор метода."""
        self.param_grid = np.asarray(param_grid)
        self.Y_grid = np.asarray(Y_grid)
        n_points = P_curves.shape[1]

        best_rmse = np.inf
        best_method = None
        best_models = None

        # Тестируем все методы
        for method in self.methods:
            models = []
            preds_all = []
            for i in range(n_points):
                y_values = P_curves[:, i]

                # Обучаем модель
                if method == "linear":
                    model = LinearRegression().fit(self.param_grid, y_values)
                    preds = model.predict(self.param_grid)
                elif method == "rbf":
                    model = RBFInterpolator(self.param_grid, y_values, kernel='thin_plate_spline')
                    preds = model(self.param_grid)
                elif method == "gp":
                    kernel = RBF(length_scale=1.0) + WhiteKernel(noise_level=1e-5)
                    model = GaussianProcessRegressor(kernel=kernel).fit(self.param_grid, y_values)
                    preds = model.predict(self.param_grid)
                else:
                    raise ValueError(f"Неизвестный метод: {method}")

                models.append(model)
                preds_all.append(preds)

            preds_all = np.array(preds_all).T
            rmse = np.sqrt(mean_squared_error(P_curves, preds_all))
            self.rmse_scores[method] = rmse

            if rmse < best_rmse:
                best_rmse = rmse
                best_method = method
                best_models = models

        # Сохраняем лучший результат
        self.best_method = best_method
        self.models = best_models
        self.is_fitted = True
        return self

    def predict(self, skin: float, N: float, a_L: float) -> pd.Series:
        """Получение интерполированной безразмерной кривой для заданных параметров."""
        if not self.is_fitted:
            raise RuntimeError("Сначала вызови fit()")

        X_pred = np.array([[skin, N, a_L]])
        preds = []

        for model in self.models:
            if isinstance(model, RBFInterpolator):
                val = model(X_pred)
            else:
                val = model.predict(X_pred)
            preds.append(val[0])

        P_curve = np.array(preds)
        P_curve = self._apply_physical_constraints(P_curve)
        return pd.Series(P_curve, index=self.Y_grid, name=f"P_D(s={skin}, N={N}, a/L={a_L})")

    # ---------------------------
    # 🔧 ФИЗИЧЕСКИЕ ОГРАНИЧЕНИЯ
    # ---------------------------

    def _apply_physical_constraints(self, P_curve: np.ndarray) -> np.ndarray:
        """Применяет базовые физические ограничения к кривой."""
        if self.constraints.get("positive", True):
            P_curve = np.maximum(P_curve, 0.0)

        if self.constraints.get("clip_range", None):
            low, high = self.constraints["clip_range"]
            P_curve = np.clip(P_curve, low, high)

        if self.constraints.get("monotonic", True):
            P_curve = np.maximum.accumulate(P_curve[::-1])[::-1]

        if self.constraints.get("smooth", True):
            P_curve = np.convolve(P_curve, np.ones(3)/3, mode='same')

        return P_curve

    # ---------------------------
    # 📊 ВИЗУАЛИЗАЦИЯ (для GUI)
    # ---------------------------

    def visualize_prediction(self, plot_widget, Y_true, P_true, Y_pred, P_pred):
        """Визуализация сравнения интерполяции в PyQtGraph."""
        import pyqtgraph as pg

        plot_widget.clear()

        # Истинные значения — серые точки
        plot_widget.plot(
            Y_true, P_true, pen=None, symbol='o', symbolBrush=(150, 150, 150), symbolSize=6,
            name='Эталонные точки'
        )

        # Интерполированные значения — красная линия + маркеры
        plot_widget.plot(
            Y_pred, P_pred, pen=pg.mkPen(color=(255, 0, 0), width=2),
            symbol='t', symbolBrush=(255, 0, 0), symbolSize=8,
            name=f'Интерполяция ({self.best_method}, RMSE={self.rmse_scores[self.best_method]:.4f})'
        )

        plot_widget.setLogMode(True, True)
        plot_widget.showGrid(x=True, y=True)
        plot_widget.setLabel('bottom', 'Y (безразмерный ёмкостной параметр)')
        plot_widget.setLabel('left', 'P_D (безразмерное давление)')
        plot_widget.setTitle('Сравнение интерполяции безразмерной кривой')

