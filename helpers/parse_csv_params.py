import pandas as pd

from schemas.required_params import RequiredParams


def parse_csv_params(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    required_params_dict = {}
    for param in df.columns:
        required_params_dict[param] = df[param].iloc[1]
    
    required_fields = set(RequiredParams.model_fields.keys())
    available_fields = set(df.columns)
    
    missing_fields = required_fields - available_fields
    extra_fields = available_fields - required_fields
    
    if missing_fields:
        error_msg = "Отсутствуют обязательные параметры:\n" + ", ".join(missing_fields)
        return None, error_msg
    elif extra_fields:
        error_msg = "Прусутствуют посторонние параметры:\n" + ", ".join(extra_fields)
        return None, error_msg
    
    required_params = RequiredParams(**required_params_dict)

    return df, None

