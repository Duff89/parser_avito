from abc import ABC, abstractmethod
from models import Item


class ResultStorage(ABC):
    """
    Отвечает ТОЛЬКО за сохранение результатов парсинга
    (Excel, CSV, API, etc)
    """
    name: str = "unknown"

    @abstractmethod
    def save(self, ads: list[Item]) -> None:
        """Сохраняет результаты"""
        pass
