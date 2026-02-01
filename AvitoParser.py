import threading
import time
from pathlib import Path

import flet as ft
from loguru import logger

from dto import AvitoConfig
from integrations.notifications.factory import build_notifier
from lang import *
from load_config import save_avito_config, load_avito_config
from parser_cls import AvitoParse
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

    page.window.center()

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
        vk_token.value = config.vk_token or ""
        vk_user_id.value = "\n".join(config.vk_user_id or [])
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
        ignore_ads_in_reserv.value = config.ignore_reserv
        ignore_promote_ads.value = config.ignore_promotion
        max_count_of_retry.value = config.max_count_of_retry or 5
        one_time_start.value = config.one_time_start
        one_file_for_link.value = config.one_file_for_link
        parse_views.value = config.parse_views
        save_xlsx.value = config.save_xlsx
        use_webdriver.value = config.use_webdriver
        cookies_api_key.value = config.cookies_api_key

        page.update()

    def to_int_safe(value, default=0):
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def save_config():
        """Сохраняет настройки в TOML"""
        config = {"avito": {
            "tg_token": tg_token.value or "",
            "tg_chat_id": tg_chat_id.value.splitlines() if tg_chat_id.value else [],
            "vk_token": vk_token.value or "",
            "vk_user_id": vk_user_id.value.splitlines() if vk_user_id.value else [],
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
            "ignore_reserv": ignore_ads_in_reserv.value,
            "ignore_promotion": ignore_promote_ads.value,
            "one_time_start": one_time_start.value,
            "one_file_for_link": one_file_for_link.value,
            "parse_views": parse_views.value,
            "save_xlsx": save_xlsx.value,
            "use_webdriver": use_webdriver.value,
            "cookies_api_key": cookies_api_key.value
        }}

        save_avito_config(config)
        logger.debug("Настройки сохранены в config.toml")

    def close_dlg(e):
        dlg_modal_proxy.open = False
        page.update()

    def logger_console_init():
        logger.add(logger_console_widget, format="{time:HH:mm:ss} - {message}")

    def logger_console_widget(message):
        console_widget.controls.append(
            ft.Text(
                message.rstrip(), # убираем перенос строки с логов
                size=12,
                color=ft.colors.GREEN,
            )
        )
        page.update()

    def telegram_log_test(e):
        """Тестирование отправки уведомлений"""
        logger.info("Проверка настроек уведомлений")

        try:
            config = AvitoConfig(
                tg_token=tg_token.value,
                tg_chat_id=tg_chat_id.value.split(),
                urls=[] # заглушка
            )

            notifier = build_notifier(config=config)
            notifier.notify(message="✅ Это тестовое сообщение")

        except Exception as err:
            logger.error(f"Ошибка при проверке Telegram: {err}")

    def vk_log_test(e):
        """Тестирование отправки уведомлений VK"""
        logger.info("Проверка настроек VK")

        try:
            config = AvitoConfig(
                vk_token=vk_token.value,
                vk_user_id=vk_user_id.value.splitlines(),
                urls=[] # заглушка
            )

            notifier = build_notifier(config=config)
            notifier.notify(message="✅ Это тестовое сообщение от парсера Avito")

        except Exception as err:
            logger.error(f"Ошибка при проверке VK: {err}")

    dlg_modal_proxy = ft.AlertDialog(
        modal=True,
        title=ft.Text("Помощь по разделу:"),
        content=ft.Container(
            content=ft.Text(PROXY_PANEL_HELP, size=14),
            width=600,
            height=600,
            padding=10
        ),
        actions=[
            ft.TextButton("Купить прокси",
                          on_click=lambda e: page.launch_url(
                              PROXY_LINK)),
            ft.TextButton("Зарегистрироваться на spfa.ru",
                          on_click=lambda e: page.launch_url(
                              SPFA_LINK)),
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
            if one_time_start.value:
                stop_event.set()
                page.window.close()

    def stop_parser(e):
        nonlocal is_run
        stop_event.set()
        logger.debug("Стоп")
        is_run = False
        console_widget.height = 100
        stop_btn.visible = False
        start_btn.visible = True
        start_btn.text = "Останавливаюсь..."
        start_btn.disabled = True
        page.update()

    def check_string():
        if proxy.value and ("proxy.site" not in proxy.value or "@" not in proxy.value):
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


    def panel(title: str, content: list[ft.Control], expanded=False):
        panel_ref = ft.Ref[ft.ExpansionPanel]()

        def toggle(e):
            panel_ref.current.expanded = not panel_ref.current.expanded
            page.update()

        return ft.ExpansionPanel(
            ref=panel_ref,
            header=ft.Container(
                content=ft.ListTile(
                    title=ft.Text(title, weight=ft.FontWeight.BOLD),
                ),
                on_click=toggle,
            ),
            content=ft.Container(
                content=ft.Column(content, spacing=10),
                padding=15
            ),
            expanded=expanded
        )

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
    min_price = ft.TextField(label="Минимальная цена", width=300, expand=True, text_size=12, height=40,
                             tooltip=MIN_PRICE_HELP)
    max_price = ft.TextField(label="Максимальная цена", width=300, expand=True, text_size=12, height=40,
                             tooltip=MAX_PRICE_HELP)
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
    count_page = ft.TextField(label="Количество страниц", width=450, expand=True, tooltip=COUNT_PAGE_HELP, text_size=12,
                              height=40, )
    pause_general = ft.TextField(label="Пауза в секундах между повторами", width=400, expand=True, text_size=12,
                                 height=40, tooltip=PAUSE_GENERAL_HELP)
    pause_between_links = ft.TextField(label="Пауза в секундах между каждой ссылкой", width=400, text_size=12,
                                       height=40, expand=True, tooltip=PAUSE_BETWEEN_LINKS_HELP)

    max_age = ft.TextField(label="Макс. возраст объявления (в сек.)", width=400, text_size=12, height=40, expand=True,
                           tooltip=MAX_AGE_HELP)
    max_count_of_retry = ft.TextField(label="Макс. кол-во повторов", width=300, text_size=12, height=40, expand=True,
                                      tooltip=MAX_COUNT_OF_RETRY_HELP)
    tg_token = ft.TextField(label="Token telegram", width=400, text_size=12, height=70, expand=True,
                            tooltip=TG_TOKEN_HELP)
    tg_chat_id = ft.TextField(label="Chat id telegram. Можно несколько через Enter", width=400,
                              multiline=True, expand=True, text_size=12, height=70, tooltip=TG_CHAT_ID_HELP)
    btn_test_tg = ft.ElevatedButton(text="Проверить tg", disabled=False, on_click=telegram_log_test, expand=True,
                                    tooltip=BTN_TEST_TG_HELP)
    vk_token = ft.TextField(label="Token VK (сообщества)", width=400, text_size=12, height=70, expand=True,
                            tooltip="Токен доступа VK API от имени сообщества")
    vk_user_id = ft.TextField(label="User ID VK (username). Можно несколько через Enter", width=400,
                              multiline=True, expand=True, text_size=12, height=70,
                              tooltip="Username или ID пользователей VK для отправки сообщений")
    btn_test_vk = ft.ElevatedButton(text="Проверить VK", disabled=False, on_click=vk_log_test, expand=True,
                                    tooltip="Отправить тестовое сообщение в VK")
    proxy = ft.TextField(label="Прокси в формате username:password@mproxy.site:port", width=400, expand=True,
                         tooltip=PROXY_HELP)
    proxy_change_ip = ft.TextField(
        label="Ссылка для изменения IP, в формате https://changeip.mobileproxy.space/?proxy_key=*** (только для мобильных прокси)", width=400,
        expand=True, tooltip=PROXY_CHANGE_IP_HELP)
    proxy_btn_panel_help = ft.FilledButton(text="Помощь", on_click=open_dlg_modal, expand=True,
                                       tooltip=PROXY_BTN_HELP_HELP)


    proxy_help_icon = ft.Icon(
        ft.icons.HELP_OUTLINE,
        tooltip="Cправка по прокси:\n\n"
                "• Если есть мобильный прокси — заполните оба поля\n"
                "• Если это серверный прокси — только первое поле\n"
                "• Не знаете, что это вообще такое - кликайте <Помощь> ниже\n",
    )

    cookies_api_key = ft.TextField(
        label="API ключ сервиса обхода блокировок spfa.ru (опционально)",
        password=True,
        can_reveal_password=True,
        expand=True,
    )
    bypass_api_key_help_icon = ft.Icon(
        ft.icons.HELP_OUTLINE,
        tooltip="api-key:\n\n"
                "• Зарегистрируйтесь на spfa.ru, чтобы его получить\n"
                "• Данный ключ поможет в обходе блокировок\n"
    )

    account_login_btn = ft.ElevatedButton(
        text="🔐 Войти в свой аккаунт (опционально)",
        icon=ft.icons.LOGIN,
        disabled=True,
        tooltip="Еще не реализовано"
    )
    account_login_btn_help_icon = ft.Icon(
        ft.icons.HELP_OUTLINE,
        tooltip="Можно использовать свой аккаунт:\n\n"
                "• Такой способ будет стабильно работать\n"
                "• Есть риск блокировки этого аккаунта\n"
    )

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
        height=50,
    )
    start_btn = ft.FilledButton("Старт", width=800, on_click=start_parser, expand=True)
    stop_btn = ft.OutlinedButton("Стоп", width=980, on_click=stop_parser, visible=False,
                                 style=ft.ButtonStyle(bgcolor=ft.colors.RED_400), expand=True)
    console_widget = ft.ListView(
        expand=True,
        spacing=2,
        auto_scroll=True,
    )

    buy_me_coffe_btn = ft.TextButton("Продвинуть разработку",
                                     on_click=lambda e: page.launch_url(DONAT_LINK),
                                     style=ft.ButtonStyle(color=ft.colors.GREEN_300), expand=True,
                                     tooltip=BUY_ME_COFFE_BTN_HELP)
    report_issue_btn = ft.TextButton("Сообщить о проблеме", on_click=lambda e: page.launch_url(
        "https://github.com/Duff89/parser_avito/issues"), style=ft.ButtonStyle(color=ft.colors.GREY), expand=True,
                                     tooltip=REPORT_ISSUE_BTN_HELP)
    ignore_ads_in_reserv = ft.Checkbox(label="Игнор-ть резервы", value=True, tooltip=IGNORE_RESERV_HELP)
    ignore_promote_ads = ft.Checkbox(label="Игнор-ть продвинутые", value=False)
    one_time_start = ft.Checkbox(label="Выключить после завершения работы", value=False, tooltip=ONE_TIME_START_HELP)
    one_file_for_link = ft.Checkbox(label="Отдельный файл для каждой ссылки", value=False,
                                    tooltip=ONE_FILE_FOR_LINK_HELP)
    parse_views = ft.Checkbox(label="Парсить просмотры", value=False,
                                    tooltip=PARSE_VIEWS_HELP)
    save_xlsx = ft.Checkbox(label="Сохранять в Excel", value=True,
                              tooltip=SAVE_XLSX_HELP)

    use_webdriver = ft.Checkbox(label="Использовать браузер", value=True,
                            tooltip=USE_WEBDRIVER_HELP)

    accordion = ft.ExpansionPanelList(
        expand_icon_color=ft.colors.GREEN_300,
        elevation=2,
        divider_color=ft.colors.GREY_700,
        controls=[
            panel(
                "🔴 Основные параметры",
                [
                    url_input,
                    ft.Row([min_price, max_price]),
                    count_page,
                ],
                expanded=True
            ),

            panel(
                "🟡 Фильтрация",
                [
                    ft.Row([keys_word_white_list, keys_word_black_list]),
                    seller_black_list,
                    ft.Row([geo,max_age]),
                    ft.Row([ignore_ads_in_reserv, ignore_promote_ads]),
                ]
            ),

            panel(
                "📨 Уведомления",
                [
                    ft.Text("Telegram", weight=ft.FontWeight.BOLD),
                    ft.Row([tg_token, tg_chat_id]),
                    btn_test_tg,

                    ft.Divider(),

                    ft.Text("VK", weight=ft.FontWeight.BOLD),
                    ft.Row([vk_token, vk_user_id]),
                    btn_test_vk
                ]
            ),

            panel(
                "🌐 Прокси и обход блокировок",
                [
                    ft.Row([proxy, proxy_change_ip, proxy_help_icon]),
                    ft.Row([cookies_api_key, bypass_api_key_help_icon]),
                    ft.Row([account_login_btn, account_login_btn_help_icon]),
                    ft.Row([proxy_btn_panel_help], alignment=ft.MainAxisAlignment.CENTER,
                spacing=0)
                ]
            ),

            panel(
                "⚙️ Поведение парсера",
                [
                    ft.Row([pause_general, pause_between_links]),
                    max_count_of_retry,
                    ft.Row([one_time_start, one_file_for_link]),
                    ft.Row([parse_views, save_xlsx]),
                ]
            ),

            panel(
                "▶️ Запуск",
                [
                    console_widget,
                    start_btn,
                    stop_btn,
                ]
            ),
        ]
    )

    other_btn = ft.Row(
        [buy_me_coffe_btn, report_issue_btn],
        alignment=ft.MainAxisAlignment.CENTER
    )

    def start_page():
        page.add(
            ft.Column(
                [
                    other_btn,
                    accordion,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                spacing=20
            )
        )

    set_up()
    start_page()
    logger_console_init()


ft.app(
    target=main,
    assets_dir="assets",
)
