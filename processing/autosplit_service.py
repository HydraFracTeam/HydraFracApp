"""
Сервис автосплиттера — применение выбранного режима КСД/КВД к данным.
"""
from typing import Optional, Tuple
from core.models import RawDynamicData


# Режимы автосплиттера
MODE_KSD = "ksd"
MODE_KVD = "kvd"
MODE_BOTH = "both"
MODE_IGNORE = "ignore"


def apply_autosplit(
    raw: RawDynamicData,
    split_info: dict,
    mode: str,
) -> Tuple[RawDynamicData, Optional[str], Optional[dict]]:
    """
    Применяет выбранный режим автосплиттера к данным.

    Args:
        raw: исходные данные (модифицируются in-place)
        split_info: словарь с информацией о разделении (index, time, pressure, ...)
        mode: режим — MODE_KSD, MODE_KVD, MODE_BOTH, MODE_IGNORE

    Returns:
        (raw, report_message, autosplit_info)
        - raw: данные после применения режима
        - report_message: текст для отчёта (или None)
        - autosplit_info: split_info если режим BOTH, иначе None
    """
    split_idx = split_info.get('index', len(raw.t) // 2)

    if mode == MODE_KSD:
        raw.t = raw.t[:split_idx]
        raw.P = raw.P[:split_idx]
        if hasattr(raw, 'Q') and raw.Q is not None:
            raw.Q = raw.Q[:split_idx]
        return raw, f"Выбран режим КСД: использованы точки 0-{split_idx}", None

    elif mode == MODE_KVD:
        raw.t = raw.t[split_idx:]
        raw.P = raw.P[split_idx:]
        if hasattr(raw, 'Q') and raw.Q is not None:
            raw.Q = raw.Q[split_idx:]
        return raw, f"Выбран режим КВД: использованы точки {split_idx}-end", None

    elif mode == MODE_BOTH:
        msg = (
            f"⚠ Использованы все данные (КСД + КВД). "
            f"Подбор может быть некорректным!"
        )
        return raw, msg, split_info

    elif mode == MODE_IGNORE:
        return raw, "Автосплиттер отключен.", None

    else:
        return raw, None, None
