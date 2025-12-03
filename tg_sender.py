import requests
import time
import re

from loguru import logger

from models import Item


class SendAdToTg:
    def __init__(self, bot_token: str, chat_id: list, max_retries: int = 5, retry_delay: int = 5):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @staticmethod
    def escape_markdown(text: str) -> str:
        """Экранирует спецсимволы MarkdownV2, кроме """
        if not text:
            return ""
        text = str(text).replace("\xa0", " ")
        return re.sub(r'([_\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

    def __send_to_tg(self, chat_id: str | int, ad: Item = None, msg: str = None):
        if msg:
            payload = {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "MarkdownV2",
            }
            return requests.post(f"https://api.telegram.org/bot{self.bot_token}/sendMessage", json=payload)
        else:
            message = self.format_ad(ad)

        _image_url = self.get_first_image(ad=ad)
        for attempt in range(1, self.max_retries + 1):
            try:
                payload = {
                    "chat_id": chat_id,
                    "caption": message,
                    "photo": _image_url,
                    "parse_mode": "MarkdownV2",
                    "disable_web_page_preview": True,
                }
                logger.info(payload)

                response = requests.post(self.api_url, json=payload)
                if response.status_code == 400:
                    logger.warning("Не удалось отправить сообщение. Проверьте правильность введенных данных")
                    break

                response.raise_for_status()
                logger.debug(f"Сообщение успешно отправлено (попытка {attempt})")
                break
            except requests.RequestException as e:
                logger.debug(f"Ошибка при отправке (попытка {attempt}): {e}")
                logger.debug(message)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.debug("Не удалось отправить сообщение после всех попыток.")

    def send_to_tg(self, ad: Item = None, msg: str = None):
        for chat_id in self.chat_id:
            self.__send_to_tg(chat_id=chat_id, ad=ad, msg=msg)

    @staticmethod
    def get_first_image(ad: Item):
        def get_largest_image_url(img):
            best_key = max(
                img.root.keys(),
                key=lambda k: int(k.split("x")[0]) * int(k.split("x")[1])
            )
            return str(img.root[best_key])

        images_urls = [get_largest_image_url(img) for img in ad.images]
        if images_urls:
            return images_urls[0]


    @staticmethod
    def format_ad(ad: Item) -> str:
        def esc(text: str) -> str:
            if not text:
                return ""
            s = str(text).replace("\xa0", " ")
            return re.sub(r'([_\[\]()~`>#+\-=|{}.!])', r'\\\1', s)

        price = esc(getattr(ad, "priceDetailed", {}).get("value", "") if isinstance(getattr(ad, "priceDetailed", None),
                                                                                    dict) else getattr(ad.priceDetailed,
                                                                                                       "value",
                                                                                                       getattr(ad,
                                                                                                               "priceDetailed",
                                                                                                               "")))
        title = esc(getattr(ad, "title", ""))
        short_url = f"https://avito.ru/{getattr(ad, 'id', '')}"
        seller = esc(str(getattr(ad, "sellerId", ""))) if getattr(ad, "sellerId", None) else ""

        parts = []
        if price:
            price_part = f"*{price}*"
            if getattr(ad, "isPromotion", False):
                price_part += " 🢁"
            parts.append(price_part)

        if title:
            parts.append(f"[{title}]({short_url})")

        if seller:
            parts.append(f"Продавец: {seller}")

        message = "\n".join(parts)
        return message
