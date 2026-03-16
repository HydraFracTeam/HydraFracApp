import numpy as np


def select_top_k(scores, k):
    """
    Выбор top-k лучших элементов из словаря по значениям.
    
    Args:
        scores (Dict): Словарь {ключ: значение_ошибки}
        k (int): Количество лучших элементов для возврата
        
    Returns:
        List: Список из k лучших ключей (отсортированных по возрастанию ошибки)
    """

    items = sorted(scores.items(), key=lambda x: x[1])

    return [x[0] for x in items[:k]]
