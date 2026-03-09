def calculate_L_value(L_min: float, L_max: float) -> float:
    """
    Вычисляет начальное значение длины трещины как среднее между границами
    """
    return (L_min + L_max) / 2
