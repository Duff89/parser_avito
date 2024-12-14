import configparser
import re
import threading
import time

import flet as ft
import yaml
from loguru import logger
from notifiers.logging import NotificationHandler

from core.settings import ParserSettings

__VERSION__ = "2.0.2"

from lang import *
from parser_cls import AvitoParse


def main(page: ft.Page):
    page.title = f'Parser Avito v {__VERSION__}'
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.window.width = 1000
    page.window.height = 920
    page.window.min_width = 650
    page.window.min_height = 920
    page.padding = 20
    tg_logger_init = False
    config_pyd = ParserSettings()
    config = configparser.ConfigParser()
    config.read("settings.ini", encoding='utf-8')
    is_run = False
    stop_event = threading.Event()

    def set_up():
        """Работа с настройками"""
        nonlocal config
        tg_chat_id.value = "\n".join(config_pyd.avito.chat_ids)
        tg_token.value = config_pyd.avito.tg_token
        count_page.value = config_pyd.avito.num_ads
        pause_sec.value = config_pyd.avito.freq
        keyword_input.value = "\n".join(config_pyd.avito.keys)
        max_price.value = config_pyd.avito.max_price
        min_price.value = config_pyd.avito.min_price
        geo.value = config_pyd.avito.geo
        proxy.value = config_pyd.avito.proxy
        proxy_change_ip.value = config_pyd.avito.proxy_change_ip
        need_more_info.value = config_pyd.avito.need_more_info
        debug_mode.value = config_pyd.avito.debug_mode
        page.update()

    def save_config():
        """Сохраняет конфиг"""
        config_dump = {
            "avito": {
                "tg_token": tg_token.value,
                "chat_ids": tg_chat_id.value.split(),
                "url": str(url_input.value).replace('%', '%%').split(),
                "num_ads": count_page.value,
                "freq": pause_sec.value,
                "keys": keyword_input.value.split(),
                "max_price": max_price.value,
                "min_price": min_price.value,
                "geo": geo.value,
                "proxy": proxy.value,
                "proxy_change_ip": proxy_change_ip.value,
                "need_more_info": need_more_info.value,
                "debug_mode": debug_mode.value,
            }
        }
        with open('settings.yaml', 'w', encoding='utf-8') as configfile:
            yaml.dump(config_dump, configfile)
        logger.debug("Настройки сохранены")

    def check_tg_btn(e):
        if len(tg_chat_id.value) > 5 and len(tg_token.value) > 10:
            btn_test_tg.disabled = False
        else:
            btn_test_tg.disabled = True
        page.update()

    def close_dlg(e):
        dlg_modal_proxy.open = False
        page.update()

    def logger_console_init():
        logger.add(logger_console_widget, format="{time:HH:mm:ss} - {message}")

    def logger_console_widget(message):
        console_widget.value += message
        page.update()

    def logger_tg():
        """Логирование в telegram"""
        nonlocal tg_logger_init
        token = tg_token.value
        chat_ids = tg_chat_id.value.split()

        if tg_logger_init:
            return

        if token and chat_ids:
            for chat_id in chat_ids:
                params = {
                    'token': token,
                    'chat_id': chat_id
                }
                tg_handler = NotificationHandler("telegram", defaults=params)

                """Все логи уровня SUCCESS и выше отсылаются в телегу"""
                logger.add(tg_handler, level="SUCCESS", format="{message}")

            tg_logger_init = True
            return None

        logger.info("Данные для отправки в telegram не заполнены. Результат будет сохранен в файл и выведен здесь")

    def telegram_log_test(e):
        """Тестирование отправки сообщения в telegram"""
        logger_tg()
        token = tg_token.value
        chat_id = tg_chat_id.value
        if all([token, chat_id]):
            logger.success('test')

            logger.info(TG_TEST_MSG)
            return None
        logger.info("Должны быть заполнены поля ТОКЕН TELEGRAM и CHAT ID TELEGRAM")

    dlg_modal_proxy = ft.AlertDialog(
        modal=True,
        title=ft.Text("Подробнее насчёт прокси"),
        content=ft.Container(
            content=ft.Text(BUY_PROXY_LINK, size=20),
            width=600,
            height=400,
            padding=10
        ),
        actions=[
            ft.TextButton("Купить прокси",
                          on_click=lambda e: page.launch_url(
                              "https://mobileproxy.space/user.html?buyproxy&coupons_code=eMy-r4y-FZE-kMu")),
            ft.TextButton("Отмена", on_click=close_dlg),

        ],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=lambda e: print("Modal dialog dismissed!"),
    )

    def open_dlg_modal(e):
        page.overlay.append(dlg_modal_proxy)
        dlg_modal_proxy.open = True
        page.update()

    def start_parser(e):
        nonlocal is_run
        logger.info("Старт")
        stop_event.clear()
        save_config()
        console_widget.height = 700
        input_fields.visible = False
        start_btn.visible = False
        stop_btn.visible = True
        is_run = True
        page.update()
        while is_run and not stop_event.is_set():
            run_process()
            if not is_run:
                return
            logger.info("Пауза между повторами")
            for _ in range(int(pause_sec.value if pause_sec.value else 300)):
                time.sleep(1)
                if not is_run:
                    logger.info("Завершено")
                    return

    def stop_parser(e):
        nonlocal is_run
        stop_event.set()
        logger.debug("Стоп")
        is_run = False
        console_widget.height = 100
        input_fields.visible = True
        stop_btn.visible = False
        start_btn.visible = True
        start_btn.text = "Останавливаюсь..."
        start_btn.disabled = True
        page.update()

    def geo_change(e):
        if geo.value:
            need_more_info.value = True
        page.update()

    def run_process():
        logger_tg()
        parser = AvitoParse(
            stop_event=stop_event,
            url=url_input.value.split(),
            count=int(count_page.value),
            keysword_list=keyword_input.value.split(),
            max_price=int(max_price.value),
            min_price=int(min_price.value),
            geo=geo.value,
            proxy=proxy.value,
            proxy_change_url=proxy_change_ip.value,
            debug_mode=debug_mode.value,
            need_more_info=need_more_info.value
        )
        parsing_thread = threading.Thread(target=parser.parse)
        parsing_thread.start()
        parsing_thread.join()
        start_btn.disabled = False
        start_btn.text = "Старт"
        page.update()

    label_required = ft.Text("Обязательные параметры", size=20)
    url_input = ft.TextField(
        label="Вставьте начальную ссылку или ссылки (до 5шт.). Используйте Enter между значениями",
        multiline=True,
        min_lines=1,
        max_lines=5,
        expand=True,
        tooltip=URL_INPUT_HELP
    )
    min_price = ft.TextField(label="Минимальная цена", width=400, expand=True, tooltip=MIN_PRICE_HELP)
    max_price = ft.TextField(label="Максимальная цена", width=400, expand=True, tooltip=MAX_PRICE_HELP)
    label_not_required = ft.Text("Дополнительные параметры")
    keyword_input = ft.TextField(
        label="Ключевые слова. Используйте Enter между значениями",
        multiline=True,
        min_lines=1,
        max_lines=5,
        width=400,
        expand=True,
        tooltip=KEYWORD_INPUT_HELP
    )
    count_page = ft.TextField(label="Количество страниц", width=400, expand=True, tooltip=COUNT_PAGE_HELP)
    pause_sec = ft.TextField(label="Пауза в секундах между повторами", width=400, expand=True, tooltip=PAUSE_SEC_HELP)
    tg_token = ft.TextField(label="Token telegram", width=400, on_change=check_tg_btn, expand=True,
                            tooltip=TG_TOKEN_HELP)
    tg_chat_id = ft.TextField(label="Chat id telegram. Можно несколько", width=400, on_change=check_tg_btn,
                              multiline=True, expand=True, tooltip=TG_CHAT_ID_HELP)
    btn_test_tg = ft.ElevatedButton(text="Проверить tg", disabled=True, on_click=telegram_log_test, expand=True,
                                    tooltip=BTN_TEST_TG_HELP)
    proxy = ft.TextField(label="Прокси в формате username:password@server:port", width=400, expand=True,
                         tooltip=PROXY_HELP)
    proxy_change_ip = ft.TextField(
        label="Ссылка для изменения IP, в формате https://changeip.mobileproxy.space/?proxy_key=***", width=400,
        expand=True, tooltip=PROXY_CHANGE_IP_HELP)
    proxy_btn_help = ft.ElevatedButton(text="Подробнее про прокси", on_click=open_dlg_modal, expand=True,
                                       tooltip=PROXY_BTN_HELP_HELP)
    geo = ft.TextField(label="Ограничение по городу", width=400, on_change=geo_change, expand=True, tooltip=GEO_HELP)
    start_btn = ft.FilledButton("Старт", width=800, on_click=start_parser, expand=True)
    stop_btn = ft.OutlinedButton("Стоп", width=980, on_click=stop_parser, visible=False,
                                 style=ft.ButtonStyle(bgcolor=ft.colors.RED_400), expand=True)
    console_widget = ft.Text(width=800, height=100, color=ft.colors.GREEN, value="", selectable=True,
                             expand=True)  # , bgcolor=ft.colors.GREY_50)
    need_more_info = ft.Checkbox("Дополнительная информация", on_change=geo_change, tooltip=NEED_MORE_INFO_HELP)
    debug_mode = ft.Checkbox("Режим отладки", tooltip=DEBUG_MODE_HELP)
    buy_me_coffe_btn = ft.TextButton("Купить кофе разработчику",
                                     on_click=lambda e: page.launch_url("https://yoomoney.ru/to/410014382689862"),
                                     style=ft.ButtonStyle(color=ft.colors.GREEN_300), expand=True,
                                     tooltip=BUY_ME_COFFE_BTN_HELP)
    report_issue_btn = ft.TextButton("Сообщить о проблеме", on_click=lambda e: page.launch_url(
        "https://github.com/Duff89/parser_avito/issues"), style=ft.ButtonStyle(color=ft.colors.GREY), expand=True,
                                     tooltip=REPORT_ISSUE_BTN_HELP)
    input_fields = ft.Column(
        [
            label_required,
            url_input,
            ft.Row(
                [min_price, max_price],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
            ),
            ft.Text(""),
            label_not_required,

            ft.Row(
                [keyword_input, geo],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
            ),
            ft.Row(
                [count_page, pause_sec],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
            ),
            ft.Row(
                [tg_token, tg_chat_id],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
            ),
            btn_test_tg,
            ft.Row(
                [proxy, proxy_change_ip],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
            ),
            proxy_btn_help,
            ft.Text(""),
            ft.Row(
                [need_more_info, debug_mode],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
            ),

        ],
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

    controls = ft.Column(
        [console_widget,
         start_btn,
         stop_btn],
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )
    other_btn = ft.Row([buy_me_coffe_btn, report_issue_btn], expand=True, alignment=ft.MainAxisAlignment.CENTER)
    all_field = ft.Column([input_fields, controls, other_btn], alignment=ft.MainAxisAlignment.CENTER,
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def start_page():
        page.add(all_field, )

    set_up()
    start_page()
    logger_console_init()


ft.app(
    target=main,
)
