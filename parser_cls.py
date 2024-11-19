import os
import random
import threading
import time
import csv
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import requests
from notifiers.logging import NotificationHandler
from seleniumbase import SB
from loguru import logger

from custom_exception import StopEventException
from locator import LocatorAvito


class AvitoParse:
    """
    Парсинг  товаров на avito.ru
    """
    def __init__(self,
                 url: list,
                 keysword_list: list,
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
                 ):
        self.url_list = url
        self.url = None
        self.keys_word = keysword_list or None
        self.count = count
        self.data = []
        self.tg_token = tg_token
        self.title_file = self.__get_file_title()
        self.max_price = int(max_price)
        self.min_price = int(min_price)
        self.geo = geo
        self.debug_mode = debug_mode
        self.need_more_info = need_more_info
        self.proxy = proxy
        self.proxy_change_url = proxy_change_url
        self.stop_event = stop_event or threading.Event()

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
        self.__create_file_csv()
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
        """Ограничение количества просмотренных объявлений"""
        if os.path.isfile('viewed.txt'):
            with open('viewed.txt', 'r') as file:
                self.viewed_list = list(map(str.rstrip, file.readlines()))
                if len(self.viewed_list) > 5000:
                    self.viewed_list = self.viewed_list[-900:]
        else:
            with open('viewed.txt', 'w'):
                self.viewed_list = []

        titles = self.driver.find_elements(LocatorAvito.TITLES[1], by="css selector")
        logger.info(f"Вижу {len(titles)} объявлений на странице")
        data_from_general_page = []
        for title in titles:
            """Сбор информации с основной страницы"""
            name = title.find_element(*LocatorAvito.NAME).text
            if title.find_elements(*LocatorAvito.DESCRIPTIONS):
                description = title.find_element(*LocatorAvito.DESCRIPTIONS).text
            else:
                description = ''

            url = title.find_element(*LocatorAvito.URL).get_attribute("href")
            price = title.find_element(*LocatorAvito.PRICE).get_attribute("content")
            ads_id = title.get_attribute("data-item-id")

            if self.is_viewed(ads_id):
                continue
            self.viewed_list.append(ads_id)
            data = {
                'name': name,
                'description': description,
                'url': url,
                'price': price
            }
            if self.min_price <= int(price) <= self.max_price:
                if self.keys_word:
                    if any([item.lower() in (description.lower() + name.lower()) for item in self.keys_word]):
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
                if self.geo and item_info.get("geo"):
                    if not self.geo.lower() in str(item_info.get("geo")).lower():
                        continue
                self.__pretty_log(data=item_info)
                self.__save_data(data=item_info)
            except Exception as err:
                logger.debug(err)

    @staticmethod
    def __pretty_log(data):
        """Красивый вывод"""
        logger.success(
            f'\n{data.get("name", "-")}\n'
            f'Цена: {data.get("price", "-")}\n'
            f'Описание: {data.get("description", "-")}\n'
            f'Просмотров: {data.get("views", "-")}\n'
            f'Дата публикации: {data.get("date_public", "-")}\n'
            f'Продавец: {data.get("seller_name", "-")}\n'
            f'Адрес: {data.get("geo", "-")}\n'
            f'Ссылка: {data.get("url", "-")}\n')

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
        if self.geo and self.driver.find_elements(LocatorAvito.GEO[1], by="css selector"):
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

    def is_viewed(self, ads_id: str) -> bool:
        """Проверяет, смотрели мы это или нет"""
        if ads_id in self.viewed_list:
            return True
        return False

    def __save_data(self, data: dict):
        """Сохраняет результат в файл keyword*.csv"""
        with open(f"result/{self.title_file}.csv", mode="a", newline='', encoding='utf-8', errors='ignore') as file:
            writer = csv.writer(file)
            writer.writerow([
                data.get("name", '-'),
                data.get("price", '-'),
                data.get("url", '-'),
                data.get("description", '-'),
                data.get("views", '-'),
                data.get("date_public", '-'),
                data.get("seller_name", 'no'),
                data.get("geo", '-')
            ])

        """сохраняет просмотренные объявления"""
        with open('viewed.txt', 'w') as file:
            for item in set(self.viewed_list):
                file.write("%s\n" % item)

    @property
    def __is_csv_empty(self) -> bool:
        """Пустой csv или нет"""
        os.makedirs(os.path.dirname("result/"), exist_ok=True)
        try:
            with open(f"result/{self.title_file}.csv", 'r', encoding='utf-8', errors='ignore') as file:
                reader = csv.reader(file)
                try:
                    first_row = next(reader)
                except StopIteration:
                    return True
                return False
        except FileNotFoundError:
            return True

    @logger.catch
    def __create_file_csv(self):
        """Создает файл и прописывает названия если нужно"""

        if self.__is_csv_empty:
            with open(f"result/{self.title_file}.csv", 'a', encoding='utf-8', errors='ignore') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "Название",
                    "Цена",
                    "Ссылка",
                    "Описание",
                    "Просмотров",
                    "Дата публикации",
                    "Продавец",
                    "Адрес"
                ])

    def __get_file_title(self) -> str:
        """Определяет название файла"""
        if self.keys_word not in ['', None]:
            title_file = "-".join(list(map(str.lower, self.keys_word)))
        else:
            title_file = 'all'
        return title_file

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
                    proxy=self.proxy
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
            logger.info("Запрос на смену IP отправлен. Жду изменения")
        proxies = {
            'https': f"http://{self.proxy}"
        }
        for i in range(10):
            self.check_stop_event()
            time.sleep(5)
            try:
                response = requests.get(
                    url="https://api.ipify.org?format=json",
                    proxies=proxies)
                if ip := response.json().get("ip"):
                    logger.info(f"Новый IP {ip}")
                    self.driver.delete_all_cookies()
                    return True
            except Exception as err:
                logger.debug(err)
                time.sleep(5)
        return False


if __name__ == '__main__':
    import configparser

    config = configparser.ConfigParser()  # создаём объекта парсера
    config.read("settings.ini", encoding="utf-8")  # читаем конфиг

    try:
        """Багфикс проблем с экранированием"""
        url = config["Avito"]["URL"].split(",")
    except Exception:
        with open('settings.ini', encoding="utf-8") as file:
            line_url = file.readlines()[1]
            regex = r"http.+"
            url = re.findall(regex, line_url)

    chat_ids = config["Avito"]["CHAT_ID"].split(",")
    token = config["Avito"]["TG_TOKEN"]
    num_ads = config["Avito"]["NUM_ADS"]
    freq = config["Avito"]["FREQ"]
    keys = config["Avito"]["KEYS"].split(",")
    max_price = config["Avito"].get("MAX_PRICE", "9999999999") or "9999999999"
    min_price = config["Avito"].get("MIN_PRICE", "0") or "0"
    geo = config["Avito"].get("GEO", "") or ""
    proxy = config["Avito"].get("PROXY", "")
    proxy_change_ip = config["Avito"].get("PROXY_CHANGE_IP", "")
    need_more_info = config["Avito"]["NEED_MORE_INFO"]

    if token and chat_ids:
        for chat_id in chat_ids:
            params = {
                'token': token,
                'chat_id': chat_id
            }
            tg_handler = NotificationHandler("telegram", defaults=params)

            """Все логи уровня SUCCESS и выше отсылаются в телегу"""
            logger.add(tg_handler, level="SUCCESS", format="{message}")

    while True:
        try:
            AvitoParse(
                url=url,
                count=int(num_ads),
                keysword_list=keys,
                max_price=int(max_price),
                min_price=int(min_price),
                geo=geo,
                need_more_info=1 if need_more_info else 0,
                proxy=proxy,
                proxy_change_url=proxy_change_ip
            ).parse()
            logger.info("Пауза")
            time.sleep(int(freq))
        except Exception as error:
            logger.error(error)
            logger.error('Произошла ошибка, но работа будет продолжена через 30 сек. '
                         'Если ошибка повторится несколько раз - перезапустите скрипт.'
                         'Если и это не поможет - обратитесь к разработчику по ссылке ниже')
            time.sleep(30)
