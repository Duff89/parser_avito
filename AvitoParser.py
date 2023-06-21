#!/usr/bin/env python3

"""
AvitoParser - Поиск объявлений на avito.ru по цене или ключевым словам
by Duff89 (https://github.com/Duff89)
"""
__version__ = 1.06

import threading, tkinter, time
import webbrowser
import configparser

from loguru import logger
from notifiers.logging import NotificationHandler

from parser_cls import AvitoParse
from tooltip import ToolTip


class Window(tkinter.Tk):
    def __init__(self):
        tkinter.Tk.__init__(self)
        self.width_entry_field = 80
        self.resizable(width=True, height=True)
        self.title(f"AvitoParser v.{__version__}")
        self.is_run = False
        self.main_windows_init()
        self.logger_widget_init()
        self.tg_logger_init = False

    def main_windows_init(self):
        """Инициализация всех полей"""
        self.set_up()
        self.token_label = tkinter.Label(self, text="ТОКЕН TELEGRAM:")
        self.token_label.grid(row=0, column=0, pady=5, sticky='e')
        self.token_entry = tkinter.Entry(self, width=self.width_entry_field)
        self.token_entry.grid(row=0, column=1, pady=5, sticky='w')
        self.token_entry.insert(0, self.tg_token_env)

        self.chat_id_label = tkinter.Label(self, text="CHAT ID TELEGRAM:")
        self.chat_id_label.grid(row=1, column=0, pady=5, sticky='e')
        self.chat_id_entry = tkinter.Entry(self, width=self.width_entry_field)
        self.chat_id_entry.grid(row=1, column=1, pady=5, sticky='w')
        self.chat_id_entry.insert(0, self.chat_id_env)

        self.key_label = tkinter.Label(self, text="КЛЮЧЕВЫЕ СЛОВА:")
        self.key_label.grid(row=2, column=0, pady=5, sticky='e')
        self.key_entry = tkinter.Entry(self, width=self.width_entry_field)
        self.key_entry.grid(row=2, column=1, pady=5, sticky='w')
        self.key_entry.insert(0, self.keys_env)

        self.ads_label = tkinter.Label(self, text="КОЛИЧЕСТВО СТРАНИЦ:")
        self.ads_label.grid(row=3, column=0, pady=5, sticky='e')
        self.ads_entry = tkinter.Entry(self, width=self.width_entry_field)
        self.ads_entry.grid(row=3, column=1, pady=5, sticky='w')
        self.ads_entry.insert(0, self.num_ads_env)

        self.freq_label = tkinter.Label(self, text="ПАУЗА В МИН.:")
        self.freq_label.grid(row=4, column=0, pady=5, sticky='e')
        self.freq_entry = tkinter.Entry(self, width=self.width_entry_field)
        self.freq_entry.grid(row=4, column=1, pady=5, sticky='w')
        self.freq_entry.insert(0, self.freq_env)

        self.url_label = tkinter.Label(self, text="URL*:")
        self.url_label.grid(row=5, column=0, pady=5, sticky='e')
        self.url_entry = tkinter.Entry(self, width=self.width_entry_field)
        self.url_entry.grid(row=5, column=1, pady=5, sticky='w')
        self.url_entry.insert(0, self.start_url_env)

        self.min_price_label = tkinter.Label(self, text="Минимальная цена:")
        self.min_price_label.grid(row=6, column=0, pady=5, sticky='e')
        self.min_price_entry = tkinter.Entry(self, width=self.width_entry_field)
        self.min_price_entry.grid(row=6, column=1, pady=5, sticky='w')
        self.min_price_entry.insert(0, str(self.min_price_env))

        self.max_price_label = tkinter.Label(self, text="Максимальная цена:")
        self.max_price_label.grid(row=7, column=0, pady=5, sticky='e')
        self.max_price_entry = tkinter.Entry(self, width=self.width_entry_field)
        self.max_price_entry.grid(row=7, column=1, pady=5, sticky='w')
        self.max_price_entry.insert(0, str(self.max_price_env))

        self.test_button = tkinter.Button(self, text="Тест", padx=50, command=self.telegram_log_test)
        self.test_button.grid(row=1, column=2, padx=0, pady=0)

        link_label = tkinter.Label(self, text="Связаться с автором или сообщить о проблеме",
                                   fg="blue", cursor="hand2")
        link_label.grid(column=1, row=200, pady=10)
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/Duff89/parser_avito"))

        link_label = tkinter.Label(self, text="Поддержать развитие проекта",
                                   fg="blue", cursor="hand2")
        link_label.grid(column=1, row=201, pady=10)
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://yoomoney.ru/to/410014382689862"))


        # кнопка "Старт"
        self.start_btn()

        ToolTip(self.token_entry, "Введите токен telegram").bind()
        ToolTip(self.chat_id_entry, "Введите chat_id Вашего диалога в telegram").bind()
        ToolTip(self.ads_entry, "Сколько страниц проверять каждый раз").bind()
        ToolTip(self.freq_entry, "Пауза между повторами. В минутах").bind()
        ToolTip(self.url_entry, "Адрес с которого нужно начинать").bind()
        ToolTip(self.key_entry, "Ключевые слова. Вводить через запятую, регистр не важен").bind()
        ToolTip(self.min_price_entry,
                "Будет искать только объявления, где цена больше либо равна введенному значению. "
                "Оставьте 0 если Вам не нужен этот параметр").bind()
        ToolTip(self.max_price_entry,
                "Будет искать только объявления, где цена меньше либо равна введенному значению").bind()


    def telegram_log_test(self):
        """Тестирование отправки сообщения в telegram"""
        #if not self.tg_logger_init:
        self.logger_tg()
        token = self.token_entry.get()
        chat_id = self.chat_id_entry.get()
        if all([token, chat_id]):
            logger.success('test')

            logger.info('Если сообщение пришло к Вам в telegram - значит всё настроено правильно. Если нет - '
                        'результат парсинга всегда можно посмотреть в папке result или ниже')
            return None
        logger.info("Должны быть заполнены поля ТОКЕН TELEGRAM и CHAT ID TELEGRAM")

    def start_scraping(self):
        """Кнопка старт. Запуск"""
        self.logger_tg()

        """Если URL все-таки не заполнен"""
        url = self.url_entry.get()
        if not url:
            logger.info("Внимание! URL - обязательный параметр. Пример ссылки:")
            logger.info("https://www.avito.ru/moskva/remont_i_stroitelstvo/sadovaya_tehnika-ASgBAgICAURYnAI")
            return
        """Прячем кнопку старт"""
        self.is_run = True
        self.start_button.configure(text='Работает', state='disabled')
        self.start_button.destroy()
        self.update()
        logger.info("Начинаем поиск")

        """Размещаем кнопку Стоп"""
        self.stop_button = tkinter.Button(self, text="Стоп", padx=50, command=self.stop_scraping)
        self.stop_button.grid(row=8, column=0, columnspan=2, padx=5, pady=5)

        """Сохраняем конфиг"""
        self.save_config()

        """Основной цикл"""
        while self.is_run:
            self.run_parse()
            if not self.is_run: break
            logger.info("Проверка завершена")
            logger.info(f"Пауза {self.frequency} минут")
            for _ in range(int(self.frequency) * 60):
                time.sleep(1)
                if not self.is_run: break

        """Убираем кнопку Стоп и создаем старт"""
        self.stop_button.destroy()
        logger.info("Успешно остановлено")
        self.start_btn()
        self.update()

    def start_btn(self):
        """Кнопка старт. Старт работы"""
        self.start_button = tkinter.Button(self,
                                           padx=50,
                                           text="Старт",
                                           command=lambda: self.is_run or
                                                           threading.Thread(target=self.start_scraping).start())
        self.start_button.grid(row=8, column=0, columnspan=2, padx=5, pady=5)

    def stop_scraping(self):
        """Кнопка стоп. Остановка работы"""
        logger.info("Идет остановка. Пожалуйста, подождите")
        self.is_run = False
        self.stop_button.configure(text='Останавливаюсь', state='disabled', padx=5, pady=5)
        self.update()

    def set_up(self):
        """Работа с настройками"""

        self.config = configparser.ConfigParser()  # создаём объекта парсера
        self.config.read("settings.ini")  # читаем конфиг
        self.start_url_env = self.config["Avito"]["URL"]
        self.chat_id_env = self.config["Avito"]["CHAT_ID"]
        self.tg_token_env = self.config["Avito"]["TG_TOKEN"]
        self.num_ads_env = self.config["Avito"]["NUM_ADS"]
        self.freq_env = self.config["Avito"]["FREQ"]
        self.keys_env = self.config["Avito"]["KEYS"]
        self.max_price_env = self.config["Avito"].get("MAX_PRICE", "0")
        self.min_price_env = self.config["Avito"].get("MIN_PRICE", "0")

    def save_config(self):
        """Сохраняет конфиг"""
        self.config["Avito"]["TG_TOKEN"] = self.token_entry.get()
        self.config["Avito"]["CHAT_ID"] = self.chat_id_entry.get()
        self.config["Avito"]["URL"] = str(self.url_entry.get()).replace('%', '%%')  # bugfix
        self.config["Avito"]["NUM_ADS"] = self.ads_entry.get()
        self.config["Avito"]["FREQ"] = self.freq_entry.get()
        self.config["Avito"]["KEYS"] = self.key_entry.get()
        self.config["Avito"]["MAX_PRICE"] = self.max_price_entry.get()
        self.config["Avito"]["MIN_PRICE"] = self.min_price_entry.get()
        with open('settings.ini', 'w') as configfile:
            self.config.write(configfile)

    def logger_tg(self):
        """Логирование в telegram"""
        token = self.token_entry.get()
        chat_id = self.chat_id_entry.get()
        if self.tg_logger_init: return
        if token and chat_id:
            params = {
                'token': token,
                'chat_id': chat_id
            }
            tg_handler = NotificationHandler("telegram", defaults=params)

            """Все логи уровня SUCCESS и выше отсылаются в телегу"""
            logger.add(tg_handler, level="SUCCESS", format="{message}")
            self.tg_logger_init = True
            return None
        logger.info("Данные для отправки в telegram не заполнены. Результат будет сохранен в файл и выведен здесь")

    def logger_widget_init(self):
        """Инициализация логирования в widget"""
        self.log_widget = tkinter.Text(self, wrap="word")
        self.log_widget.grid(row=9, column=0, columnspan=3, padx=5)
        self.log_widget.config(width=123, height=35)
        logger.add(self.logger_text_widget, format="{time:HH:mm:ss} - {message}")
        logger.info("Запуск AvitoParser")
        logger.info("Чтобы начать работу, проверьте, чтобы поле URL было заполненными, "
                    "остальное на Ваше усмотрение. Нужна помощь - нажмите на ссылку внизу окна.")
        logger.info("Удачного поиска !!!")

    def logger_text_widget(self, message):
        """Логирование в log_widget (окно приложения)"""
        self.log_widget.insert(tkinter.END, message)
        self.log_widget.see(tkinter.END)

    def run_parse(self):
        """Запуск парсера"""
        url = self.url_entry.get()
        num_ads = self.ads_entry.get() or 5
        keys = self.key_entry.get()
        self.frequency = self.freq_entry.get() or 5
        max_price = self.max_price_entry.get()
        min_price = self.min_price_entry.get()

        AvitoParse(
            url=url,
            count=int(num_ads),
            keysword_list=keys.split(","),
            max_price=int(max_price),
            min_price=int(min_price),
        ).parse()


if __name__ == '__main__':
    Window().mainloop()
