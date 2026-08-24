import subprocess
import sys
import os
from loguru import logger


def _get_browsers_path() -> str:
    """
    Возвращает корректный путь к браузерам Playwright для текущей ОС.
    """
    home = os.path.expanduser("~")
    if os.name == "nt":  # Windows
        return os.path.join(home, "AppData", "Local", "ms-playwright")
    if sys.platform == "darwin":  # macOS
        return os.path.join(home, "Library", "Caches", "ms-playwright")
    # Linux и прочие
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
        # === Указываем корректный путь к браузерам для текущей ОС ===
        browsers_path = _get_browsers_path()
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path

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

