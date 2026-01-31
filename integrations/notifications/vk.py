import requests
from loguru import logger

from integrations.notifications.base import Notifier
from integrations.notifications.transport import send_with_retries
from integrations.notifications.utils import get_first_image
from models import Item


class VKNotifier(Notifier):
    def __init__(self, vk_token: str, user_id: str | int):
        self.vk_token = vk_token
        self.user_id = user_id

    def notify_message(self, message: str):
        def _send():
            headers = {
                "Authorization": f"Bearer {self.vk_token}"
            }
            return requests.post(
                "https://api.vk.com/method/messages.send",
                headers=headers,
                json={
                    "domain": self.user_id,
                    "random_id": 0,
                    "message": message,
                    "v": "5.199"
                },
                timeout=10,
            )

        send_with_retries(_send)

    def notify_ad(self, ad: Item):
        def _send():
            message = self.format_ad(ad)
            _image_url = get_first_image(ad=ad)

            # Загружаем фото если есть
            attachment = None
            if _image_url:
                attachment = self.__upload_photo_to_vk(_image_url, str(self.user_id))
            payload = {
                "domain": self.user_id,
                "random_id": 0,
                "message": message,
                "v": "5.199"
            }
            if attachment:
                payload["attachment"] = attachment

            headers = {
                "Authorization": f"Bearer {self.vk_token}"
            }

            return requests.post(
                "https://api.vk.com/method/messages.send",
                json=payload,
                headers=headers,
                timeout=10,
            )

        response = send_with_retries(_send)
        if response is None:
            logger.warning("VK: не удалось отправить сообщение")
            return

        body = response.json()

        if "error" in body:
            error_msg = body["error"].get("error_msg", "Unknown error")
            error_code = body["error"].get("error_code", 0)
            logger.warning(f"VK API error {error_code}: {error_msg}")
            return

        logger.debug(f"Сообщение успешно отправлено")

    def notify(self, ad: Item = None, message: str = None):
        if ad:
            return self.notify_ad(ad=ad)
        return self.notify_message(message=message)

    def __upload_photo_to_vk(self, photo_url: str, user_id: str) -> str | None:
        """Загружает фото по URL и возвращает attachment для messages.send"""
        headers = {"Authorization": f"Bearer {self.vk_token}"}

        try:
            # Шаг 1: Получаем URL для загрузки
            upload_server_response = requests.post(
                "https://api.vk.com/method/photos.getMessagesUploadServer",
                headers=headers,
                data={"v": "5.199"}
            ).json()

            if "error" in upload_server_response:
                logger.warning(f"VK upload server error: {upload_server_response['error']}")
                return None

            upload_url = upload_server_response["response"]["upload_url"]

            # Шаг 2: Скачиваем фото и загружаем на VK
            photo_data = requests.get(photo_url, timeout=10).content
            upload_response = requests.post(
                upload_url,
                files={"photo": ("photo.jpg", photo_data, "image/jpeg")}
            ).json()

            if not upload_response.get("photo") or upload_response.get("photo") == "[]":
                logger.warning("VK: фото не загружено")
                return None

            # Шаг 3: Сохраняем фото
            save_response = requests.post(
                "https://api.vk.com/method/photos.saveMessagesPhoto",
                headers=headers,
                data={
                    "photo": upload_response["photo"],
                    "server": upload_response["server"],
                    "hash": upload_response["hash"],
                    "v": "5.199"
                }
            ).json()

            if "error" in save_response:
                logger.warning(f"VK save photo error: {save_response['error']}")
                return None

            # Возвращаем attachment в формате photo{owner_id}_{id}
            photo_info = save_response["response"][0]
            attachment = f"photo{photo_info['owner_id']}_{photo_info['id']}"
            logger.debug(f"VK: фото загружено, attachment: {attachment}")
            return attachment

        except Exception as e:
            logger.warning(f"Error uploading photo to VK: {e}")
            return None

    @staticmethod
    def format_ad(ad: Item) -> str:
        """Форматирует объявление в простой текст для VK (без Markdown)"""

        def clean(text: str) -> str:
            if not text:
                return ""
            return str(text).replace("\xa0", " ")

        price = clean(
            getattr(ad, "priceDetailed", {}).get("value", "") if isinstance(getattr(ad, "priceDetailed", None),
                                                                            dict) else getattr(ad.priceDetailed,
                                                                                               "value",
                                                                                               getattr(ad,
                                                                                                       "priceDetailed",
                                                                                                       "")))
        title = clean(getattr(ad, "title", ""))
        short_url = f"https://avito.ru/{getattr(ad, 'id', '')}"
        seller = clean(str(getattr(ad, "sellerId", ""))) if getattr(ad, "sellerId", None) else ""

        parts = []
        if price:
            price_part = f"💰 {price}"
            if getattr(ad, "isPromotion", False):
                price_part += " 🔥"
            parts.append(price_part)

        if title:
            parts.append(f"📦 {title}")

        if seller:
            parts.append(f"👤 Продавец: {seller}")

        if short_url:
            parts.append(f"🔗 {short_url}")

        message = "\n".join(parts)
        return message
