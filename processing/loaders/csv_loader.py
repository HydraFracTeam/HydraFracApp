# processing/csv_loader.py

import pandas as pd
import numpy as np
from pydantic import ValidationError

from schemas.raw_dynamic_input import RawDynamicDataInput
from core.models import RawDynamicData


def load_dynamic_data_from_csv(file_path: str) -> RawDynamicData:
    """
    Загрузка динамических данных из csv файла
    """

    df = pd.read_csv(file_path)

    df.columns = [c.strip().lower() for c in df.columns]

    if "t" not in df.columns or "p" not in df.columns:
        raise ValueError("CSV файл обязательно должен содержать колонки: t, P")

    t = df["t"].tolist()
    P = df["p"].tolist()

    Q = df["q"].tolist() if "q" in df.columns else None

    # Валидация через pydantic модель
    try:
        validated = RawDynamicDataInput(
            t=t,
            P=P,
            Q=Q
        )
    except ValidationError as e:
        # Формируем понятные сообщения об ошибках для пользователя
        error_messages = []
        for error in e.errors():
            error_messages.append(error['msg'])
        
        # Объединяем все сообщения об ошибках в одно
        combined_message = "; ".join(error_messages)
        raise ValueError(combined_message)

    # Сохраняем в датакласс для последующей работы
    return RawDynamicData(
        t=np.asarray(validated.t, dtype=float),
        P=np.asarray(validated.P, dtype=float),
        Q=np.asarray(validated.Q, dtype=float) if validated.Q else None,
        is_Q_in_dynamic_input=validated.Q is not None,
        source_file=file_path
    )
