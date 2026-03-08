from pathlib import Path


def get_file_suffix(file_path: str) -> str:
    return Path(file_path).suffix.lower()
