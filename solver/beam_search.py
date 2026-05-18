# solver/beam_search.py
import logging
logger = logging.getLogger(__name__)
def select_top_k(scores: dict, k: int = 5):
    """
    Выбирает топ-k элементов по возрастанию значения.
    Возвращает список из k ключей с минимальными значениями.
    """
    if not scores:
        return []
    sorted_items = sorted(scores.items(), key=lambda x: x[1])
    return [item[0] for item in sorted_items[:k]]