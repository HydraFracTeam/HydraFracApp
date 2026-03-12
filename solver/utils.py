# solver/utils.py
import pandas as pd
import numpy as np
from typing import Dict, List
from .models import CurveData, StaticParams


def build_library_from_dataframe(
    df: pd.DataFrame,
    static_cols: List[str] = ['h', 'N', 'W', 'L', 'a/L'],
    param_col: str = 'Skin',
    x_col: str = 'X',
    y_col: str = 'Y'
) -> Dict[StaticParams, Dict[float, CurveData]]:
    """
    Построение библиотеки кривых из DataFrame (твой legacy-формат).
    
    Returns:
        {StaticParams: {param_value: CurveData}}
    """
    library = {}
    
    # Группировка по статическим параметрам
    grouped = df.groupby(static_cols)
    
    for static_values, group in grouped:
        # Создаем StaticParams
        static = StaticParams(
            h=static_values[0],
            N=static_values[1],
            W=static_values[2],
            L=static_values[3],
            a_L=static_values[4]
        )
        
        # Внутри группы — по динамическому параметру
        param_groups = group.groupby(param_col)
        
        candidates = {}
        for param_val, param_group in param_groups:
            sorted_group = param_group.sort_values(x_col)
            curve = CurveData(
                x=sorted_group[x_col].values.astype(float),
                y=sorted_group[y_col].values.astype(float)
            )
            candidates[float(param_val)] = curve
        
        if len(candidates) > 1:  # Только если есть варианты для выбора
            library[static] = candidates
    
    return library


def filter_library(
    library: Dict[StaticParams, Dict[float, CurveData]],
    **kwargs
) -> Dict[StaticParams, Dict[float, CurveData]]:
    """
    Фильтрация библиотеки по значениям статических параметров.
    
    Пример:
        filtered = filter_library(lib, h=10.0, N=5)
    """
    result = {}
    for static, candidates in library.items():
        match = all(
            getattr(static, key) == value 
            for key, value in kwargs.items()
        )
        if match:
            result[static] = candidates
    return result