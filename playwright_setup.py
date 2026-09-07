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


def ensure_playwright_installed(browser: str = "chromium"):
    """
    Проверяет наличие браузеров Playwright и переопределяет путь для exe-сборки.
    Устанавливает их при необходимости.
    """
    try:
        # === Указываем правильный путь к браузерам ===
        # Для exe-сборки под Windows путь нужно задать явно, на остальных ОС
        # Playwright сам находит свой каталог с браузерами.
        ms_playwright_dir = get_browsers_dir()
        if sys.platform == "win32":
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = ms_playwright_dir

        browsers_exist = os.path.isdir(ms_playwright_dir) and any(
            name.startswith(browser) for name in os.listdir(ms_playwright_dir)
        )

        if not browsers_exist:
            logger.info(f"Playwright не найден. Устанавливаю {browser}...")
            subprocess.run([sys.executable, "-m", "playwright", "install", browser], check=True)
        else:
            logger.debug("Playwright уже установлен, хорошо")

    except Exception as e:
        logger.warning(f"Ошибка при установке\проверке Playwright: {e}")

