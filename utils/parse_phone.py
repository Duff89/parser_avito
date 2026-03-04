import requests
import json
import re
from loguru import logger

from dto import AvitoConfig
from integrations.notifications.transport import send_with_retries
from models import Item


class ParsePhone:
    API_URL = "https://spfa.ru/api/phone/"
    DEFAULT_TIMEOUT = 30
    BATCH_SIZE = 10 # по сколько номеров парсить за раз

    def __init__(self, ads: list[Item], config: AvitoConfig):
        self.ads = ads
        self.config = config


    def get_phone_batch(self, ads_ids: list):
        def _send():
            return requests.post(
                self.API_URL,
                json={
                    "api_key": self.config.cookies_api_key,
                    "ads": ads_ids,
                },
                timeout=self.DEFAULT_TIMEOUT,
            )

        return send_with_retries(_send)

    @staticmethod
    def get_phone_dict(response: dict) -> dict:
        """
        Возвращает телефоны в виде словаря {ad_id: phone}

        Args:
            response: JSON ответ от сервера

        Returns:
            dict: Словарь с телефонами
        """
        if not response.get("success"):
            logger.warning("Не удалось получить результат через сервер")
            return {}

        ads_list = response.get("results", [])
        if not isinstance(ads_list, list):
            logger.error(f"Неверный формат results: {type(ads_list)}")
            return {}

        # Создаем словарь с приведением ad_id к строке
        result_dict = {
            str(ad.get('ad_id')): ad.get('phone')
            for ad in ads_list
            if ad.get('ad_id') is not None
        }

        logger.debug(f"Получено {len(result_dict)} телефонов из ответа")
        return result_dict

    @staticmethod
    def clean_phone(phone: str) -> str:
        """
        Очищает номер телефона от всех нецифровых символов
        """
        if not phone or not isinstance(phone, str):
            return phone

        # Убираем '+', пробелы, скобки, дефисы - оставляем только цифры
        cleaned = re.sub(r'\D', '', phone)
        return cleaned if cleaned else phone

    def parse_phones(self) -> list[Item]:
        logger.info(f"Начинаем парсинг телефонов для {len(self.ads)} объявлений")
        result_dict_with_phone = {}

        for i in range(0, len(self.ads), self.BATCH_SIZE):
            try:
                batch = self.ads[i:i + self.BATCH_SIZE]

                ads_ids = [
                    str(ad.id) for ad in batch
                    if ad.contacts.phone
                ]

                if not ads_ids:
                    continue

                response = self.get_phone_batch(ads_ids=ads_ids)

                if response.status_code != 200:
                    continue

                response_data = response.json()

                # Получаем словарь с телефонами и сразу очищаем их
                phone_dict = self.get_phone_dict(response=response_data)
                # Применяем глубокую очистку ко всем телефонам
                cleaned_dict = {
                    ad_id: self.clean_phone(phone)
                    for ad_id, phone in phone_dict.items()
                }
                result_dict_with_phone.update(cleaned_dict)

            except Exception as err:
                logger.error(f"Ошибка при обработке батча: {err}")
                continue

        logger.info(f"Всего получено телефонов из API: {len(result_dict_with_phone)}")

        # Подсчёт статистики по очищенным телефонам
        actual_phones = {k: v for k, v in result_dict_with_phone.items() if v}
        logger.info(f"Из них непустых номеров: {len(actual_phones)}")

        # Добавляем результат к начальным объявлениям
        updated_count = 0
        for ad in self.ads:
            if str(ad.id) in result_dict_with_phone:
                ad.phone = result_dict_with_phone.get(str(ad.id))
                updated_count += 1

        logger.info(f"Обновлено объявлений с телефонами: {updated_count}")

        # Пример первых нескольких записей для проверки
        sample_items = list(result_dict_with_phone.items())[:5]
        logger.info(f"Пример очищенных номеров: {sample_items}")

        return self.ads