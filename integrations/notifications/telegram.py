import requests
from loguru import logger

from integrations.notifications.base import Notifier
from integrations.notifications.transport import send_with_retries
from integrations.notifications.utils import get_first_image
from models import Item


class TelegramNotifier(Notifier):
    def __init__(self, bot_token: str, chat_id: str, proxy: str = None, only_text: bool = False):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.proxy = self.get_proxy(proxy=proxy)
        self.only_text = only_text

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

    def _send_text_fallback(self, message: str) -> None:
        def _send():
            return requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "MarkdownV2",
                    "disable_web_page_preview": True,
                },
                proxies=self.proxy,
                timeout=10,
            )

        send_with_retries(_send)

    def _send_photo_bytes(self, image_url: str, message: str) -> bool:
        """Download the image locally and re-upload to Telegram as multipart.

        Returns True on success, False if the image could not be downloaded.
        """
        try:
            img_resp = requests.get(image_url, proxies=self.proxy, timeout=15)
            img_resp.raise_for_status()
            image_bytes = img_resp.content
        except requests.RequestException as e:
            logger.warning(f"[notify] could not download image for multipart upload: {e}")
            return False

        def _send():
            return requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendPhoto",
                data={
                    "chat_id": self.chat_id,
                    "caption": message,
                    "parse_mode": "MarkdownV2",
                },
                files={"photo": ("photo.jpg", image_bytes, "image/jpeg")},
                proxies=self.proxy,
                timeout=30,
            )

        send_with_retries(_send)
        return True

    def notify_ad(self, ad: Item):
        message = self.format(ad)

        def _send():
            if self.only_text:
                return requests.post(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": message,
                        "parse_mode": "MarkdownV2",
                        "disable_web_page_preview": True,
                    },
                    proxies=self.proxy,
                    timeout=10,
                )

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

        try:
            send_with_retries(_send)
        except requests.HTTPError as e:
            resp = e.response
            if not self.only_text and resp is not None and resp.status_code == 400:
                image_url = get_first_image(ad=ad)
                if image_url:
                    logger.info("[notify] sendPhoto URL rejected (400), retrying with image bytes")
                    uploaded = self._send_photo_bytes(image_url=image_url, message=message)
                    if not uploaded:
                        logger.warning("[notify] multipart upload also failed, falling back to text-only")
                        self._send_text_fallback(message=message)
                    return
            raise

    def notify(self, ad: Item = None, message: str = None):
        if ad:
            return self.notify_ad(ad=ad)
        return self.notify_message(message=message)
