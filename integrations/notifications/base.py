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
        seller_display = getattr(ad, "sellerName", None) or getattr(ad, "sellerId", "")
        seller = escape_markdown_v2(str(seller_display)) if seller_display else ""
        short_url = f"https://avito.ru/{getattr(ad, 'id', '')}"

        parts = []

        if getattr(ad, "old_price", None) is not None and getattr(ad, "priceDetailed", None) and getattr(ad.priceDetailed, "value", None) is not None:
            new_val = ad.priceDetailed.value
            old_val = ad.old_price
            old_formatted = f"{old_val:,}".replace(",", " ") + " ₽"
            new_formatted = f"{new_val:,}".replace(",", " ") + " ₽"
            arrow = "📉" if new_val < old_val else "📈"
            price_change_text = escape_markdown_v2(f"{arrow} {old_formatted} ➔ {new_formatted}")
            part = f"*{price_change_text}*"
            if getattr(ad, "isPromotion", False):
                part += " 🢁"
            parts.append(part)
        elif price:
            part = f"*{price}*"
            if getattr(ad, "isPromotion", False):
                part += " 🢁"
            parts.append(part)

        if title:
            parts.append(f"[{title}]({short_url})")

        if seller:
            parts.append(f"Продавец: {seller}")

        return "\n".join(parts)
