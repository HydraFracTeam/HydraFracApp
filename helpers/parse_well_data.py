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
        print(f"Загрузка файла: {file_path}")
        
        # Определяем тип файла по расширению
        if file_path.lower().endswith('.parquet'):
            df = pd.read_parquet(file_path)
        else:
            # Для CSV файлов указываем кодировку и разделитель
            try:
                df = pd.read_csv(file_path, encoding='utf-8', sep=',', low_memory=False)
            except UnicodeDecodeError:
                # Пробуем другие кодировки
                df = pd.read_csv(file_path, encoding='cp1251', sep=',', low_memory=False)
        
        print(f"Файл загружен: {len(df)} строк, {len(df.columns)} колонок")
        
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
        print("Очистка данных...")
        # Очищаем данные от NaN и inf значений
        df = df.replace([np.inf, -np.inf], np.nan)
        initial_rows = len(df)
        df = df.dropna(subset=['t', 'P', 'Q'])  # Удаляем строки с NaN в ключевых колонках
        
        if len(df) == 0:
            return None, "После очистки данных не осталось валидных строк"
        
        removed_rows = initial_rows - len(df)
        if removed_rows > 0:
            print(f"Удалено {removed_rows} строк с некорректными данными")
        
        print(f"Группировка данных по параметрам скважин...")
        # Группируем данные по параметрам скважины
        well_groups = group_data_by_well_parameters(df)
        
        if not well_groups:
            return None, "Не удалось сгруппировать данные по параметрам скважин"
        
        # Создаем WellTimeSeries для каждой группы
        print(f"Найдено {len(well_groups)} групп данных")
        time_series_list = []
        
        for group_idx, (group_id, group_data) in enumerate(well_groups.items()):
            print(f"Обработка группы {group_idx + 1}/{len(well_groups)}: {len(group_data)} точек")
            
            if len(group_data) < 2:  # Минимум 2 точки для временного ряда
                print(f"  Пропуск группы {group_id}: недостаточно точек")
                continue
                
            # Сортируем по времени
            group_data = group_data.sort_values('t')
            
            # Проверяем, что данные корректны
            if group_data['t'].isna().any() or group_data['P'].isna().any() or group_data['Q'].isna().any():
                print(f"  Пропуск группы {group_id}: содержит NaN значения")
                continue
            
            try:
                # Создаем временные ряды
                time_series = WellTimeSeries(
                    time=group_data['t'].reset_index(drop=True),
                    pressure=group_data['P'].reset_index(drop=True),
                    flow_rate=group_data['Q'].reset_index(drop=True),
                    skin=float(group_data['Skin'].iloc[0]),
                    thickness=float(group_data['h'].iloc[0]),
                    fractures_count=int(group_data['N'].iloc[0]),
                    fracture_width=float(group_data['W'].iloc[0]),
                    fracture_length=float(group_data['L'].iloc[0]),
                    a_l_ratio=float(group_data['a/L'].iloc[0])
                )
                time_series_list.append(time_series)
                print(f"  ✓ Группа {group_id} успешно создана")
            except (ValueError, TypeError) as e:
                print(f"  ✗ Ошибка создания временного ряда для группы {group_id}: {e}")
                continue
        
        if not time_series_list:
            return None, "Не удалось создать временные ряды из данных"
        
        return time_series_list, None
        
    except Exception as exc:
        return None, f"Ошибка обработки данных: {exc}"


def group_data_by_well_parameters(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Группирует данные по параметрам скважины.
    Уникальная комбинация Skin, h, N, W, L, a/L определяет один сценарий.
    Для каждого сценария строки с разными ElemIdx, t, P, dP, Q описывают изменения по времени.
    Возвращает словарь {group_id: group_data}
    """
    # Параметры для группировки (определяют уникальный сценарий)
    grouping_params = ['Skin', 'h', 'N', 'W', 'L', 'a/L']
    
    # Проверяем наличие необходимых колонок
    missing_columns = [col for col in grouping_params if col not in df.columns]
    if missing_columns:
        print(f"Предупреждение: отсутствуют колонки для группировки: {missing_columns}")
        return {"well_0": df}
    
    try:
        # Создаем копию DataFrame для группировки
        df_copy = df.copy()
        
        # Округляем значения для группировки близких параметров
        for param in grouping_params:
            if df_copy[param].dtype in [np.float64, np.float32]:
                # Округляем числовые параметры до 4 знаков
                df_copy[f'{param}_rounded'] = df_copy[param].round(4)
            else:
                # Для нечисловых параметров просто копируем
                df_copy[f'{param}_rounded'] = df_copy[param]
        
        # Получаем список округленных параметров для группировки
        rounded_params = [f'{param}_rounded' for param in grouping_params]
        
        # Группируем данные по уникальным комбинациям параметров
        grouped = df_copy.groupby(rounded_params, dropna=False)
        
        print(f"Найдено {len(grouped)} уникальных сценариев (комбинаций параметров скважин)")
        
        groups = {}
        for i, (params, group) in enumerate(grouped):
            # Удаляем временные колонки с округлением
            group_clean = group.drop(columns=[col for col in group.columns if col.endswith('_rounded')], errors='ignore')
            
            # Сортируем по времени для правильного отображения изменений
            if 't' in group_clean.columns:
                group_clean = group_clean.sort_values('t')
                
            groups[f"well_{i}"] = group_clean.reset_index(drop=True)
            
            # Формируем информацию о группе
            param_info = []
            for j, param in enumerate(grouping_params):
                if isinstance(params, tuple):
                    value = params[j]
                else:
                    value = params
                param_info.append(f"{param}={value}")
            
            print(f"  Сценарий {i}: {', '.join(param_info)}, {len(group_clean)} точек")
        
        return groups
        
    except Exception as e:
        print(f"Ошибка группировки данных: {e}")
        import traceback
        traceback.print_exc()
        # Возвращаем все данные как одну группу в случае ошибки
        return {"well_0": df}


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
