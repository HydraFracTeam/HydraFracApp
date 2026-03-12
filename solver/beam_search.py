import numpy as np


def select_top_k(scores, k):

    items = sorted(scores.items(), key=lambda x: x[1])

    return [x[0] for x in items[:k]]