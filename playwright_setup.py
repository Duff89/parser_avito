import asyncio
import concurrent.futures
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


if sys.platform == "win32":
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", get_browsers_dir())


def _check_browser_sync(browser: str) -> bool:
    """
    Выполняет синхронную проверку наличия браузера через sync_playwright.
    Должно вызываться в потоке без активного asyncio event loop.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser_type = getattr(p, browser, None)
            if browser_type is None:
                return False
            executable = browser_type.executable_path
            return bool(executable) and os.path.exists(executable)
    except Exception as err:
        logger.debug(f"Не удалось проверить наличие браузера {browser}: {err}")
        return False


def _browser_installed(browser: str) -> bool:
    """
    Проверяет, установлен ли браузер именно той ревизии,
    которую ожидает текущая версия Playwright.
    Безопасно работает как в обычном синхронном коде, так и внутри активного цикла asyncio (например, в Flet UI).
    """
    try:
        loop = asyncio.get_running_loop()
    except (RuntimeError, AttributeError):
        loop = None

    if loop is not None and loop.is_running():
        # Если находимся внутри цикла asyncio, sync_playwright() выбросит ошибку
        # "Playwright Sync API inside the asyncio loop".
        # Выполняем синхронную проверку в отдельном потоке без event loop.
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_check_browser_sync, browser)
                return future.result(timeout=10)
        except Exception as err:
            logger.debug(f"Ошибка при изолированной проверке браузера {browser}: {err}")
            return False
    else:
        return _check_browser_sync(browser)


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

        # В PyInstaller-сборке sys.executable указывает на сам AvitoParser.exe!
        # Вызов [sys.executable, "-m", "playwright", ...] перезапустит парсер в новом окне.
        # Вместо этого используем встроенный Node.js драйвер Playwright.
        if getattr(sys, "frozen", False):
            try:
                from playwright._impl._driver import compute_driver_executable, get_driver_env

                driver_res = compute_driver_executable()
                driver_cmd = list(driver_res) if isinstance(driver_res, tuple) else [driver_res]
                run_kwargs = {"env": get_driver_env(), "check": True}
                if sys.platform == "win32":
                    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    if no_window:
                        run_kwargs["creationflags"] = no_window
                subprocess.run(
                    [*driver_cmd, "install", browser],
                    **run_kwargs,
                )
                logger.info(f"Playwright браузер {browser} успешно установлен через встроенный драйвер.")
                return
            except Exception as e_driver:
                logger.warning(f"Не удалось установить браузер через драйвер Playwright: {e_driver}")
                try:
                    subprocess.run(["playwright", "install", browser], check=True)
                    return
                except Exception:
                    pass
                raise
        else:
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", browser],
                check=True,
            )
            logger.info(f"Playwright браузер {browser} успешно установлен.")

    except Exception as e:
        logger.warning(f"Ошибка при установке\\проверке Playwright: {e}")
