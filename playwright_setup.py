import subprocess
import sys
import os
from loguru import logger


def get_browsers_dir() -> str:
    """
    Возвращает каталог, в котором Playwright хранит браузеры для текущей ОС.
    """
    custom_dir = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if custom_dir:
        return custom_dir

    home = os.path.expanduser("~")
    if sys.platform == "win32":
        return os.path.join(home, "AppData", "Local", "ms-playwright")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Caches", "ms-playwright")
    return os.path.join(home, ".cache", "ms-playwright")


def _browser_installed(browser: str) -> bool:
    """
    Проверяет, установлен ли браузер именно той ревизии,
    которую ожидает текущая версия Playwright.
    """
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            executable = getattr(p, browser).executable_path
            return bool(executable) and os.path.exists(executable)
    except Exception as err:
        logger.debug(f"Не удалось проверить наличие браузера {browser}: {err}")
        return False


def ensure_playwright_installed(browser: str = "chromium"):
    """
    Проверяет наличие браузеров Playwright нужной ревизии и
    переопределяет путь для exe-сборки. Устанавливает их при необходимости.
    """
    try:
        # Для exe-сборки под Windows путь нужно задать явно.
        # Пользовательский PLAYWRIGHT_BROWSERS_PATH сохраняется.
        if sys.platform == "win32":
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = get_browsers_dir()

        if _browser_installed(browser):
            logger.debug("Playwright уже установлен, хорошо")
            return

        logger.info(f"Playwright не найден. Устанавливаю {browser}...")
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", browser],
            check=True,
        )

    except Exception as e:
        logger.warning(f"Ошибка при установке\\проверке Playwright: {e}")
