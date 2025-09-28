import requests
import time

from loguru import logger

from models import Item


class SendAdToTg:
    def __init__(self, bot_token: str, chat_id: list, max_retries: int = 5, retry_delay: int = 5):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def __send_to_tg(self, chat_id: str | int, ad: Item = None, msg: str = None):
        if msg:
            message = msg
            self.max_retries = 2
        else:
            message = self.format_ad(ad)

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(self.api_url, json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "markdown"
                })
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
    def format_ad(ad: Item) -> str:
        full_url = f"https://avito.ru/{ad.urlPath}"
        short_url = f"https://avito.ru/{ad.id}"
        message = (
                f"*{ad.priceDetailed.value}*" + ("🢁" if ad.isPromotion else "")
                + f"\n[{ad.title}]({full_url})\n{short_url}\n"
                + (f"Продавец: {ad.sellerId}\n" if ad.sellerId else "")

        )
        return message
