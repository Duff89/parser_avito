#!/usr/bin/env python3

"""
AvitoParser - Поиск объявлений на avito.ru по цене или ключевым словам
by Duff89 (https://github.com/Duff89)
"""
__version__ = 1.08

import customtkinter

import threading, tkinter, time
import webbrowser
import configparser

from loguru import logger
from notifiers.logging import NotificationHandler

from parser_cls import AvitoParse


customtkinter.set_appearance_mode("dark")

class Window(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("528x590")
        self.width_entry_field = 500
        self.resizable(width=False, height=False)
        self.title(f"AvitoParser v.{__version__}")
        self.is_run = False
        self.main_windows_init()
        self.logger_widget_init()
        self.tg_logger_init = False

        """Центрируем окно относительно экрана"""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = self.winfo_width()
        window_height = self.winfo_height()
        x_pos = (screen_width - window_width) // 2
        y_pos = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")

        self.checkbox_frame = FeedbackFrame(self)
        self.checkbox_frame.grid(row=11, column=0, columnspan=2, pady=10, sticky="s")


    def main_windows_init(self):
        """Инициализация всех полей"""
        self.set_up()
        self.token_label = customtkinter.CTkLabel(self, text="Token:")
        self.token_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.token_entry = customtkinter.CTkEntry(self, width=self.width_entry_field, placeholder_text="Введите токен вашего Telegram бота")
        self.token_entry.grid(row=0, column=1, pady=5, sticky='w')
        self.token_entry.insert(0, self.tg_token_env)

        self.chat_id_label = customtkinter.CTkLabel(self, text="Chat ID:")
        self.chat_id_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.chat_id_entry = customtkinter.CTkEntry(self, width=self.width_entry_field, placeholder_text="Введите ID чата вашего диалога в Telegram")
        self.chat_id_entry.grid(row=1, column=1, pady=5, sticky='w')
        self.chat_id_entry.insert(0, self.chat_id_env)

        self.key_label = customtkinter.CTkLabel(self, text="Ключевые слова:")
        self.key_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.key_entry = customtkinter.CTkEntry(self, width=self.width_entry_field, placeholder_text="Через запятую(регистр не важен)")
        self.key_entry.grid(row=2, column=1, pady=5, sticky='w')
        self.key_entry.insert(0, self.keys_env)

        self.ads_label = customtkinter.CTkLabel(self, text="Количество страниц:")
        self.ads_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.ads_entry = customtkinter.CTkEntry(self, width=self.width_entry_field, placeholder_text="Сколько страниц проверять каждый раз")
        self.ads_entry.grid(row=3, column=1, pady=5, sticky='w')
        self.ads_entry.insert(0, self.num_ads_env)

        self.freq_label = customtkinter.CTkLabel(self, text="Пауза:")
        self.freq_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.freq_entry = customtkinter.CTkEntry(self, width=self.width_entry_field, placeholder_text="Пауза между повторами. В минутах")
        self.freq_entry.grid(row=4, column=1, pady=5, sticky='w')
        self.freq_entry.insert(0, self.freq_env)

        self.url_label = customtkinter.CTkLabel(self, text="Url:")
        self.url_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.url_entry = customtkinter.CTkEntry(self, width=self.width_entry_field, placeholder_text="Адрес с которого нужно начинать")
        self.url_entry.grid(row=5, column=1, pady=5, sticky='w')
        self.url_entry.insert(0, self.start_url_env)

        self.min_price_label = customtkinter.CTkLabel(self, text="Минимальная цена:")
        self.min_price_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.min_price_entry = customtkinter.CTkEntry(self, width=self.width_entry_field, placeholder_text="Цена больше либо равна введенному значению")
        self.min_price_entry.grid(row=6, column=1, pady=5, sticky='w')
        self.min_price_entry.insert(0, str(self.min_price_env))

        self.max_price_label = customtkinter.CTkLabel(self, text="Максимальная цена:")
        self.max_price_label.grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.max_price_entry = customtkinter.CTkEntry(self, width=self.width_entry_field, placeholder_text="Цена меньше либо равна введенному значению")
        self.max_price_entry.grid(row=7, column=1, pady=5, sticky='w')
        self.max_price_entry.insert(0, str(self.max_price_env))

        self.test_button = customtkinter.CTkButton(self, text="Получить тестовое уведомление", command=self.telegram_log_test)
        self.test_button.grid(row=9, column=1, pady=5, padx=(0, 6), sticky="ew")

        # кнопка "Старт"
        self.start_btn()

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
        self.stop_button = customtkinter.CTkButton(self, text="Стоп", command=self.stop_scraping)
        self.stop_button.grid(row=9, column=0, padx=5, pady=5, sticky="ew")

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
        self.start_button = customtkinter.CTkButton(self,
                                           text="Старт",
                                           command=lambda: self.is_run or
                                                           threading.Thread(target=self.start_scraping).start())
        self.start_button.grid(row=9, column=0, padx=5, pady=5, sticky="ew")

    def stop_scraping(self):
        """Кнопка стоп. Остановка работы"""
        logger.info("Идет остановка. Пожалуйста, подождите")
        self.is_run = False
        self.stop_button.configure(text='Останавливаюсь', state='disabled', row=9, column=0, padx=5, pady=5, sticky="ew")
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
        self.log_widget = customtkinter.CTkTextbox(self, wrap="word", width=650, height=300, text_color="#00ff26")
        self.log_widget.grid(row=10, padx=5, pady=(10, 0), column=0, columnspan=2)
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
        max_price = self.max_price_entry.get() or 1000000
        min_price = self.min_price_entry.get() or 0

        AvitoParse(
            url=url,
            count=int(num_ads),
            keysword_list=keys.split(","),
            max_price=int(max_price),
            min_price=int(min_price),
        ).parse()

class FeedbackFrame(customtkinter.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        link_label = customtkinter.CTkLabel(self, text="Связаться с автором или сообщить о проблеме",
                                   text_color="grey60", cursor="hand2")
        link_label.grid(column=1, row=1, padx=10, pady=5,)
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/Duff89/parser_avito"))

        link_label = customtkinter.CTkLabel(self, text="Поддержать развитие проекта",
                                   text_color="grey60", cursor="hand2")
        link_label.grid(column=1, row=2, padx=10)
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://yoomoney.ru/to/410014382689862"))


if __name__ == '__main__':
    Window().mainloop()
