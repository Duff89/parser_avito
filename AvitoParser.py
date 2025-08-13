import threading
import time
from pathlib import Path

import flet as ft
from loguru import logger

from lang import *
from load_config import save_avito_config, load_avito_config
from parser_cls import AvitoParse
from tg_sender import SendAdToTg
from version import VERSION


def main(page: ft.Page):
    page.title = f'Parser Avito v {VERSION}'
    page.window.icon = str(Path(__file__).parent / "assets" / "logo.ico")
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.window.width = 1000
    page.window.height = 980
    page.window.min_width = 650
    page.window.min_height = 500
    page.padding = 20
    is_run = False
    stop_event = threading.Event()

    def set_up():
        """Загружает настройки из config.toml и применяет к интерфейсу"""
        try:
            config = load_avito_config("config.toml")
        except Exception as err:
            logger.error(f"Ошибка при загрузке конфига: {err}")
            return

        url_input.value = "\n".join(config.urls or [])
        tg_chat_id.value = "\n".join(config.tg_chat_id or [])
        tg_token.value = config.tg_token or ""
        count_page.value = str(config.count)
        keys_word_white_list.value = "\n".join(config.keys_word_white_list or [])
        keys_word_black_list.value = "\n".join(config.keys_word_black_list or [])
        max_price.value = str(config.max_price)
        min_price.value = str(config.min_price)
        geo.value = config.geo or ""
        proxy.value = config.proxy_string or ""
        proxy_change_ip.value = config.proxy_change_url or ""
        pause_general.value = config.pause_general or 60
        pause_between_links.value = config.pause_between_links or 5
        max_age.value = config.max_age or 0
        seller_black_list.value = "\n".join(config.seller_black_list or [])

        page.update()

    def to_int_safe(value, default=0):
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def save_config():
        """Сохраняет настройки в TOML, безопасно обрабатывая пустые значения"""
        config = {"avito": {
            "tg_token": tg_token.value or "",
            "tg_chat_id": tg_chat_id.value.splitlines() if tg_chat_id.value else [],
            "urls": url_input.value.splitlines() if url_input.value else [],
            "count": to_int_safe(count_page.value, 1),
            "keys_word_white_list": keys_word_white_list.value.splitlines() if keys_word_white_list.value else [],
            "keys_word_black_list": keys_word_black_list.value.splitlines() if keys_word_black_list.value else [],
            "seller_black_list": seller_black_list.value.splitlines() if seller_black_list.value else [],
            "max_price": to_int_safe(max_price.value, 99999999),
            "min_price": to_int_safe(min_price.value, 0),
            "geo": geo.value or "",
            "proxy_string": proxy.value or "",
            "proxy_change_url": proxy_change_ip.value or "",
            "pause_general": to_int_safe(pause_general.value, 3),
            "pause_between_links": to_int_safe(pause_between_links.value, 1),
            "max_age": to_int_safe(max_age.value, 0),
            "max_count_of_retry": to_int_safe(max_count_of_retry.value, 5),
        }}

        save_avito_config(config)
        logger.debug("Настройки сохранены в config.toml")

    def close_dlg(e):
        dlg_modal_proxy.open = False
        page.update()

    def logger_console_init():
        logger.add(logger_console_widget, format="{time:HH:mm:ss} - {message}")

    def logger_console_widget(message):
        console_widget.value += message
        page.update()

    def telegram_log_test(e):
        """Тестирование отправки сообщения в telegram"""
        logger.info("Сейчас будет проверка данных telegram")
        token = tg_token.value
        chat_id = tg_chat_id.value
        if all([token, chat_id]):
            SendAdToTg(
                bot_token=token,
                chat_id=chat_id.split()
            ).send_to_tg()
            return
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
                              PROXY_LINK)),
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
        result = check_string()
        if not result:
            return
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
            for _ in range(int(pause_general.value if pause_general.value else 300)):
                time.sleep(1)
                if not is_run:
                    logger.info("Завершено")
                    start_btn.text = "Старт"
                    start_btn.disabled = False
                    page.update()
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

    def check_string():
        if proxy.value and "proxy.site" not in proxy.value:
            dlg_modal = ft.AlertDialog(
                modal=True,
                title=ft.Text("Проблемы с прокси"),
                content=ft.Text(UNSUPPORT_PROXY),
                actions=[
                    ft.TextButton("Купить совместимые прокси",
                                  on_click=lambda e: page.launch_url(
                                      PROXY_LINK)),
                    ft.TextButton("Понятно", on_click=lambda e: page.close(dlg_modal)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
                on_dismiss=lambda e: print("Окно закрыто"),
            )
            page.open(dlg_modal)
            return False
        return True

    def run_process():
        config = load_avito_config("config.toml")
        parser = AvitoParse(config, stop_event=stop_event)
        parsing_thread = threading.Thread(target=parser.parse)
        parsing_thread.start()
        parsing_thread.join()
        start_btn.disabled = False
        start_btn.text = "Старт"
        page.update()

    label_required = ft.Text("Обязательные параметры", size=20)
    url_input = ft.TextField(
        label="Вставьте начальную ссылку или ссылки. Используйте Enter между значениями",
        multiline=True,
        min_lines=3,
        max_lines=100,
        expand=True,
        tooltip=URL_INPUT_HELP,
        text_size=12,
        height=70,

    )
    min_price = ft.TextField(label="Минимальная цена", width=400, expand=True, text_size=12, height=40,
                             tooltip=MIN_PRICE_HELP)
    max_price = ft.TextField(label="Максимальная цена", width=400, expand=True, text_size=12, height=40,
                             tooltip=MAX_PRICE_HELP)
    label_not_required = ft.Text("Дополнительные параметры", height=30)
    keys_word_white_list = ft.TextField(
        label="Ключевые слова (через Enter)",
        multiline=True,
        min_lines=1,
        max_lines=50,
        width=400,
        expand=True,
        tooltip=KEYWORD_INPUT_HELP,
        text_size=12, height=60,
    )
    keys_word_black_list = ft.TextField(
        label="Черный список ключевых слов (через Enter)",
        multiline=True,
        min_lines=1,
        max_lines=50,
        width=400,
        expand=True,
        tooltip=KEYWORD_BLACK_INPUT_HELP,
        text_size=12, height=60,
    )
    count_page = ft.TextField(label="Количество страниц", width=400, expand=True, tooltip=COUNT_PAGE_HELP, text_size=12,
                              height=40, )
    pause_general = ft.TextField(label="Пауза в секундах между повторами", width=400, expand=True, text_size=12,
                                 height=40, tooltip=PAUSE_GENERAL_HELP)
    pause_between_links = ft.TextField(label="Пауза в секундах между каждой ссылкой", width=400, text_size=12,
                                       height=40, expand=True, tooltip=PAUSE_BETWEEN_LINKS_HELP)

    max_age = ft.TextField(label="Макс. возраст объявления (в сек.)", width=400, text_size=12, height=40, expand=True,
                           tooltip=MAX_AGE_HELP)
    max_count_of_retry = ft.TextField(label="Макс. кол-во повторов", width=400, text_size=12, height=40, expand=True,
                                      tooltip=MAX_COUNT_OF_RETRY_HELP)
    tg_token = ft.TextField(label="Token telegram", width=400, text_size=12, height=40, expand=True,
                            tooltip=TG_TOKEN_HELP)
    tg_chat_id = ft.TextField(label="Chat id telegram. Можно несколько", width=400,
                              multiline=True, expand=True, text_size=12, height=40, tooltip=TG_CHAT_ID_HELP)
    btn_test_tg = ft.ElevatedButton(text="Проверить tg", disabled=False, on_click=telegram_log_test, expand=True,
                                    tooltip=BTN_TEST_TG_HELP)
    proxy = ft.TextField(label="Прокси в формате username:password@mproxy.site:port", width=400, expand=True,
                         tooltip=PROXY_HELP)
    proxy_change_ip = ft.TextField(
        label="Ссылка для изменения IP, в формате https://changeip.mobileproxy.space/?proxy_key=***", width=400,
        expand=True, tooltip=PROXY_CHANGE_IP_HELP)
    proxy_btn_help = ft.ElevatedButton(text="Подробнее про прокси", on_click=open_dlg_modal, expand=True,
                                       tooltip=PROXY_BTN_HELP_HELP)
    geo = ft.TextField(label="Ограничение по городу", width=400, expand=True, text_size=12, height=40,
                       tooltip=GEO_HELP)
    seller_black_list = ft.TextField(
        label="Черный список продавцов (через Enter)",
        multiline=True,
        min_lines=1,
        max_lines=100,
        expand=True,
        tooltip=BLACK_LIST_OF_SELLER_HELP,
        text_size=12,
        height=60,
    )
    start_btn = ft.FilledButton("Старт", width=800, on_click=start_parser, expand=True)
    stop_btn = ft.OutlinedButton("Стоп", width=980, on_click=stop_parser, visible=False,
                                 style=ft.ButtonStyle(bgcolor=ft.colors.RED_400), expand=True)
    console_widget = ft.Text(width=800, height=100, color=ft.colors.GREEN, value="", selectable=True,
                             expand=True)  # , bgcolor=ft.colors.GREY_50)

    buy_me_coffe_btn = ft.TextButton("Продвинуть разработку",
                                     on_click=lambda e: page.launch_url(DONAT_LINK),
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
            # ft.Text(""),
            label_not_required,

            ft.Row(
                [keys_word_white_list, keys_word_black_list],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
            ),
            ft.Row(
                [count_page, pause_general],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
            ),
            ft.Row(
                [geo, pause_between_links],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
            ),
            ft.Row(
                [max_age, max_count_of_retry],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
            ),
            seller_black_list,
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

        ],
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,

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
        page.add(ft.Column(
            [all_field],
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO
        ))

    set_up()
    start_page()
    logger_console_init()


ft.app(
    target=main,
    assets_dir="assets",
)
