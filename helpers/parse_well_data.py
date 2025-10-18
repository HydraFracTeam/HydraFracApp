import pandas as pd
from typing import Optional, Tuple, List, Dict
import numpy as np

from schemas.well_data import WellData, WellTimeSeries


def parse_well_data(file_path: str) -> Tuple[Optional[List[WellTimeSeries]], Optional[str]]:
    """
    Парсит файл с данными разведки месторождений (CSV или Parquet) и создает список WellTimeSeries.
    Ожидает формат: Skin, h, N, W, L, a/L, ElemIdx, X, Y, t, P, dP, Q
    Поддерживает несколько групп данных с разными параметрами скважин.
    """
    if not file_path:
        return None, "Файл не выбран"

    try:
        # Определяем тип файла по расширению
        if file_path.lower().endswith('.parquet'):
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_csv(file_path)
    except Exception as exc:
        return None, f"Ошибка чтения файла: {exc}"

    if df.shape[0] < 1:
        return None, "Недостаточно строк в файле"

    # Проверяем наличие обязательных колонок
    required_columns = ['Skin', 'h', 'N', 'W', 'L', 'a/L', 'ElemIdx', 'X', 'Y', 't', 'P', 'dP', 'Q']
    available_columns = list(df.columns)
    
    missing_columns = [col for col in required_columns if col not in available_columns]
    if missing_columns:
        return None, f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}"

    try:
        # Группируем данные по параметрам скважины
        well_groups = group_data_by_well_parameters(df)
        
        if not well_groups:
            return None, "Не удалось сгруппировать данные по параметрам скважин"
        
        # Создаем WellTimeSeries для каждой группы
        time_series_list = []
        for group_id, group_data in well_groups.items():
            if len(group_data) < 2:  # Минимум 2 точки для временного ряда
                continue
                
            # Сортируем по времени
            group_data = group_data.sort_values('t')
            
            # Создаем временные ряды
            time_series = WellTimeSeries(
                time=group_data['t'],
                pressure=group_data['P'],
                flow_rate=group_data['Q'],
                skin=float(group_data['Skin'].iloc[0]),
                thickness=float(group_data['h'].iloc[0]),
                fractures_count=int(group_data['N'].iloc[0]),
                fracture_width=float(group_data['W'].iloc[0]),
                fracture_length=float(group_data['L'].iloc[0]),
                a_l_ratio=float(group_data['a/L'].iloc[0])
            )
            time_series_list.append(time_series)
        
        if not time_series_list:
            return None, "Не удалось создать временные ряды из данных"
        
        return time_series_list, None
        
    except Exception as exc:
        return None, f"Ошибка обработки данных: {exc}"


def group_data_by_well_parameters(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Группирует данные по параметрам скважины.
    Возвращает словарь {group_id: group_data}
    """
    # Параметры для группировки
    grouping_params = ['Skin', 'h', 'N', 'W', 'L', 'a/L']
    
    # Создаем группировку с учетом небольшой погрешности для числовых параметров
    tolerance = 1e-6
    
    groups = {}
    group_id = 0
    
    for idx, row in df.iterrows():
        # Ищем существующую группу с похожими параметрами
        found_group = None
        
        for existing_group_id, existing_group in groups.items():
            # Проверяем, подходят ли параметры к существующей группе
            if all(abs(row[param] - existing_group[param].iloc[0]) <= tolerance 
                   for param in grouping_params):
                found_group = existing_group_id
                break
        
        if found_group is not None:
            # Добавляем к существующей группе
            groups[found_group] = pd.concat([groups[found_group], row.to_frame().T], ignore_index=True)
        else:
            # Создаем новую группу
            groups[f"well_{group_id}"] = row.to_frame().T
            group_id += 1
    
    return groups


def analyze_well_groups(df: pd.DataFrame) -> Dict[str, any]:
    """
    Анализирует группы данных в файле и возвращает статистику.
    """
    groups = group_data_by_well_parameters(df)
    
    analysis = {
        'total_groups': len(groups),
        'total_points': len(df),
        'groups_info': []
    }
    
    for group_id, group_data in groups.items():
        group_info = {
            'group_id': group_id,
            'points_count': len(group_data),
            'skin': float(group_data['Skin'].iloc[0]),
            'thickness': float(group_data['h'].iloc[0]),
            'fractures': int(group_data['N'].iloc[0]),
            'fracture_width': float(group_data['W'].iloc[0]),
            'fracture_length': float(group_data['L'].iloc[0]),
            'a_l_ratio': float(group_data['a/L'].iloc[0]),
            'time_range': (float(group_data['t'].min()), float(group_data['t'].max())),
            'pressure_range': (float(group_data['P'].min()), float(group_data['P'].max())),
            'flow_rate_range': (float(group_data['Q'].min()), float(group_data['Q'].max()))
        }
        analysis['groups_info'].append(group_info)
    
    return analysis


def parse_well_csv(file_path: str) -> Tuple[Optional[List[WellTimeSeries]], Optional[str]]:
    """
    Парсит CSV файл с данными разведки месторождений и создает список WellTimeSeries.
    Ожидает формат: Skin, h, N, W, L, a/L, ElemIdx, X, Y, t, P, dP, Q
    """
    return parse_well_data(file_path)  # Используем общую функцию


def parse_well_data_row(row: pd.Series) -> Optional[WellData]:
    """
    Парсит одну строку данных в объект WellData.
    """
    try:
        return WellData(
            skin=float(row['Skin']),
            h=float(row['h']),
            n=int(row['N']),
            w=float(row['W']),
            l=float(row['L']),
            a_l=float(row['a/L']),
            elem_idx=int(row['ElemIdx']),
            x=float(row['X']),
            y=float(row['Y']),
            t=float(row['t']),
            p=float(row['P']),
            dp=float(row['dP']),
            q=float(row['Q'])
        )
    except Exception:
        return None


def validate_well_data(df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
    """
    Валидирует данные скважины на корректность.
    """
    # Проверяем физическую корректность данных
    if (df['P'] <= 0).any():
        return False, "Давление должно быть положительным"
    
    if (df['h'] <= 0).any():
        return False, "Толщина пласта должна быть положительной"
    
    if (df['N'] < 1).any():
        return False, "Количество трещин должно быть не менее 1"
    
    if (df['W'] <= 0).any():
        return False, "Ширина трещины должна быть положительной"
    
    if (df['L'] <= 0).any():
        return False, "Длина трещины должна быть положительной"
    
    if (df['a/L'] <= 0).any() or (df['a/L'] > 1).any():
        return False, "Отношение a/L должно быть в диапазоне (0, 1]"
    
    # Проверяем монотонность времени
    if not df['t'].is_monotonic_increasing:
        return False, "Время должно быть монотонно возрастающим"
    
    return True, None


def extract_well_parameters(df: pd.DataFrame) -> dict:
    """
    Извлекает параметры скважины из DataFrame.
    """
    first_row = df.iloc[0]
    return {
        'skin': float(first_row['Skin']),
        'thickness': float(first_row['h']),
        'fractures_count': int(first_row['N']),
        'fracture_width': float(first_row['W']),
        'fracture_length': float(first_row['L']),
        'a_l_ratio': float(first_row['a/L']),
        'total_elements': len(df),
        'time_range': (float(df['t'].min()), float(df['t'].max())),
        'pressure_range': (float(df['P'].min()), float(df['P'].max())),
        'flow_rate_range': (float(df['Q'].min()), float(df['Q'].max()))
    }
