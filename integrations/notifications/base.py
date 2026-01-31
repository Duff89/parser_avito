from abc import ABC, abstractmethod

from integrations.notifications.utils import escape_markdown_v2, get_price
from models import Item


class Notifier(ABC):

    @abstractmethod
    def notify(self, ad: Item = None, message: str = None):
        """Отправляем одно объявление"""
        pass

    def notify_many(self, ads: list[Item]):
        """Отправляем список объявлений"""
        for ad in ads:
            self.notify(ad=ad)

    # default форматирование
    def format(self, ad: Item) -> str:
        price = escape_markdown_v2(get_price(ad))
        title = escape_markdown_v2(getattr(ad, "title", ""))
        seller = escape_markdown_v2(str(getattr(ad, "sellerId", "")))
        short_url = f"https://avito.ru/{getattr(ad, 'id', '')}"

        parts = []

        if price:
            part = f"*{price}*"
            if getattr(ad, "isPromotion", False):
                part += " 🢁"
            parts.append(part)

        if title:
            parts.append(f"[{title}]({short_url})")

        if seller:
            parts.append(f"Продавец: {seller}")

        return "\n".join(parts)
