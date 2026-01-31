from abc import ABC, abstractmethod

from models import Item

class ResultNamingStrategy(ABC):

    @abstractmethod
    def get_storage_key(self, *, url: str | None = None) -> str:
        """
        Возвращает ключ хранилища:
        - путь к файлу
        - id бакета
        """
        pass
