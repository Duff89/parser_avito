import os
import subprocess
import time
import csv
from random import choice

import undetected_chromedriver as uc
from notifiers.logging import NotificationHandler
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.window import WindowTypes
from loguru import logger
from locator import LocatorAvito


class AvitoParse:
    """
    Парсинг бесплатных товаров на avito.ru
    url - начальный url
    keysword_list- список ключевых слов
    count - сколько проверять страниц
    tg_token - токен telegram, если не передать- не будет отправки в телегу, результат будет в файле и консоли
    """

    def __init__(self,
                 url: str,
                 keysword_list: list,
                 count: int = 10,
                 tg_token: str = None,
                 max_price: int = 0,
                 min_price: int = 0
                 ):
        self.url = url
        self.keys_word = keysword_list
        self.count = count
        self.data = []
        self.tg_token = tg_token
        self.title_file = self.__get_file_title()
        self.max_price = int(max_price)
        self.min_price = int(min_price)

    def __set_up(self):
        options = Options()
        options.add_argument('--headless')
        _ua = choice(list(map(str.rstrip, open("user_agent_pc.txt").readlines())))
        options.add_argument(f'--user-agent={_ua}')
        self.driver = uc.Chrome(version_main=self.__get_chrome_version,
                                options=options,
                                )

    @property
    def __get_chrome_version(self):
        """Определяет версию chrome в зависимости от платформы"""
        if os.name == 'nt':
            import winreg
            # открываем ключ реестра, содержащий информацию о Google Chrome
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
            # считываем значение ключа "version"
            version = winreg.QueryValueEx(reg_key, "version")[0]
            return version.split(".")[0]
        else:
            output = subprocess.check_output(['google-chrome', '--version'])
            try:
                version = output.decode('utf-8').split()[-1]
                version = version.split(".")[0]
                return version
            except Exception as error:
                logger.error(error)
                logger.info("У Вас не установлен Chrome, либо он требует обновления")
                raise Exception("Chrome Exception")

    def __get_url(self):
        self.driver.get(self.url)

    def __paginator(self):
        """Кнопка далее"""
        logger.info('Страница успешно загружена. Просматриваю объявления')
        self.__create_file_csv()
        while self.count > 0:
            self.__parse_page()
            """Проверяем есть ли кнопка далее"""
            if self.driver.find_elements(*LocatorAvito.NEXT_BTN):
                self.driver.find_element(*LocatorAvito.NEXT_BTN).click()
                self.count -= 1
            else:
                logger.info("Нет кнопки дальше")
                break

    @logger.catch
    def __parse_page(self):
        """Парсит открытую страницу"""

        """Ограничение количества просмотренных объявлений"""
        if os.path.isfile('viewed.txt'):
            with open('viewed.txt', 'r') as file:
                self.viewed_list = list(map(str.rstrip, file.readlines()))
                if len(self.viewed_list) > 5000:
                    self.viewed_list = self.viewed_list[-900:]
        else:
            with open('viewed.txt', 'w') as file:
                self.viewed_list = []

        titles = self.driver.find_elements(*LocatorAvito.TITLES)
        for title in titles:
            name = title.find_element(*LocatorAvito.NAME).text
            description = title.find_element(*LocatorAvito.DESCRIPTIONS).text
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
            """Определяем нужно ли нам учитывать ключевые слова"""
            if self.keys_word != ['']:
                if any([item.lower() in description.lower() for item in self.keys_word]) and self.min_price <= int(
                        price) <= self.max_price:
                    self.data.append(self.__parse_full_page(url, data))
                    """Отправляем в телеграм"""
                    self.__pretty_log(data=data)
                    self.__save_data(data=data)
            elif self.min_price <= int(price) <= self.max_price:

                self.data.append(self.__parse_full_page(url, data))
                """Отправляем в телеграм"""
                self.__pretty_log(data=data)
                self.__save_data(data=data)
            else:
                continue

    def __pretty_log(self, data):
        """Красивый вывод"""
        logger.success(
            f'\n{data.get("name", "-")}\n'
            f'Цена: {data.get("price", "-")}\n'
            f'Описание: {data.get("description", "-")}\n'
            f'Просмотров: {data.get("views", "-")}\n'
            f'Дата публикации: {data.get("date_public", "-")}\n'
            f'Продавец: {data.get("seller_name", "-")}\n'
            f'Ссылка: {data.get("url", "-")}\n')

    def __parse_full_page(self, url: str, data: dict) -> dict:
        """Парсит для доп. информации открытое объявление на отдельной вкладке"""
        self.driver.switch_to.new_window(WindowTypes.TAB)  # новая вкладка
        self.driver.get(url)
        self.driver.switch_to.window(self.driver.window_handles[1])

        """Количество просмотров"""
        if self.driver.find_elements(*LocatorAvito.TOTAL_VIEWS):
            total_views = self.driver.find_element(*LocatorAvito.TOTAL_VIEWS).text.split()[0]
            data["views"] = total_views

        """Дата публикации"""
        if self.driver.find_elements(*LocatorAvito.DATE_PUBLIC):
            date_public = self.driver.find_element(*LocatorAvito.DATE_PUBLIC).text
            if "· " in date_public:
                date_public = date_public.replace("· ", '')
            data["date_public"] = date_public

        """Имя продавца"""
        if self.driver.find_elements(*LocatorAvito.SELLER_NAME):
            seller_name = self.driver.find_element(*LocatorAvito.SELLER_NAME).text
            if seller_name == 'Компания' and self.driver.find_elements(*LocatorAvito.COMPANY_NAME):
                seller_name = self.driver.find_element(*LocatorAvito.COMPANY_NAME) \
                    .find_element(*LocatorAvito.COMPANY_NAME_TEXT).text
            data["seller_name"] = seller_name

        """Закрывает вкладку №2 и возвращается на №1"""
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return data

    def is_viewed(self, ads_id: str) -> bool:
        """Проверяет, смотрели мы это или нет"""
        if ads_id in self.viewed_list:
            return True
        return False

    def __save_data(self, data: dict):
        """Сохраняет результат в файл keyword*.csv"""

        with open(f"result/{self.title_file}.csv", mode="a", newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                data.get("name", '-'),
                data.get("price", '-'),
                data.get("url", '-'),
                data.get("description", '-'),
                data.get("views", '-'),
                data.get("date_public", '-'),
                data.get("seller_name", '-'),
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
            with open(f"result/{self.title_file}.csv", 'r') as file:
                reader = csv.reader(file)
                writer = csv.writer(file)
                try:
                    # Попытка чтения первой строки
                    first_row = next(reader)
                except StopIteration:
                    # файл пустой
                    return True
                return False
        except FileNotFoundError:
            return True

    def __create_file_csv(self):
        """Создает файл и прописывает названия если нужно"""

        if self.__is_csv_empty:
            with open(f"result/{self.title_file}.csv", 'a') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "Название",
                    "Цена",
                    "Ссылка",
                    "Описание",
                    "Просмотров",
                    "Дата публикации",
                    "Продавец",
                ])

    def __get_file_title(self) -> str:
        """Определяет название файла"""
        if self.keys_word != ['']:
            title_file = "-".join(list(map(str.lower, self.keys_word)))

        else:
            title_file = 'all'
        return title_file

    def parse(self):
        """Метод для вызова"""
        try:
            self.__set_up()
            self.__get_url()
            self.__paginator()
        except Exception as error:
            logger.error(f"Ошибка: {error}")
        finally:
            self.driver.quit()


if __name__ == '__main__':
    """Здесь заменить данные на свои"""
    import configparser

    config = configparser.ConfigParser()  # создаём объекта парсера
    config.read("settings.ini")  # читаем конфиг
    url = config["Avito"]["URL"]
    chat_id = config["Avito"]["CHAT_ID"]
    token = config["Avito"]["TG_TOKEN"]
    num_ads = config["Avito"]["NUM_ADS"]
    freq = config["Avito"]["FREQ"]
    keys = config["Avito"]["KEYS"]
    max_price = config["Avito"].get("MAX_PRICE", "0")
    min_price = config["Avito"].get("MIN_PRICE", "0")

    if token and chat_id:
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
                keysword_list=keys.split(","),
                max_price=int(max_price),
                min_price=int(min_price)
            ).parse()
            logger.info("Пауза")
            time.sleep(int(freq) * 60)
        except Exception as error:
            logger.error(error)
            logger.error('Произошла ошибка, но работа будет продолжена через 30 сек. '
                         'Если ошибка повторится несколько раз - перезапустите скрипт.'
                         'Если и это не поможет - обратитесь к разработчику')
            time.sleep(30)
