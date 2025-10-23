import os
import pickle
from typing import Any

def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def save_to_file(data: Any, file_path: str) -> None:
    with open(file_path, 'wb') as file:
        pickle.dump(data, file)

def load_from_file(file_path: str) -> Any:
    with open(file_path, 'rb') as file:
        return pickle.load(file)