import asyncio
import os
import random
import time
import csv
import re
from notifiers.logging import NotificationHandler
from seleniumbase import SB
from loguru import logger
from locator import LocatorAvito

from lib.req import fetch


class AvitoParse:
    """
    Парсинг  товаров на avito.ru
    """

    def __init__(
        self,
        url: str,
        keysword_list: list,
        count: int = 10,
        tg_token: str = None,
        max_price: int = 0,
        min_price: int = 0,
        geo: str = None,
        delay: int = 0,
        debug_mode: int = 0,
    ):
        self.url = url
        self.keys_word = keysword_list
        self.count = count
        self.data = []
        self.tg_token = tg_token
        self.title_file = self.__get_file_title()
        self.max_price = int(max_price)
        self.min_price = int(min_price)
        self.geo = geo
        self.delay = delay
        self.debug_mode = debug_mode

    def __get_url(self):
        self.driver.open(self.url)

        if "Доступ ограничен" in self.driver.get_title():
            time.sleep(10)
            raise Exception("Перезапуск из-за блокировки IP")

        self.driver.open_new_window()  # сразу открываем и вторую вкладку
        self.driver.switch_to_window(window=0)

    async def __paginator(self):
        """Кнопка далее"""
        logger.info("Страница успешно загружена. Просматриваю объявления")
        self.__create_file_csv()
        while self.count > 0:
            await self.__parse_page()

            time.sleep(random.randint(5, 7))
            """Проверяем есть ли кнопка далее"""
            if self.driver.find_elements(LocatorAvito.NEXT_BTN[1], by="css selector"):
                self.driver.find_element(
                    LocatorAvito.NEXT_BTN[1], by="css selector"
                ).click()
                self.count -= 1
                logger.debug("Следующая страница")
            else:
                logger.info("Нет кнопки дальше")
                break

    @logger.catch
    async def __parse_page(self):
        """Парсит открытую страницу"""

        """Ограничение количества просмотренных объявлений"""
        if os.path.isfile("viewed.txt"):
            with open("viewed.txt", "r") as file:
                self.viewed_list = list(map(str.rstrip, file.readlines()))
                if len(self.viewed_list) > 5000:
                    self.viewed_list = self.viewed_list[-900:]
        else:
            with open("viewed.txt", "w") as file:
                self.viewed_list = []

        titles = self.driver.find_elements(LocatorAvito.TITLES[1], by="css selector")
        items = []
        for title in titles:
            name = title.find_element(*LocatorAvito.NAME).text

            if title.find_elements(*LocatorAvito.DESCRIPTIONS):
                description = title.find_element(*LocatorAvito.DESCRIPTIONS).text
            else:
                description = ""

            url = title.find_element(*LocatorAvito.URL).get_attribute("href")
            price = title.find_element(*LocatorAvito.PRICE).get_attribute("content")
            ads_id = title.get_attribute("data-item-id")
            items.append(
                {
                    "name": name,
                    "description": description,
                    "url": url,
                    "price": price,
                    "ads_id": ads_id,
                }
            )

        for data in items:
            ads_id = data.pop("ads_id")
            name = data.get("name")
            description = data.get("description")
            url = data.get("url")
            price = data.get("price")

            if self.is_viewed(ads_id):
                continue
            self.viewed_list.append(ads_id)

            """Определяем нужно ли нам учитывать ключевые слова"""
            if self.keys_word != [""]:
                if (
                    any(
                        [
                            item.lower() in (description.lower() + name.lower())
                            for item in self.keys_word
                        ]
                    )
                    and self.min_price <= int(price) <= self.max_price
                ):
                    self.data.append(self.__parse_full_page(url, data))
                    """Проверка адреса если нужно"""
                    if self.geo and self.geo.lower() not in self.data[-1].get(
                        "geo", self.geo.lower()
                    ):
                        continue
                    """Отправляем в телеграм"""
                    self.__pretty_log(data=data)
                    await self.__save_data(data=data)

            elif self.min_price <= int(price) <= self.max_price:

                self.data.append(self.__parse_full_page(url, data))
                """Проверка адреса если нужно"""
                if self.geo and self.geo.lower() not in self.data[-1].get(
                    "geo", self.geo.lower()
                ):
                    continue
                """Отправляем в телеграм"""
                self.__pretty_log(data=data)
                await self.__save_data(data=data)

            else:
                continue

            if self.delay:
                logger.info(f"Пауза {self.delay} сек")
                time.sleep(self.delay)

    def __pretty_log(self, data):
        """Красивый вывод"""
        logger.success(
            f'\n{data.get("name", "-")}\n'
            f'Цена: {data.get("price", "-")}\n'
            f'Описание: {data.get("description", "-")}\n'
            f'Просмотров: {data.get("views", "-")}\n'
            f'Дата публикации: {data.get("date_public", "-")}\n'
            f'Продавец: {data.get("seller_name", "-")}\n'
            f'Ссылка: {data.get("url", "-")}\n'
        )

    def __parse_full_page(self, url: str, data: dict) -> dict:
        """Парсит для доп. информации открытое объявление на отдельной вкладке"""
        self.driver.switch_to_window(window=1)
        self.driver.get(url)

        """Если не дождались загрузки"""
        try:
            self.driver.wait_for_element(
                LocatorAvito.TOTAL_VIEWS[1], by="css selector", timeout=10
            )
        except Exception:
            """Проверка на бан по ip"""
            if "Доступ ограничен" in self.driver.get_title():
                logger.success(
                    "Доступ ограничен: проблема с IP. \nПоследние объявления будут без подробностей"
                )

            self.driver.switch_to_window(window=0)
            logger.debug("Не дождался загрузки страницы")
            return data

        """Гео"""
        if self.geo and self.driver.find_elements(
            LocatorAvito.GEO[1], by="css selector"
        ):
            geo = self.driver.find_element(LocatorAvito.GEO[1], by="css selector").text
            data["geo"] = geo.lower()

        """Количество просмотров"""
        if self.driver.find_elements(LocatorAvito.TOTAL_VIEWS[1], by="css selector"):
            total_views = self.driver.find_element(
                LocatorAvito.TOTAL_VIEWS[1]
            ).text.split()[0]
            data["views"] = total_views

        """Дата публикации"""
        if self.driver.find_elements(LocatorAvito.DATE_PUBLIC[1], by="css selector"):
            date_public = self.driver.find_element(
                LocatorAvito.DATE_PUBLIC[1], by="css selector"
            ).text
            if "· " in date_public:
                date_public = date_public.replace("· ", "")
            data["date_public"] = date_public

        """Имя продавца"""
        if self.driver.find_elements(LocatorAvito.SELLER_NAME[1], by="css selector"):
            seller_name = self.driver.find_element(
                LocatorAvito.SELLER_NAME[1], by="css selector"
            ).text
            data["seller_name"] = seller_name

        """Возвращается на вкладку №1"""
        self.driver.switch_to_window(window=0)
        return data

    def is_viewed(self, ads_id: str) -> bool:
        """Проверяет, смотрели мы это или нет"""
        if ads_id in self.viewed_list:
            return True
        return False

    async def __save_data(self, data: dict):
        link = "http://104.248.143.154:8080/api/s/s2s/track"
        code, res = await fetch(
            link,
            data,
            headers={
                "X-Write-Key": "BaUKuuGZToJLSFmBtpwLK4KObUyFNmX1:LdWfwlhLbcvr8dgUNsfNDDT1NkSaIsKE",
            },
        )

        print("REQ", link, data)
        print("RES", code, res)

        # with open(f"result/{self.title_file}.csv", mode="a", newline='', encoding='utf-8', errors='ignore') as file:
        #     writer = csv.writer(file)
        #     writer.writerow([
        #         data.get("name", '-'),
        #         data.get("price", '-'),
        #         data.get("url", '-'),
        #         data.get("description", '-'),
        #         data.get("views", '-'),
        #         data.get("date_public", '-'),
        #         data.get("seller_name", 'no'),
        #         data.get("geo", '-')
        #     ])

        """сохраняет просмотренные объявления"""
        with open("viewed.txt", "w") as file:
            for item in set(self.viewed_list):
                file.write("%s\n" % item)

    @property
    def __is_csv_empty(self) -> bool:
        """Пустой csv или нет"""
        os.makedirs(os.path.dirname("result/"), exist_ok=True)
        try:
            with open(
                f"result/{self.title_file}.csv", "r", encoding="utf-8", errors="ignore"
            ) as file:
                reader = csv.reader(file)
                try:
                    # Попытка чтения первой строки
                    next(reader)
                except StopIteration:
                    # файл пустой
                    return True
                return False
        except FileNotFoundError:
            return True

    @logger.catch
    def __create_file_csv(self):
        """Создает файл и прописывает названия если нужно"""

        if self.__is_csv_empty:
            with open(
                f"result/{self.title_file}.csv", "a", encoding="utf-8", errors="ignore"
            ) as file:
                writer = csv.writer(file)
                writer.writerow(
                    [
                        "Название",
                        "Цена",
                        "Ссылка",
                        "Описание",
                        "Просмотров",
                        "Дата публикации",
                        "Продавец",
                        "Адрес",
                    ]
                )

    def __get_file_title(self) -> str:
        """Определяет название файла"""
        if self.keys_word != [""]:
            title_file = "-".join(list(map(str.lower, self.keys_word)))

        else:
            title_file = "all"
        return title_file

    async def parse(self):
        """Метод для вызова"""
        with SB(
            uc=True,
            headed=True if self.debug_mode else False,
            headless=True if not self.debug_mode else False,
            page_load_strategy="eager",
            block_images=True,
            # skip_js_waits=True,
        ) as self.driver:
            try:
                self.__get_url()
                await self.__paginator()
            except Exception as error:
                logger.error(f"Ошибка: {error}")


async def main():
    import configparser

    config = configparser.ConfigParser()  # создаём объекта парсера
    config.read("settings.ini")  # читаем конфиг

    try:
        """Багфикс проблем с экранированием"""
        url = config["Avito"]["URL"]  # начальный url
    except Exception:
        with open("settings.ini") as file:
            line_url = file.readlines()[1]
            regex = r"http.+"
            url = re.search(regex, line_url)[0]
    chat_id = config["Avito"]["CHAT_ID"]
    token = config["Avito"]["TG_TOKEN"]
    num_ads = config["Avito"]["NUM_ADS"]
    freq = config["Avito"]["FREQ"]
    delay = config["Avito"]["DELAY"] or "0"
    keys = config["Avito"]["KEYS"]
    max_price = config["Avito"].get("MAX_PRICE", "0") or "0"
    min_price = config["Avito"].get("MIN_PRICE", "0") or "0"
    geo = config["Avito"].get("GEO", "") or ""

    if token and chat_id:
        params = {"token": token, "chat_id": chat_id}
        tg_handler = NotificationHandler("telegram", defaults=params)

        """Все логи уровня SUCCESS и выше отсылаются в телегу"""
        logger.add(tg_handler, level="SUCCESS", format="{message}")

    while True:
        try:
            await AvitoParse(
                url=url,
                count=int(num_ads),
                keysword_list=keys.split(","),
                max_price=int(max_price),
                min_price=int(min_price),
                geo=geo,
                delay=int(delay),
            ).parse()
            logger.info(f"Пауза {int(freq)} мин")
            time.sleep(int(freq) * 60)
        except Exception as error:
            logger.error(error)
            logger.error(
                "Произошла ошибка, но работа будет продолжена через 30 сек. "
                "Если ошибка повторится несколько раз - перезапустите скрипт."
                "Если и это не поможет - обратитесь к разработчику по ссылке ниже"
            )
            asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
