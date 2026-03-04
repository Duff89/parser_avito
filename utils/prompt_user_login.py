import asyncio
import json
from playwright.async_api import async_playwright, Playwright
from loguru import logger
from playwright_setup import ensure_playwright_installed
from pathlib import Path

logger.add("logs/app.log", rotation="5 MB", retention="5 days", level="DEBUG")

PLAYWRIGHT_STATE_FILE = "storage/own_cookies.json"

# Черный список - куки которые точно не нужны. Данный блок работает, но требует доп проверки
BLACKLIST_COOKIES = {
    # Технические/трекинговые куки
    '_gid', '_gat',
    'tmr_*', 'tmr_lvid*', 'tmr_detect', 'fpestid',
    '_fbp', '_fbc',
    'ajs_*', 'amplitude_*',
    '__utm*', '__utma', '__utmb', '__utmc', '__utmt', '__utmz',

    # Куки метрик и аналитики
    '_ym_uid', '_ym_counter', '_ym_metrika_enabled',
    '_gaexp', '_gac_*',
    'mp_*_mixpanel',

    # Рекламные куки
    '_gcl_*', '_gcl_au',
    'IDE', 'test_cookie',

    # Куки A/B тестов
    'ab_test_*', 'exp_*', 'experiment_*',

    # Технические куки браузера
    'viewport_width', 'viewport_height',
    'screenResolution', 'colorDepth',
    'pixelRatio', 'timezone',

    # Локальные куки авито (не влияющие на авторизацию)
    'previousSearch', 'search_*', 'favorites_*',
    'viewed_*', 'recently_viewed',
    'location_*', 'city_*',

    # Куки с длинными значениями (часто трекинг)
    '_avif', '_avmc', '_avte', '_avts',
    '__gads', '__gpi',

    'cookiesyncs', 'idt_*', 'rt_*', 'gcfids', 'afp_cookie', 'sn', 'PVID', 'VID', 'XSRF-TOKEN',
    'utid', 'JWT-Cookie', 'adudid', 'BeeAID', 'suuid3', 'ut',
}

# Белый список - важные куки для авторизации
WHITELIST_COOKIES = {
    'auth',           # Основная кука авторизации (1)
    'sessid',         # Сессионная JWT (eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9...)
    'srv_id',         # Серверная аффинити (gsxTJnj0KXn10fKe...)
    '_avisc',         # Важная кука Авито (Nl9q37dBvbQI/Ik8fI749yI97NLC8hcB2m7z9Va3l+E=)
    'rt',             # Возможно refresh token (bc99429e1eb701a934c8eef9b2f4feca)
    'uid',            # User ID (в ваших куках это поле 'u': '3bjjr2uy.1diokuo.1j946umhj8900')
    'user_id',        # Альтернативный ID пользователя
    'sid',            # Session ID
    'csrf',           # CSRF токен
    'csrftoken',      # Альтернативный CSRF токен
    'csprefid',       # Предпочтения безопасности (0f54b430-f125-48eb-aede-518922621a73)
    'cssid',          # Сессия (79489a5a-c67a-4e27-8a95-110ef1a3c7b7)
    'f',              # Возможно fingerprint (5.0c4f4b6d233fb90636b4dd61b04726f1eca7eef0...)
    'ft',             # Fingerprint токен ("qJJhi32H1q/njHeDODNujPlx2UaHkRAt9MC23OiqFubgewLUSOyvAy9Eeb1SqOULuCcyqaNh9Z8Ku4GOiq2VqtqmCvuMMwSfUTe+W+e3MetDC8mdYt5ua5TEi80fqk8RYn1tzgQgjSMK8PJaappHsQ==")
    'sx',             # Сессионные данные (H4sIAAAAAAAC%2F6pWMjMzM0tOMTdLszSzNDUzMbNMNU9KNbZMMTc1SE42T7FUsqpWKlOyUvIqNfSLCjfJz3HySwtJNHVX0lFKVbIyNDc3NLU0NjYyqa0FBAAA%2F%2F8xG4okTAAAAA%3D%3D)
}


def should_keep_cookie(cookie_name: str) -> bool:
    """
    Проверяет, нужно ли сохранять куку
    """
    # Сначала проверяем белый список (если кука в белом списке - сохраняем)
    for whitelist_pattern in WHITELIST_COOKIES:
        if whitelist_pattern.endswith('*'):
            # Паттерн с wildcard
            if cookie_name.startswith(whitelist_pattern[:-1]):
                return True
        elif cookie_name == whitelist_pattern:
            return True

    # Проверяем черный список
    for blacklist_pattern in BLACKLIST_COOKIES:
        if blacklist_pattern.endswith('*'):
            # Паттерн с wildcard
            if cookie_name.startswith(blacklist_pattern[:-1]):
                return False
        elif cookie_name == blacklist_pattern:
            return False

    # По умолчанию не сохраняем куки, которых нет в белом списке
    return False


async def prompt_user_login(playwright: Playwright):
    ensure_playwright_installed("chromium")
    chromium = playwright.chromium
    launch_args = {
        "headless": False,
        "chromium_sandbox": False,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--start-maximized",
        ]
    }
    context_args = {
        "is_mobile": False,
        "has_touch": False,
        "locale": "ru-RU",
        "no_viewport": True,
    }
    try:
        browser = await chromium.launch(**launch_args)
        context = await browser.new_context(**context_args)
        page = await context.new_page()
    except:
        logger.error("Не удалось запустить графический браузер")
        return

    # Переходим на страницу авторизации
    await page.goto(url="https://www.avito.ru/#login?authsrc=h", timeout=0)

    # Проверяем на наличие капчи
    if "Доступ ограничен" in await page.title():
        await page.reload()

    logger.info("Пожалуйста, авторизуйтесь в браузере. Ожидание cookies auth=1...")

    # Ожидаем появления cookies с auth=1
    auth_detected = False
    try:
        while not auth_detected:
            await asyncio.sleep(1)

            cookies = await context.cookies()

            for cookie in cookies:
                if cookie.get('name') == 'auth' and cookie.get('value') == '1':
                    auth_detected = True
                    logger.info("Обнаружена успешная авторизация (cookie auth=1)")
                    break

            if not page.context.browser.is_connected():
                logger.error("Браузер был закрыт пользователем")
                return

    except Exception as e:
        logger.error(f"Ошибка при ожидании авторизации: {e}")
        return

    # Сохраняем только нужные куки
    await asyncio.sleep(5) # пауза, чтобы все куки прогрузились
    try:
        cookies = await context.cookies()

        # Фильтруем куки
        filtered_cookies = {}
        skipped_cookies = []

        for cookie in cookies:
            cookie_name = cookie['name']

            if should_keep_cookie(cookie_name):
                filtered_cookies[cookie_name] = cookie['value']
                logger.debug(f"Сохранена кука: {cookie_name}")
            else:
                skipped_cookies.append(cookie_name)

        # Сохраняем в файл
        state_filepath = Path(PLAYWRIGHT_STATE_FILE)
        state_filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(state_filepath, 'w', encoding='utf-8') as f:
            json.dump({"cookies": filtered_cookies}, f, indent=2, ensure_ascii=False)

        # Устанавливаем права на файл
        try:
            state_filepath.chmod(0o600)
        except:
            pass

        await context.close()

        # Логируем статистику
        logger.info(f"Сессия сохранена в {PLAYWRIGHT_STATE_FILE}")
        logger.info(f"Сохранено кук: {len(filtered_cookies)}")
        logger.info(f"Пропущено кук: {len(skipped_cookies)}")

        if skipped_cookies:
            logger.debug(f"Пропущенные куки: {', '.join(skipped_cookies[:10])}" +
                         ("..." if len(skipped_cookies) > 10 else ""))

    except Exception as e:
        logger.error(f"Не удалось записать сессию в файл {PLAYWRIGHT_STATE_FILE}: {e}")


async def wrapper():
    async with async_playwright() as playwright:
        await prompt_user_login(playwright)


if __name__ == "__main__":
    asyncio.run(wrapper())