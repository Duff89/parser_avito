import asyncio
import html
import json
import random
import re
import time
from urllib.parse import unquote, urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from curl_cffi import requests
from loguru import logger
from pydantic import ValidationError
from requests.cookies import RequestsCookieJar

from common_data import HEADERS
from db_service import SQLiteDBHandler
from dto import Proxy, AvitoConfig
from get_cookies import get_cookies
from hide_private_data import log_config
from load_config import load_avito_config
from models import ItemsResponse, Item
from tg_sender import SendAdToTg
from version import VERSION
from xlsx_service import XLSXHandler

DEBUG_MODE = False

logger.add("logs/app.log", rotation="5 MB", retention="5 days", level="DEBUG")


class AvitoParse:
    def __init__(
            self,
            config: AvitoConfig,
            stop_event=None
    ):
        self.config = config
        self.proxy_obj = self.get_proxy_obj()
        self.db_handler = SQLiteDBHandler()
        self.tg_handler = self.get_tg_handler()
        self.xlsx_handler = XLSXHandler(self.__get_file_title())
        self.stop_event = stop_event
        self.cookies = None
        self.session = requests.Session()
        self.headers = HEADERS
        self.good_request_count = 0
        self.bad_request_count = 0

        log_config(config=self.config, version=VERSION)

    def get_tg_handler(self) -> SendAdToTg | None:
        if all([self.config.tg_token, self.config.tg_chat_id]):
            return SendAdToTg(bot_token=self.config.tg_token, chat_id=self.config.tg_chat_id)
        return None

    def _send_to_tg(self, ads: list[Item]) -> None:
        for ad in ads:
            self.tg_handler.send_to_tg(ad=ad)

    def get_proxy_obj(self) -> Proxy | None:
        if all([self.config.proxy_string, self.config.proxy_change_url]):
            return Proxy(
                proxy_string=self.config.proxy_string,
                change_ip_link=self.config.proxy_change_url
            )
        logger.info("Работаем без прокси")
        return None

    def get_cookies(self, max_retries: int = 1, delay: float = 2.0) -> dict | None:
        for attempt in range(1, max_retries + 1):
            try:
                cookies, user_agent = asyncio.run(get_cookies(proxy=self.proxy_obj, headless=True))
                if cookies:
                    logger.info(f"[get_cookies] Успешно получены cookies с попытки {attempt}")

                    self.headers["user-agent"] = user_agent
                    return cookies
                else:
                    raise ValueError("Пустой результат cookies")
            except Exception as e:
                logger.warning(f"[get_cookies] Попытка {attempt} не удалась: {e}")
                if attempt < max_retries:
                    time.sleep(delay * attempt)  # увеличиваем задержку
                else:
                    logger.error(f"[get_cookies] Все {max_retries} попытки не удались")
                    return None

    def save_cookies(self) -> None:
        """Сохраняет cookies из requests.Session в JSON-файл."""
        with open("cookies.json", "w") as f:
            json.dump(self.session.cookies.get_dict(), f)

    def load_cookies(self) -> None:
        """Загружает cookies из JSON-файла в requests.Session."""
        try:
            with open("cookies.json", "r") as f:
                cookies = json.load(f)
                jar = RequestsCookieJar()
                for k, v in cookies.items():
                    jar.set(k, v)
                self.session.cookies.update(jar)
        except FileNotFoundError:
            pass

    def fetch_data(self, url, retries=3, backoff_factor=1):
        proxy_data = None
        if self.proxy_obj:
            proxy_data = {"https": f"http://{self.config.proxy_string}"}

        for attempt in range(1, retries + 1):
            if self.stop_event and self.stop_event.is_set():
                return

            try:
                response = self.session.get(
                    url=url,
                    headers=self.headers,
                    proxies=proxy_data,
                    cookies=self.cookies,
                    impersonate="chrome",
                    timeout=20,
                    verify=False,
                    http_version=3
                )
                logger.debug(f"Попытка {attempt}: {response.status_code}")

                if response.status_code >= 500:
                    raise requests.RequestsError(f"Ошибка сервера: {response.status_code}")
                if response.status_code == 429:
                    self.bad_request_count += 1
                    self.session = requests.Session()
                    self.change_ip()
                    if attempt >= 3:
                        self.cookies = self.get_cookies()
                    raise requests.RequestsError(f"Слишком много запросов: {response.status_code}")
                if response.status_code in [403, 302]:
                    self.cookies = self.get_cookies()
                    raise requests.RequestsError(f"Заблокирован: {response.status_code}")

                self.save_cookies()
                self.good_request_count += 1
                return response.text
            except requests.RequestsError as e:
                logger.debug(f"Попытка {attempt} закончилась неуспешно: {e}")
                if attempt < retries:
                    sleep_time = backoff_factor * attempt
                    logger.debug(f"Повтор через {sleep_time} секунд...")
                    time.sleep(sleep_time)
                else:
                    logger.info("Все попытки были неуспешными")
                    return None

    def parse(self):
        self.load_cookies()

        if self.config.one_file_for_link:
            self.xlsx_handler = None

        for _index, url in enumerate(self.config.urls):
            for i in range(0, self.config.count):
                if self.stop_event and self.stop_event.is_set():
                    return
                if DEBUG_MODE:
                    html_code = open("response.txt", "r", encoding="utf-8").read()
                else:
                    html_code = self.fetch_data(url=url, retries=self.config.max_count_of_retry)

                if not html_code:
                    return self.parse()

                if not self.xlsx_handler and self.config.one_file_for_link:
                    self.xlsx_handler = XLSXHandler(f"result/{_index + 1}.xlsx")

                data_from_page = self.find_json_on_page(html_code=html_code)
                try:
                    ads_models = ItemsResponse(**data_from_page.get("data", {}).get("catalog"))
                except ValidationError as err:
                    logger.error(f"При валидации объявлений произошла ошибка: {err}")
                    continue

                ads = self._clean_null_ads(ads=ads_models.items)

                ads = self._add_seller_to_ads(ads=ads)

                if not ads:
                    logger.info("Объявления закончились, заканчиваю работу с данной ссылкой")
                    break

                filter_ads = self.filter_ads(ads=ads)

                if self.tg_handler and not self.config.one_time_start:
                    self._send_to_tg(ads=filter_ads)

                filter_ads = self.parse_views(ads=filter_ads)

                if filter_ads:
                    logger.info(f"Сохраняю")
                    self.__save_data(ads=filter_ads)
                else:
                    logger.info("Сохранять нечего")

                url = self.get_next_page_url(url=url)

                logger.info(f"Пауза {self.config.pause_between_links} сек.")
                time.sleep(self.config.pause_between_links)

            if self.config.one_file_for_link:
                self.xlsx_handler = None

        logger.info(f"Хорошие запросы: {self.good_request_count}шт, плохие: {self.bad_request_count}шт")

        if self.config.one_time_start and self.tg_handler:
            self.tg_handler.send_to_tg(msg="Парсинг Авито завершён. Все ссылки обработаны")
            self.stop_event = True

    @staticmethod
    def _clean_null_ads(ads: list[Item]) -> list[Item]:
        return [ad for ad in ads if ad.id]

    @staticmethod
    def find_json_on_page(html_code, data_type: str = "mime") -> dict:
        soup = BeautifulSoup(html_code, "html.parser")
        try:
            for _script in soup.select('script'):
                script_type = _script.get('type')

                if data_type == 'mime' and script_type == 'mime/invalid':
                    script_content = html.unescape(_script.text)
                    parsed_data = json.loads(script_content)

                    if 'state' in parsed_data:
                        return parsed_data['state']

                    elif 'data' in parsed_data:
                        logger.info("data")
                        return parsed_data['data']

                    else:
                        return parsed_data

        except Exception as err:
            logger.error(f"Ошибка при поиске информации на странице: {err}")
        return {}

    def filter_ads(self, ads: list[Item]) -> list[Item]:
        """Сортирует объявления"""
        filters = [
            self._filter_viewed,
            self._filter_by_price_range,
            self._filter_by_black_keywords,
            self._filter_by_white_keyword,
            self._filter_by_address,
            self._filter_by_seller,
            self._filter_by_recent_time,
            self._filter_by_reserve,
            self._filter_by_promotion,
        ]

        for filter_fn in filters:
            ads = filter_fn(ads)
            logger.info(f"После фильтрации {filter_fn.__name__} осталось {len(ads)}")
            if not len(ads):
                return ads
        return ads

    def _filter_by_price_range(self, ads: list[Item]) -> list[Item]:
        try:
            return [ad for ad in ads if self.config.min_price <= ad.priceDetailed.value <= self.config.max_price]
        except Exception as err:
            logger.debug(f"Ошибка при фильтрации по цене: {err}")
            return ads

    def _filter_by_black_keywords(self, ads: list[Item]) -> list[Item]:
        if not self.config.keys_word_black_list:
            return ads
        try:
            return [ad for ad in ads if not self._is_phrase_in_ads(ad=ad, phrases=self.config.keys_word_black_list)]
        except Exception as err:
            logger.debug(f"Ошибка при проверке объявлений по списку стоп-слов: {err}")
            return ads

    def _filter_by_white_keyword(self, ads: list[Item]) -> list[Item]:
        if not self.config.keys_word_white_list:
            return ads
        try:
            return [ad for ad in ads if self._is_phrase_in_ads(ad=ad, phrases=self.config.keys_word_white_list)]
        except Exception as err:
            logger.debug(f"Ошибка при проверке объявлений по списку обязательных слов: {err}")
            return ads

    def _filter_by_address(self, ads: list[Item]) -> list[Item]:
        if not self.config.geo:
            return ads
        try:
            return [ad for ad in ads if self.config.geo in ad.geo.formattedAddress]
        except Exception as err:
            logger.debug(f"Ошибка при проверке объявлений по адресу: {err}")
            return ads

    def _filter_viewed(self, ads: list[Item]) -> list[Item]:
        try:
            return [ad for ad in ads if not self.is_viewed(ad=ad)]
        except Exception as err:
            logger.debug(f"Ошибка при проверке объявления по признаку смотрели или не смотрели: {err}")
            return ads

    def _add_seller_to_ads(self, ads: list[Item]) -> list[Item]:
        for ad in ads:
            if seller_id := self._extract_seller_slug(data=ad):
                ad.sellerId = seller_id
        return ads

    @staticmethod
    def _add_promotion_to_ads(ads: list[Item]) -> list[Item]:
        for ad in ads:
            ad.isPromotion = any(
                v.get("title") == "Продвинуто"
                for step in (ad.iva or {}).get("DateInfoStep", [])
                for v in step.payload.get("vas", [])
            )
        return ads

    def _filter_by_seller(self, ads: list[Item]) -> list[Item]:
        if not self.config.seller_black_list:
            return ads
        try:
            return [ad for ad in ads if not ad.sellerId or ad.sellerId not in self.config.seller_black_list]
        except Exception as err:
            logger.debug(f"Ошибка при отсеивании объявления с продавцами из черного списка : {err}")
            return ads

    def _filter_by_recent_time(self, ads: list[Item]) -> list[Item]:
        if not self.config.max_age:
            return ads
        try:
            return [ad for ad in ads if
                    self._is_recent(timestamp_ms=ad.sortTimeStamp, max_age_seconds=self.config.max_age)]
        except Exception as err:
            logger.debug(f"Ошибка при отсеивании слишком старых объявлений: {err}")
            return ads

    def _filter_by_reserve(self, ads: list[Item]) -> list[Item]:
        if not self.config.ignore_reserv:
            return ads
        try:
            return [ad for ad in ads if not ad.isReserved]
        except Exception as err:
            logger.debug(f"Ошибка при отсеивании объявлений в резерве: {err}")
            return ads

    def _filter_by_promotion(self, ads: list[Item]) -> list[Item]:
        ads = self._add_promotion_to_ads(ads=ads)
        if not self.config.ignore_promotion:
            return ads
        try:
            return [ad for ad in ads if not ad.isPromotion]
        except Exception as err:
            logger.debug(f"Ошибка при отсеивании продвинутых объявлений: {err}")
            return ads

    def parse_views(self, ads: list[Item]) -> list[Item]:
        if not self.config.parse_views:
            return ads

        logger.info("Начинаю парсинг просмотров")

        for ad in ads:
            try:
                html_code_full_page = self.fetch_data(url=f"https://www.avito.ru{ad.urlPath}")
                ad.total_views, ad.today_views = self._extract_views(html=html_code_full_page)
                delay = random.uniform(0.1, 0.9)
                time.sleep(delay)
            except Exception as err:
                logger.warning(f"Ошибка при парсинге {ad.urlPath}: {err}")
                continue

        return ads

    @staticmethod
    def _extract_views(html: str) -> tuple:
        soup = BeautifulSoup(html, "html.parser")

        def extract_digits(element):
            return int(''.join(filter(str.isdigit, element.get_text()))) if element else None

        total = extract_digits(soup.select_one('[data-marker="item-view/total-views"]'))
        today = extract_digits(soup.select_one('[data-marker="item-view/today-views"]'))

        return total, today

    def change_ip(self) -> bool:
        if not self.config.proxy_change_url:
            logger.info("Сейчас бы была смена ip, но мы без прокси")
            return False
        logger.info("Меняю IP")
        try:
            res = requests.get(url=self.config.proxy_change_url, verify=False)
            if res.status_code == 200:
                logger.info("IP изменен")
                return True
        except Exception as err:
            logger.info(f"При смене ip возникла ошибка: {err}")
        logger.info("Не удалось изменить IP, пробую еще раз")
        time.sleep(random.randint(3, 10))
        return self.change_ip()

    @staticmethod
    def _extract_seller_slug(data):
        match = re.search(r"/brands/([^/?#]+)", str(data))
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _is_phrase_in_ads(ad: Item, phrases: list) -> bool:
        full_text_from_ad = (ad.title + ad.description).lower()
        return any(phrase.lower() in full_text_from_ad for phrase in phrases)

    def is_viewed(self, ad: Item) -> bool:
        """Проверяет, смотрели мы это или нет"""
        return self.db_handler.record_exists(record_id=ad.id, price=ad.priceDetailed.value)

    @staticmethod
    def _is_recent(timestamp_ms: int, max_age_seconds: int) -> bool:
        now = datetime.utcnow()
        published_time = datetime.utcfromtimestamp(timestamp_ms / 1000)
        return (now - published_time) <= timedelta(seconds=max_age_seconds)

    def __get_file_title(self) -> str:
        """Определяет название файла"""
        title_file = 'all'
        if self.config.keys_word_white_list:
            title_file = "-".join(list(map(str.lower, self.config.keys_word_white_list)))

        return f"result/{title_file}.xlsx"

    def __save_data(self, ads: list[Item]) -> None:
        """Сохраняет результат в файл keyword*.xlsx и в БД"""
        try:
            self.xlsx_handler.append_data_from_page(ads=ads)
        except Exception as err:
            logger.info(f"При сохранении в Excel ошибка {err}")

        """сохраняет просмотренные объявления"""
        try:
            self.db_handler.add_record_from_page(ads=ads)
        except Exception as err:
            logger.info(f"При сохранении в БД ошибка {err}")

    def get_next_page_url(self, url: str):
        """Получает следующую страницу"""
        try:
            url_parts = urlparse(url)
            query_params = parse_qs(url_parts.query)
            current_page = int(query_params.get('p', [1])[0])
            query_params['p'] = current_page + 1
            if self.config.one_time_start:
                logger.debug(f"Страница {current_page}")

            new_query = urlencode(query_params, doseq=True)
            next_url = urlunparse((url_parts.scheme, url_parts.netloc, url_parts.path, url_parts.params, new_query,
                                   url_parts.fragment))
            return next_url
        except Exception as err:
            logger.error(f"Не смог сформировать ссылку на следующую страницу для {url}. Ошибка: {err}")


if __name__ == "__main__":
    try:
        config = load_avito_config("config.toml")
    except Exception as err:
        logger.error(f"Ошибка загрузки конфига: {err}")
        exit(1)

    while True:
        try:
            parser = AvitoParse(config)
            parser.parse()
            if config.one_time_start:
                logger.info("Парсинг завершен т.к. включён one_time_start в настройках")
                break
            logger.info(f"Парсинг завершен. Пауза {config.pause_general} сек")
            time.sleep(config.pause_general)
        except Exception as err:
            logger.error(f"Произошла ошибка {err}")
            time.sleep(30)
