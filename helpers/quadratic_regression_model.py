"""
Модуль для обучения квадратичной регрессии подгонки расчётных X-Y под эталонные.
Обучается на массиве всех скважин для создания общей модели.
"""

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline
from typing import Dict, Any, Optional, Tuple
import warnings

warnings.filterwarnings('ignore')


class QuadraticRegressionModel:
    """
    Квадратичная регрессия для подгонки расчётных X-Y под эталонные X-Y из данных.
    Обучается на массиве всех скважин с регуляризацией и физическими ограничениями.
    """
    
    def __init__(self, alpha: float = 0.1, fit_only_y: bool = False):
        """
        :param alpha: Коэффициент регуляризации L2 (Ridge) - уменьшен по умолчанию для лучшей подгонки
        :param fit_only_y: Если True, подгоняется только Y (X не изменяется)
        """
        self.alpha = alpha
        self.fit_only_y = fit_only_y
        self.X_model = None  # Модель для X
        self.Y_model = None  # Модель для Y
        self.is_fitted = False
        self.n_samples = 0
        self.rmse_x = None
        self.rmse_y = None
        self.r2_x = None
        self.r2_y = None
        self.Y_shift = 0.0  # Дополнительный сдвиг по Y для компенсации вертикального смещения
        
    def fit(self, X_calc: np.ndarray, Y_calc: np.ndarray, 
            X_data: np.ndarray, Y_data: np.ndarray) -> 'QuadraticRegressionModel':
        """
        Обучает модель на массиве расчётных и эталонных X-Y.
        
        :param X_calc: Расчётные значения X (массив всех точек со всех скважин)
        :param Y_calc: Расчётные значения Y (массив всех точек со всех скважин)
        :param X_data: Эталонные значения X из данных
        :param Y_data: Эталонные значения Y из данных
        """
        # Проверка входных данных
        X_calc = np.asarray(X_calc).flatten()
        Y_calc = np.asarray(Y_calc).flatten()
        X_data = np.asarray(X_data).flatten()
        Y_data = np.asarray(Y_data).flatten()
        
        # Убираем NaN и Inf
        mask = (np.isfinite(X_calc) & np.isfinite(Y_calc) & 
                np.isfinite(X_data) & np.isfinite(Y_data))
        
        X_calc_clean = X_calc[mask]
        Y_calc_clean = Y_calc[mask]
        X_data_clean = X_data[mask]
        Y_data_clean = Y_data[mask]
        
        if len(X_calc_clean) < 30:
            raise ValueError(f"Недостаточно точек для обучения. Найдено: {len(X_calc_clean)}, требуется минимум 30")
        
        self.n_samples = len(X_calc_clean)
        
        # Обучение модели для X
        if not self.fit_only_y:
            # Линейная регрессия с регуляризацией: X_fit = a * X_calc
            # Используем Ridge для регуляризации
            self.X_model = Ridge(alpha=self.alpha, fit_intercept=False)
            X_features = X_calc_clean.reshape(-1, 1)
            self.X_model.fit(X_features, X_data_clean)
            
            # Метрики для X
            X_pred = self.X_model.predict(X_features)
            self.rmse_x = np.sqrt(np.mean((X_data_clean - X_pred) ** 2))
            ss_tot_x = np.sum((X_data_clean - np.mean(X_data_clean)) ** 2)
            if ss_tot_x > 0:
                self.r2_x = 1 - np.sum((X_data_clean - X_pred) ** 2) / ss_tot_x
            else:
                self.r2_x = 0.0
        else:
            # Если fit_only_y, X не изменяется
            self.X_model = None
            self.rmse_x = 0.0
            self.r2_x = 1.0
        
        # Обучение модели для Y с квадратичным членом и явным сдвигом
        # Y_fit = shift + b + a_y * Y_calc + c * Y_calc^2
        # где shift - явный сдвиг всей кривой вверх-вниз (не зависит от Y_calc)
        # Используем PolynomialFeatures для квадратичного члена
        # ВАЖНО: include_bias=True добавляет константный член [1, Y, Y^2]
        poly_features = PolynomialFeatures(degree=2, include_bias=True)
        Y_features = poly_features.fit_transform(Y_calc_clean.reshape(-1, 1))
        
        # Ridge регрессия с регуляризацией
        # fit_intercept=True добавляет отдельный intercept (сдвиг), который обеспечивает
        # гибкость корректировки всей кривой вверх-вниз без изменения формы
        # Этот intercept обучается отдельно и не так сильно ограничен регуляризацией
        self.Y_model = Ridge(alpha=self.alpha, fit_intercept=True)
        self.Y_model.fit(Y_features, Y_data_clean)
        
        # Метрики для Y
        Y_pred = self.Y_model.predict(Y_features)
        
        # Y_shift теперь хранится в self.Y_model.intercept_
        # Это явный сдвиг всей кривой, который добавляется ко всем значениям
        self.Y_shift = float(self.Y_model.intercept_) if hasattr(self.Y_model, 'intercept_') else 0.0
        
        # Применяем предсказания (intercept уже включен в predict)
        Y_pred_shifted = Y_pred
        
        self.rmse_y = np.sqrt(np.mean((Y_data_clean - Y_pred_shifted) ** 2))
        ss_tot_y = np.sum((Y_data_clean - np.mean(Y_data_clean)) ** 2)
        if ss_tot_y > 0:
            self.r2_y = 1 - np.sum((Y_data_clean - Y_pred_shifted) ** 2) / ss_tot_y
        else:
            self.r2_y = 0.0
        
        # Применяем физические ограничения к коэффициентам
        self._apply_physical_constraints()
        
        self.is_fitted = True
        return self
    
    def _apply_physical_constraints(self) -> None:
        """Применяет физические ограничения к коэффициентам модели."""
        if self.Y_model is not None:
            # Коэффициенты: [1, Y, Y^2] -> [bias, a_y, c]
            # coef_ в Ridge имеет форму (n_features,), а не (1, n_features)
            coef = np.asarray(self.Y_model.coef_).flatten()
            
            if len(coef) >= 3:
                # Ограничиваем квадратичный коэффициент c в пределах [-0.2, 0.2]
                c = coef[2]
                if c < -0.2:
                    coef[2] = -0.2
                elif c > 0.2:
                    coef[2] = 0.2
                
                # Обновляем коэффициенты модели (сохраняем исходную форму)
                original_shape = self.Y_model.coef_.shape
                self.Y_model.coef_ = coef.reshape(original_shape)
    
    def predict(self, X_calc: np.ndarray, Y_calc: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Применяет обученную модель к новым расчётным X-Y.
        
        :param X_calc: Расчётные значения X
        :param Y_calc: Расчётные значения Y
        :return: Кортеж (X_fitted, Y_fitted) - подогнанные значения
        """
        if not self.is_fitted:
            raise RuntimeError("Модель не обучена. Вызовите fit() сначала.")
        
        X_calc = np.asarray(X_calc).flatten()
        Y_calc = np.asarray(Y_calc).flatten()
        
        # Предсказание для X
        if not self.fit_only_y and self.X_model is not None:
            X_features = X_calc.reshape(-1, 1)
            X_fitted = self.X_model.predict(X_features)
        else:
            X_fitted = X_calc.copy()
        
        # Предсказание для Y с квадратичным членом
        if self.Y_model is not None:
            poly_features = PolynomialFeatures(degree=2, include_bias=True)
            Y_features = poly_features.fit_transform(Y_calc.reshape(-1, 1))
            # predict() автоматически добавляет intercept (сдвиг), если fit_intercept=True
            Y_fitted = self.Y_model.predict(Y_features)
        else:
            Y_fitted = Y_calc.copy()
        
        return X_fitted, Y_fitted
    
    def get_coefficients(self) -> Dict[str, float]:
        """
        Возвращает коэффициенты модели.
        
        :return: Словарь с коэффициентами
        """
        if not self.is_fitted:
            return {}
        
        coef_dict = {}
        
        # Коэффициенты для X
        if not self.fit_only_y and self.X_model is not None:
            # coef_ в Ridge имеет форму (n_features,), а не (1, n_features)
            x_coef = np.asarray(self.X_model.coef_).flatten()
            coef_dict['a'] = float(x_coef[0]) if len(x_coef) > 0 else 1.0
        else:
            coef_dict['a'] = 1.0
        
        # Коэффициенты для Y: [bias из PolynomialFeatures, a_y, c] + intercept (сдвиг)
        if self.Y_model is not None:
            # coef_ в Ridge имеет форму (n_features,), а не (1, n_features)
            coef = np.asarray(self.Y_model.coef_).flatten()
            # intercept_ - это явный сдвиг всей кривой (отдельный параметр)
            intercept = float(self.Y_model.intercept_) if hasattr(self.Y_model, 'intercept_') else 0.0
            
            if len(coef) >= 3:
                coef_dict['b'] = float(coef[0])  # bias из PolynomialFeatures
                coef_dict['a_y'] = float(coef[1])  # линейный коэффициент
                coef_dict['c'] = float(coef[2])  # квадратичный коэффициент
                coef_dict['shift'] = intercept  # явный сдвиг всей кривой вверх-вниз
            elif len(coef) >= 2:
                coef_dict['b'] = float(coef[0])
                coef_dict['a_y'] = float(coef[1])
                coef_dict['c'] = 0.0
                coef_dict['shift'] = intercept
            else:
                coef_dict['b'] = 0.0
                coef_dict['a_y'] = 1.0
                coef_dict['c'] = 0.0
                coef_dict['shift'] = intercept
        else:
            coef_dict['b'] = 0.0
            coef_dict['a_y'] = 1.0
            coef_dict['c'] = 0.0
            coef_dict['shift'] = 0.0
        
        return coef_dict
    
    def get_metrics(self) -> Dict[str, float]:
        """
        Возвращает метрики качества модели.
        
        :return: Словарь с метриками
        """
        if not self.is_fitted:
            return {}
        
        return {
            'n_samples': self.n_samples,
            'rmse_x': self.rmse_x,
            'rmse_y': self.rmse_y,
            'r2_x': self.r2_x,
            'r2_y': self.r2_y
        }
    
    def get_info(self) -> str:
        """
        Возвращает текстовую информацию о модели.
        
        :return: Строка с информацией
        """
        if not self.is_fitted:
            return "Модель не обучена"
        
        coef = self.get_coefficients()
        metrics = self.get_metrics()
        
        info = f"Квадратичная регрессия (Ridge, alpha={self.alpha})\n"
        info += f"Обучена на {metrics['n_samples']} точках\n\n"
        info += f"Коэффициенты:\n"
        if not self.fit_only_y:
            info += f"  X: a = {coef['a']:.6f}\n"
        else:
            info += f"  X: не изменяется (fit_only_y=True)\n"
        shift_val = coef.get('shift', 0.0)
        info += f"  Y: a_y = {coef['a_y']:.6f}, b = {coef['b']:.6f}, c = {coef['c']:.6f}, shift = {shift_val:.6f}\n\n"
        info += f"Метрики:\n"
        if not self.fit_only_y:
            info += f"  X: RMSE = {metrics['rmse_x']:.6e}, R² = {metrics['r2_x']:.4f}\n"
        info += f"  Y: RMSE = {metrics['rmse_y']:.6e}, R² = {metrics['r2_y']:.4f}\n"
        
        return info

