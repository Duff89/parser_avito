import csv
import os
import random
import re
import threading
import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests
from loguru import logger
from notifiers.logging import NotificationHandler
from seleniumbase import SB

from core.settings import ParserSettings
from custom_exception import StopEventException
from db_service import SQLiteDBHandler
from locator import LocatorAvito
from xlsx_service import XLSXHandler


class AvitoParse:
    """
    Парсинг  товаров на avito.ru
    """
    def __init__(self,
                 url: list,
                 keysword_list: list,
                 keysword_black_list: list,
                 count: int = 5,
                 tg_token: str = None,
                 max_price: int = 0,
                 min_price: int = 0,
                 geo: str = None,
                 debug_mode: int = 0,
                 need_more_info: int = 1,
                 proxy: str = None,
                 proxy_change_url: str = None,
                 stop_event=None,
                 max_views: int = None,
                 fast_speed: int = 0
                 ):
        self.url_list = url
        self.url = None
        self.keys_word = keysword_list or None
        self.keys_black_word = keysword_black_list or None
        self.count = count
        self.data = []
        self.tg_token = tg_token
        self.title_file = self.__get_file_title()
        self.max_price = int(max_price)
        self.min_price = int(min_price)
        self.max_views = max_views
        self.geo = geo
        self.debug_mode = debug_mode
        self.need_more_info = need_more_info
        self.proxy = proxy
        self.proxy_change_url = proxy_change_url
        self.stop_event = stop_event or threading.Event()
        self.db_handler = SQLiteDBHandler()
        self.xlsx_handler = XLSXHandler(self.title_file)
        self.fast_speed = fast_speed

    @property
    def use_proxy(self) -> bool:
        return all([self.proxy, self.proxy_change_url])

    def ip_block(self) -> None:
        if self.use_proxy:
            logger.info("Блок IP")
            self.change_ip()
        else:
            logger.info("Блок IP. Прокси нет, поэтому делаю паузу")
            time.sleep(random.randint(300, 350))

    def __get_url(self):
        logger.info(f"Открываю страницу: {self.url}")
        self.driver.open(self.url)

        if "Доступ ограничен" in self.driver.get_title():
            self.ip_block()
            return self.__get_url()

    def __paginator(self):
        """Кнопка далее"""
        logger.info('Страница успешно загружена. Просматриваю объявления')
        for i in range(self.count):
            if self.stop_event.is_set():
                break
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            self.__parse_page()
            time.sleep(random.randint(2, 4))
            self.open_next_btn()
        return

    def open_next_btn(self):
        self.url = self.get_next_page_url(url=self.url)
        logger.info("Следующая страница")
        self.driver.uc_open(self.url)

    @staticmethod
    def get_next_page_url(url: str):
        """Получает следующую страницу"""
        try:
            url_parts = urlparse(url)
            query_params = parse_qs(url_parts.query)
            current_page = int(query_params.get('p', [1])[0])
            query_params['p'] = current_page + 1
            new_query = urlencode(query_params, doseq=True)
            next_url = urlunparse((url_parts.scheme, url_parts.netloc, url_parts.path, url_parts.params, new_query,
                                   url_parts.fragment))
            return next_url
        except Exception as err:
            logger.error(f"Не смог сформировать ссылку на следующую страницу для {url}. Ошибка: {err}")

    def __parse_page(self):
        """Парсит открытую страницу"""
        self.check_stop_event()
        titles = self.driver.find_elements(LocatorAvito.TITLES[1], by="css selector")
        logger.info(f"Вижу {len(titles)} объявлений на странице")
        data_from_general_page = []
        for title in titles:
            """Сбор информации с основной страницы"""
            name = title.find_element(*LocatorAvito.NAME).text
            if title.find_elements(*LocatorAvito.DESCRIPTIONS):
                try:
                    description = title.find_element(*LocatorAvito.DESCRIPTIONS).text
                except Exception as err:
                    logger.debug(f"Ошибка при получении описания: {err}")
                    description = ''
            else:
                description = ''

            url = title.find_element(*LocatorAvito.URL).get_attribute("href")
            price = title.find_element(*LocatorAvito.PRICE).get_attribute("content")
            ads_id = title.get_attribute("data-item-id")

            if self.is_viewed(ads_id, price):
                logger.debug("Пропускаю")
                continue
            data = {
                'name': name,
                'description': description,
                'url': url,
                'price': price,
                'id': ads_id
            }

            all_content = description.lower() + name.lower()
            if self.min_price <= int(price) <= self.max_price:
                if self.keys_word and self.keys_black_word:
                    if any([item.lower() in all_content for item in self.keys_word])\
                            and not any([item.lower() in all_content for item in self.keys_black_word]):
                        data_from_general_page.append(data)
                elif self.keys_black_word:
                    if not any([item.lower() in all_content for item in self.keys_black_word]):
                        data_from_general_page.append(data)
                elif self.keys_word:
                    if any([item.lower() in all_content for item in self.keys_word]):
                        data_from_general_page.append(data)
                else:
                    data_from_general_page.append(data)
        if data_from_general_page:
            self.__parse_other_data(item_info_list=data_from_general_page)

    def __parse_other_data(self, item_info_list: list):
        """Собирает доп. информацию для каждого объявления"""
        for item_info in item_info_list:
            try:
                if self.stop_event.is_set():
                    logger.info("Процесс будет остановлен")
                    break
                if self.need_more_info:
                    item_info = self.__parse_full_page(item_info)

                if self.geo and item_info.get("geo"):  # проверка гео
                    if not self.geo.lower() in str(item_info.get("geo")).lower():
                        continue

                if self.max_views and int(self.max_views) <= int(item_info.get("views", 0)):
                    logger.info("Количество просмотров больше заданного. Пропускаю объявление")
                    continue

                self.__pretty_log(data=item_info)
                self.__save_data(data=item_info)
            except Exception as err:
                logger.debug(err)

    @staticmethod
    def __pretty_log(data):
        """Красивый вывод для Telegram"""
        price = data.get("price", "-")
        name = data.get("name", "-")
        id_ = data.get("id", "-")
        seller_name = data.get("seller_name")
        short_url = f"https://avito.ru/{id_}"
        message = (
                f"{price}\n{name}\n{short_url}\n"
                + (f"Продавец: {seller_name}\n" if seller_name else "")
        )
        logger.success(message)

    def __parse_full_page(self, data: dict) -> dict:
        """Парсит для доп. информации открытое объявление"""
        self.driver.uc_open(data.get("url"))
        if "Доступ ограничен" in self.driver.get_title():
            logger.info("Доступ ограничен: проблема с IP")
            self.ip_block()
            return self.__parse_full_page(data=data)
        """Если не дождались загрузки"""
        try:
            self.driver.wait_for_element(LocatorAvito.TOTAL_VIEWS[1], by="css selector", timeout=10)
        except Exception:
            """Проверка на бан по ip"""
            if "Доступ ограничен" in self.driver.get_title():
                logger.info("Доступ ограничен: проблема с IP")
                self.ip_block()
                return self.__parse_full_page(data=data)
            logger.debug("Не дождался загрузки страницы")
            return data

        """Гео"""
        if self.driver.find_elements(LocatorAvito.GEO[1], by="css selector"):
            geo = self.driver.find_element(LocatorAvito.GEO[1], by="css selector").text
            data["geo"] = geo.lower()

        """Количество просмотров"""
        if self.driver.find_elements(LocatorAvito.TOTAL_VIEWS[1], by="css selector"):
            total_views = self.driver.find_element(LocatorAvito.TOTAL_VIEWS[1]).text.split()[0]
            data["views"] = total_views

        """Дата публикации"""
        if self.driver.find_elements(LocatorAvito.DATE_PUBLIC[1], by="css selector"):
            date_public = self.driver.find_element(LocatorAvito.DATE_PUBLIC[1], by="css selector").text
            if "· " in date_public:
                date_public = date_public.replace("· ", '')
            data["date_public"] = date_public

        """Имя продавца"""
        if self.driver.find_elements(LocatorAvito.SELLER_NAME[1], by="css selector"):
            seller_name = self.driver.find_element(LocatorAvito.SELLER_NAME[1], by="css selector").text
            data["seller_name"] = seller_name

        return data

    def is_viewed(self, ads_id: int, price: int) -> bool:
        """Проверяет, смотрели мы это или нет"""
        return self.db_handler.record_exists(ads_id, price)

    def __save_data(self, data: dict) -> None:
        """Сохраняет результат в файл keyword*.xlsx"""
        self.xlsx_handler.append_data(data=data)

        """сохраняет просмотренные объявления"""
        self.db_handler.add_record(record_id=int(data.get("id")), price=int(data.get("price")))

    def __get_file_title(self) -> str:
        """Определяет название файла"""
        if self.keys_word not in ['', None]:
            title_file = "-".join(list(map(str.lower, self.keys_word)))
        else:
            title_file = 'all'
        return f"result/{title_file}.xlsx"

    def parse(self):
        """Метод для вызова"""
        for _url in self.url_list:
            self.url = _url
            if self.stop_event and self.stop_event.is_set():
                logger.info("Процесс будет остановлен")
                return
            with SB(uc=True,
                    headed=True if self.debug_mode else False,
                    headless=True if not self.debug_mode else False,
                    page_load_strategy="eager",
                    block_images=True,
                    agent=random.choice(open("user_agent_pc.txt").readlines()),
                    proxy=self.proxy,
                    sjw=True if self.fast_speed else False,
                    ) as self.driver:
                try:
                    self.__get_url()
                    self.__paginator()
                except StopEventException:
                    logger.info("Парсинг завершен")
                    return
                except Exception as err:
                    logger.error(f"Ошибка: {err}")
        self.stop_event.clear()
        logger.info("Парсинг завершен")

    def check_stop_event(self):
        if self.stop_event.is_set():
            logger.info("Процесс будет остановлен")
            raise StopEventException()

    def change_ip(self) -> bool:
        logger.info("Меняю IP")
        res = requests.get(url=self.proxy_change_url)
        if res.status_code == 200:
            logger.info("IP изменен")
            return True
        logger.info("Не удалось изменить IP, пробую еще раз")
        time.sleep(10)
        return self.change_ip()


if __name__ == '__main__':
    config_pyd = ParserSettings()

    if config_pyd.avito.tg_token and config_pyd.avito.chat_ids:
        for chat_id in config_pyd.avito.chat_ids:
            params = {"token": config_pyd.avito.tg_token, "chat_id": chat_id}
            tg_handler = NotificationHandler("telegram", defaults=params)

            """Все логи уровня SUCCESS и выше отсылаются в телегу"""
            logger.add(tg_handler, level="SUCCESS", format="{message}")

    while True:
        try:
            AvitoParse(
                url=[str(url_) for url_ in config_pyd.avito.url],
                count=config_pyd.avito.num_ads,
                keysword_list=config_pyd.avito.keys,
                max_price=config_pyd.avito.max_price,
                min_price=config_pyd.avito.min_price,
                geo=config_pyd.avito.geo,
                debug_mode=config_pyd.avito.debug_mode,
                need_more_info=config_pyd.avito.need_more_info,
                proxy=config_pyd.avito.proxy,
                proxy_change_url=config_pyd.avito.proxy_change_ip,

                keysword_black_list=keys_black if keys_black not in ([''], None) else None,
                max_views=int(max_view) if max_view else None,
                fast_speed=1 if fast_speed else 0
            ).parse()
            logger.info("Пауза")
            time.sleep(int(config_pyd.avito.freq))
        except Exception as error:
            logger.error(error)
            logger.error(
                "Произошла ошибка, но работа будет продолжена через 30 сек. "
                "Если ошибка повторится несколько раз - перезапустите скрипт."
                "Если и это не поможет - обратитесь к разработчику по ссылке ниже"
            )
            time.sleep(30)
