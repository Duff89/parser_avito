from abc import ABC, abstractmethod
from typing import Dict

import httpx


class CookiesProvider(ABC):

    @abstractmethod
    def get(self) -> Dict[str, str]:
        pass

    def update(self, response: httpx.Response) -> None:
        """
        Обновить cookies после запроса.
        По умолчанию — ничего не делать.
        """
        pass

    @abstractmethod
    def handle_block(self):
        """
        Что делать, если cookies заблокированы
        """
        pass

