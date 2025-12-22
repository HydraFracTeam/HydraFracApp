"""
Модуль для обучения и использования двух специализированных моделей аппроксимации
для пологих и крутых безразмерных X-Y кривых.
Реализует контракт: разделение на классы и обучение раздельных моделей.
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional, List
from helpers.curve_classifier import CurveClassifier
from helpers.quadratic_regression_model import QuadraticRegressionModel
import warnings

warnings.filterwarnings('ignore')


class BinaryCurveModel:
    """
    Модель с бинарной классификацией кривых и двумя специализированными аппроксиматорами.
    
    Работает по следующему принципу:
    1. Классифицирует кривые на пологие (класс 0) и крутые (класс 1)
    2. Обучает две отдельные модели аппроксимации для каждого класса
    3. При предсказании сначала классифицирует кривую, затем использует соответствующую модель
    """
    
    def __init__(self, 
                 classifier_type: str = 'logistic',
                 alpha: float = 0.1,
                 fit_only_y: bool = False,
                 quad_regularization_multiplier: float = 5.0):
        """
        :param classifier_type: Тип классификатора ('logistic', 'tree', 'forest')
        :param alpha: Коэффициент регуляризации L2 для моделей аппроксимации
        :param fit_only_y: Если True, подгоняется только Y (X не изменяется)
        :param quad_regularization_multiplier: Множитель регуляризации для квадратичного члена
        """
        self.classifier_type = classifier_type
        self.alpha = alpha
        self.fit_only_y = fit_only_y
        self.quad_regularization_multiplier = quad_regularization_multiplier
        
        # Классификатор кривых
        self.classifier = CurveClassifier(classifier_type=classifier_type)
        
        # Две модели аппроксимации с увеличенной регуляризацией для квадратичного члена
        self.model_flat = QuadraticRegressionModel(
            alpha=alpha, 
            fit_only_y=fit_only_y,
            quad_regularization_multiplier=quad_regularization_multiplier
        )  # Для пологих (класс 0)
        self.model_steep = QuadraticRegressionModel(
            alpha=alpha, 
            fit_only_y=fit_only_y,
            quad_regularization_multiplier=quad_regularization_multiplier
        )  # Для крутых (класс 1)
        
        self.is_fitted = False
        self.n_samples_flat = 0
        self.n_samples_steep = 0
        
    def fit(self, 
            X_calc_all: np.ndarray,
            Y_calc_all: np.ndarray,
            X_data_all: np.ndarray,
            Y_data_all: np.ndarray,
            P_curves: Optional[List[np.ndarray]] = None,
            Q_curves: Optional[List[np.ndarray]] = None,
            X_calc_curves: Optional[List[np.ndarray]] = None,
            Y_calc_curves: Optional[List[np.ndarray]] = None,
            X_data_curves: Optional[List[np.ndarray]] = None,
            Y_data_curves: Optional[List[np.ndarray]] = None,
            h_values: Optional[List[float]] = None,
            L_values: Optional[List[float]] = None,
            W_values: Optional[List[float]] = None) -> 'BinaryCurveModel':
        """
        Обучает классификатор и две модели аппроксимации.
        
        :param X_calc_all: Расчётные значения X (массив всех точек)
        :param Y_calc_all: Расчётные значения Y (массив всех точек)
        :param X_data_all: Эталонные значения X из данных
        :param Y_data_all: Эталонные значения Y из данных
        :param P_curves: Список массивов давления P для каждой кривой (для классификации)
        :param Q_curves: Список массивов дебита Q для каждой кривой (для классификации)
        :param X_calc_curves: Список массивов расчётных X для каждой кривой (для определения меток)
        :param Y_calc_curves: Список массивов расчётных Y для каждой кривой (для определения меток)
        :param X_data_curves: Список массивов эталонных X для каждой кривой (для определения меток)
        :param Y_data_curves: Список массивов эталонных Y для каждой кривой (для определения меток)
        :param h_values: Список значений h (толщина пласта) для каждой кривой
        :param L_values: Список значений L (длина трещины) для каждой кривой
        :param W_values: Список значений W (ширина трещины) для каждой кривой
        """
        # Проверка входных данных
        X_calc_all = np.asarray(X_calc_all).flatten()
        Y_calc_all = np.asarray(Y_calc_all).flatten()
        X_data_all = np.asarray(X_data_all).flatten()
        Y_data_all = np.asarray(Y_data_all).flatten()
        
        if len(X_calc_all) != len(Y_calc_all) or len(X_calc_all) != len(X_data_all) or len(X_calc_all) != len(Y_data_all):
            raise ValueError("Все массивы должны иметь одинаковую длину")
        
        # Проверка входных данных для классификатора
        if P_curves is None or Q_curves is None:
            raise ValueError("P_curves и Q_curves обязательны для обучения классификатора")
        
        if X_calc_curves is None or Y_calc_curves is None or X_data_curves is None or Y_data_curves is None:
            raise ValueError("X_calc_curves, Y_calc_curves, X_data_curves, Y_data_curves обязательны для определения меток")
        
        if len(P_curves) != len(Q_curves) or len(P_curves) != len(X_calc_curves):
            raise ValueError(f"Количество кривых не совпадает: P={len(P_curves)}, Q={len(Q_curves)}, X_calc={len(X_calc_curves)}")
        
        # Обучение классификатора на P-Q признаках с метками из сравнения X-Y кривых
        print(f"Обучение классификатора на {len(P_curves)} кривых (признаки: P, Q, h, L, W)...")
        self.classifier.fit(P_curves, Q_curves, X_calc_curves, Y_calc_curves, X_data_curves, Y_data_curves,
                           h_values=h_values, L_values=L_values, W_values=W_values)
        
        # Классифицируем каждую кривую на основе P, Q и параметров скважины
        curve_classes = []
        for i, (P_curve, Q_curve) in enumerate(zip(P_curves, Q_curves)):
            h = h_values[i] if h_values and i < len(h_values) else None
            L = L_values[i] if L_values and i < len(L_values) else None
            W = W_values[i] if W_values and i < len(W_values) else None
            curve_class = self.classifier.predict(P_curve, Q_curve, h=h, L=L, W=W)
            curve_classes.append(curve_class)
        
        curve_classes = np.array(curve_classes)
        n_flat = np.sum(curve_classes == 0)
        n_steep = np.sum(curve_classes == 1)
        
        print(f"Распределение классов: ужимать/круче (0) = {n_flat}, растягивать/пологие (1) = {n_steep}")
        
        # Разделяем данные по классам
        # Для этого нужно знать, к какой кривой относится каждая точка
        # Если X_calc_curves и Y_calc_curves предоставлены, используем их для разделения
        if len(X_calc_curves) > 1:
            # Разделяем точки по кривым
            flat_indices = []
            steep_indices = []
            
            current_idx = 0
            for i, (X_calc_curve, Y_calc_curve) in enumerate(zip(X_calc_curves, Y_calc_curves)):
                curve_len = len(X_calc_curve)
                if curve_classes[i] == 0:
                    # Пологие кривые
                    flat_indices.extend(range(current_idx, current_idx + curve_len))
                else:
                    # Крутые кривые
                    steep_indices.extend(range(current_idx, current_idx + curve_len))
                current_idx += curve_len
            
            # Проверяем, что индексы не выходят за границы
            max_idx = len(X_calc_all)
            flat_indices = [idx for idx in flat_indices if idx < max_idx]
            steep_indices = [idx for idx in steep_indices if idx < max_idx]
            
            if len(flat_indices) > 0:
                X_calc_flat = X_calc_all[flat_indices]
                Y_calc_flat = Y_calc_all[flat_indices]
                X_data_flat = X_data_all[flat_indices]
                Y_data_flat = Y_data_all[flat_indices]
            else:
                X_calc_flat = np.array([])
                Y_calc_flat = np.array([])
                X_data_flat = np.array([])
                Y_data_flat = np.array([])
            
            if len(steep_indices) > 0:
                X_calc_steep = X_calc_all[steep_indices]
                Y_calc_steep = Y_calc_all[steep_indices]
                X_data_steep = X_data_all[steep_indices]
                Y_data_steep = Y_data_all[steep_indices]
            else:
                X_calc_steep = np.array([])
                Y_calc_steep = np.array([])
                X_data_steep = np.array([])
                Y_data_steep = np.array([])
        else:
            # Если только одна кривая, используем её класс для всех точек
            if curve_classes[0] == 0:
                X_calc_flat = X_calc_all
                Y_calc_flat = Y_calc_all
                X_data_flat = X_data_all
                Y_data_flat = Y_data_all
                X_calc_steep = np.array([])
                Y_calc_steep = np.array([])
                X_data_steep = np.array([])
                Y_data_steep = np.array([])
            else:
                X_calc_flat = np.array([])
                Y_calc_flat = np.array([])
                X_data_flat = np.array([])
                Y_data_flat = np.array([])
                X_calc_steep = X_calc_all
                Y_calc_steep = Y_calc_all
                X_data_steep = X_data_all
                Y_data_steep = Y_data_all
        
        # Обучение модели для пологих кривых
        if len(X_calc_flat) >= 30:
            print(f"Обучение модели для пологих кривых на {len(X_calc_flat)} точках...")
            self.model_flat.fit(X_calc_flat, Y_calc_flat, X_data_flat, Y_data_flat)
            self.n_samples_flat = len(X_calc_flat)
        else:
            print(f"Предупреждение: недостаточно точек для обучения модели пологих кривых ({len(X_calc_flat)} < 30)")
            self.n_samples_flat = 0
        
        # Обучение модели для крутых кривых
        if len(X_calc_steep) >= 30:
            print(f"Обучение модели для крутых кривых на {len(X_calc_steep)} точках...")
            self.model_steep.fit(X_calc_steep, Y_calc_steep, X_data_steep, Y_data_steep)
            self.n_samples_steep = len(X_calc_steep)
        else:
            print(f"Предупреждение: недостаточно точек для обучения модели крутых кривых ({len(X_calc_steep)} < 30)")
            self.n_samples_steep = 0
        
        self.is_fitted = True
        return self
    
    def predict(self, X_calc: np.ndarray, Y_calc: np.ndarray,
                P: np.ndarray, Q: np.ndarray,
                h: Optional[float] = None, L: Optional[float] = None, 
                W: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray, int]:
        """
        Применяет обученную модель к новым расчётным X-Y.
        
        Сначала классифицирует кривую на основе P, Q и параметров скважины, затем использует соответствующую модель.
        
        :param X_calc: Расчётные значения X
        :param Y_calc: Расчётные значения Y
        :param P: Давление (временной ряд) для классификации
        :param Q: Дебит (временной ряд) для классификации
        :param h: Толщина пласта (опционально)
        :param L: Длина трещины (опционально)
        :param W: Ширина трещины (опционально)
        :return: Кортеж (X_fitted, Y_fitted, curve_class) - подогнанные значения и класс кривой
        """
        if not self.is_fitted:
            raise RuntimeError("Модель не обучена. Вызовите fit() сначала.")
        
        # Классифицируем кривую на основе P, Q и параметров скважины
        curve_class = self.classifier.predict(P, Q, h=h, L=L, W=W)
        
        # Выбираем соответствующую модель
        if curve_class == 0:
            # Пологие кривые
            if self.model_flat.is_fitted:
                X_fitted, Y_fitted = self.model_flat.predict(X_calc, Y_calc)
            else:
                # Fallback: если модель не обучена, возвращаем исходные значения
                print("Предупреждение: модель для пологих кривых не обучена. Используются исходные значения.")
                X_fitted = X_calc.copy()
                Y_fitted = Y_calc.copy()
        else:
            # Крутые кривые
            if self.model_steep.is_fitted:
                X_fitted, Y_fitted = self.model_steep.predict(X_calc, Y_calc)
            else:
                # Fallback: если модель не обучена, возвращаем исходные значения
                print("Предупреждение: модель для крутых кривых не обучена. Используются исходные значения.")
                X_fitted = X_calc.copy()
                Y_fitted = Y_calc.copy()
        
        return X_fitted, Y_fitted, curve_class
    
    def get_classification_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о классификации кривой.
        
        :return: Словарь с информацией о классификаторе
        """
        return self.classifier.get_classification_info()
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о моделях аппроксимации.
        
        :return: Словарь с информацией о моделях
        """
        info = {
            "is_fitted": self.is_fitted,
            "n_samples_flat": self.n_samples_flat,
            "n_samples_steep": self.n_samples_steep,
            "model_flat_fitted": self.model_flat.is_fitted if hasattr(self.model_flat, 'is_fitted') else False,
            "model_steep_fitted": self.model_steep.is_fitted if hasattr(self.model_steep, 'is_fitted') else False,
        }
        
        if self.model_flat.is_fitted:
            metrics_flat = self.model_flat.get_metrics()
            info["metrics_flat"] = metrics_flat
        
        if self.model_steep.is_fitted:
            metrics_steep = self.model_steep.get_metrics()
            info["metrics_steep"] = metrics_steep
        
        return info
    
    def get_coefficients(self) -> Dict[str, Any]:
        """
        Возвращает коэффициенты обеих моделей.
        
        :return: Словарь с коэффициентами
        """
        coef_dict = {
            "classifier": self.classifier.get_classification_info(),
            "model_flat": {},
            "model_steep": {}
        }
        
        if self.model_flat.is_fitted:
            coef_dict["model_flat"] = self.model_flat.get_coefficients()
        
        if self.model_steep.is_fitted:
            coef_dict["model_steep"] = self.model_steep.get_coefficients()
        
        return coef_dict
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Возвращает метрики качества обеих моделей.
        
        :return: Словарь с метриками
        """
        metrics = {
            "n_samples_flat": self.n_samples_flat,
            "n_samples_steep": self.n_samples_steep,
        }
        
        if self.model_flat.is_fitted:
            metrics_flat = self.model_flat.get_metrics()
            metrics["flat"] = metrics_flat
        
        if self.model_steep.is_fitted:
            metrics_steep = self.model_steep.get_metrics()
            metrics["steep"] = metrics_steep
        
        return metrics
    
    def get_info(self) -> str:
        """
        Возвращает текстовую информацию о модели.
        
        :return: Строка с информацией
        """
        if not self.is_fitted:
            return "Модель не обучена"
        
        info_lines = []
        info_lines.append("=" * 60)
        info_lines.append("Бинарная модель аппроксимации кривых")
        info_lines.append("=" * 60)
        
        # Информация о классификаторе
        classifier_info = self.classifier.get_classification_info()
        info_lines.append(f"\nКлассификатор:")
        info_lines.append(f"  Тип: {classifier_info['classifier_type']}")
        info_lines.append(f"  Медиана пологости: {classifier_info['median_steepness']:.4f}")
        
        # Информация о модели для класса 0 (ужимать - расчётная круче)
        info_lines.append(f"\nМодель для класса 0 (ужимать - расчётная круче эталонной):")
        if self.model_flat.is_fitted:
            info_lines.append(self.model_flat.get_info())
        else:
            info_lines.append("  Не обучена")
        
        # Информация о модели для класса 1 (растягивать - расчётная положе)
        info_lines.append(f"\nМодель для класса 1 (растягивать - расчётная положе эталонной):")
        if self.model_steep.is_fitted:
            info_lines.append(self.model_steep.get_info())
        else:
            info_lines.append("  Не обучена")
        
        return "\n".join(info_lines)

