import requests

from integrations.notifications.base import Notifier
from integrations.notifications.transport import send_with_retries
from integrations.notifications.utils import get_first_image
from models import Item


class TelegramNotifier(Notifier):
    def __init__(self, bot_token: str, chat_id: str, proxy: str = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.proxy = self.get_proxy(proxy=proxy)

    @staticmethod
    def get_proxy(proxy: str = None):
        if proxy:
            return {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }
        return None


    def notify_message(self, message: str):
        def _send():
            return requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "MarkdownV2",
                },
                proxies=self.proxy,
                timeout=10,
            )

        send_with_retries(_send)

    def notify_ad(self, ad: Item):
        def _send():
            message = self.format(ad)
            return requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendPhoto",
                json={
                    "chat_id": self.chat_id,
                    "caption": message,
                    "photo": get_first_image(ad=ad),
                    "parse_mode": "MarkdownV2",
                    "disable_web_page_preview": True,
                },
                proxies=self.proxy,
                timeout=10,
            )

        send_with_retries(_send)

    def notify(self, ad: Item = None, message: str = None):
        if ad:
            return self.notify_ad(ad=ad)
        return self.notify_message(message=message)
