import json
import os
import subprocess

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
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
                 tg_token=None,
                 max_price=0
                 ):
        self.url = url
        self.keys_word = keysword_list
        self.count = count
        self.data = []
        self.tg_token = tg_token
        self.title_file = self.__get_file_title()
        self.max_price = int(max_price)

    def __set_up(self):

        options = Options()
        options.add_argument('--headless')
        self.driver = uc.Chrome(version_main=self.__get_chrome_version, options=options)

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

        with open('viewed.txt', 'r') as file:
            self.viewed_list = list(map(str.rstrip, file.readlines()))
            """Ограничение количества просмотренных объявлений"""
            if len(self.viewed_list) > 2000:
                self.viewed_list = self.viewed_list[-900:]

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
                if any([item.lower() in description.lower() for item in self.keys_word]) and int(
                        price) <= self.max_price:
                    self.data.append(data)
                    """Отправляем в телеграм"""
                    logger.success(f"{data['url']} {data['description']}")
            elif int(price) <= self.max_price:
                self.data.append(data)
                """Отправляем в телеграм"""
                logger.success(f"{data['url']} {data['description']}")
            else:
                continue
        self.__save_data()

    def is_viewed(self, ads_id: str) -> bool:
        """Проверяет, смотрели мы это или нет"""
        if ads_id in self.viewed_list:
            return True
        return False

    def __save_data(self):
        """Сохраняет результат в файл keyword*.json"""
        os.makedirs(os.path.dirname("result/"), exist_ok=True)
        if self.data:
            with open(f"result/{self.title_file}.json", 'a', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)

        """сохраняет просмотренные объявления"""
        with open('viewed.txt', 'w') as file:
            for item in set(self.viewed_list):
                file.write("%s\n" % item)

    def __get_file_title(self) -> str:
        """Определяет название файла"""
        if self.keys_word != ['']:
            title_file = "-".join(list(map(str.lower, self.keys_word)))

        else:
            title_file = 'all'
        return title_file

    def parse(self):
        """Метод для вызова"""
        self.__set_up()
        self.__get_url()
        try:
            self.__paginator()
        except Exception as error:
            logger.error(f"Ошибка: {error}")
        finally:
            self.driver.quit()
