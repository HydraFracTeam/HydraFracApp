from pathlib import Path


def get_filename(file_path: str) -> str:
    return Path(file_path).name
