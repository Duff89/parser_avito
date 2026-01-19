import requests
import time
import re

from loguru import logger

from models import Item


class SendAdToVK:
    def __init__(self, vk_token: str, user_id: list, max_retries: int = 5, retry_delay: int = 5):
        self.vk_token = vk_token
        self.user_id = user_id
        self.api_url = "https://api.vk.com/method/messages.send"
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @staticmethod
    def escape_markdown(text: str) -> str:
        """Экранирует спецсимволы MarkdownV2, кроме """
        if not text:
            return ""
        text = str(text).replace("\xa0", " ")
        return re.sub(r'([_\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

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
        """Форматирует объявление в простой текст для VK (без Markdown)"""
        def clean(text: str) -> str:
            if not text:
                return ""
            return str(text).replace("\xa0", " ")

        price = clean(getattr(ad, "priceDetailed", {}).get("value", "") if isinstance(getattr(ad, "priceDetailed", None),
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

    def __send_to_vk(self, user_id: str | int, ad: Item = None, msg: str = None):
        headers = {
            "Authorization": f"Bearer {self.vk_token}"
        }

        if msg:
            payload = {
                "domain": user_id,
                "random_id": 0,
                "message": msg,
                "v": "5.199"
            }
            return requests.post(self.api_url, headers=headers, data=payload)

        message = self.format_ad(ad)
        _image_url = self.get_first_image(ad=ad)

        # Загружаем фото если есть
        attachment = None
        if _image_url:
            attachment = self.__upload_photo_to_vk(_image_url, str(user_id))

        for attempt in range(1, self.max_retries + 1):
            try:
                payload = {
                    "domain": user_id,
                    "random_id": 0,
                    "message": message,
                    "v": "5.199"
                }
                if attachment:
                    payload["attachment"] = attachment

                logger.info(payload)
                response = requests.post(self.api_url, headers=headers, data=payload)

                if response.status_code != 200:
                    logger.warning("Не удалось отправить сообщение. Проверьте правильность введенных данных")
                    break

                body = response.json()
                if "error" in body:
                    error_msg = body["error"].get("error_msg", "Unknown error")
                    error_code = body["error"].get("error_code", 0)
                    logger.warning(f"VK API error {error_code}: {error_msg}")


                    if attempt < self.max_retries:
                        time.sleep(self.retry_delay)
                        continue
                    break

                logger.debug(f"Сообщение успешно отправлено (попытка {attempt})")
                break
            except requests.RequestException as e:
                logger.debug(f"Ошибка при отправке (попытка {attempt}): {e}")
                logger.debug(message)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.debug("Не удалось отправить сообщение после всех попыток.")

    def send_to_vk(self, ad: Item = None, msg: str = None):
        for user_id in self.user_id:
            self.__send_to_vk(user_id=user_id, ad=ad, msg=msg)
