from parser.export.naming.base import ResultNamingStrategy
from pathlib import Path

class SingleFileNamingStrategy(ResultNamingStrategy):
    def __init__(self, path: str):
        self.path = path

    def get_storage_key(self, *, url: str | None = None) -> str:
        # Всегда возвращаем один файл
        return self.path
