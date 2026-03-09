
def calculate_k_value(k_min: float, k_max: float) -> float:
    """
    Вычисляет начальное значение проницаемости как среднее между границами
    """
    return (k_min + k_max) / 2
