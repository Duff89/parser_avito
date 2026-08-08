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

    def get_user_agent(self) -> str | None:
        """Return the user agent associated with the current cookies, if any."""
        return None

    def get_fingerprint(self) -> dict | None:
        """Return the HTTP client profile associated with the current cookies."""
        return None

    @abstractmethod
    def handle_block(self):
        """
        Что делать, если cookies заблокированы
        """
        pass

