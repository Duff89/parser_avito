import asyncio
from playwright.async_api import async_playwright, Playwright
from loguru import logger
from playwright_setup import ensure_playwright_installed
from pathlib import Path

from load_config import load_avito_config

logger.add("logs/app.log", rotation="5 MB", retention="5 days", level="DEBUG")

async def prompt_user_login(playwright: Playwright):
    try:
        config = load_avito_config("config.toml")
    except Exception as err:
        logger.error(f"Ошибка загрузки конфига: {err}")

    if isinstance(config.playwright_state_file,str):
        logger.info("Сессия будет сохранена в Playwright state file " + config.playwright_state_file)
    else:
        logger.error("Playwright state file не задан. Сессия не будет сохранён")
        return

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

    # Waiting for 2fa response because it's enabled on all Avito accounts
    try:
        async with page.expect_response(url_or_predicate="https://www.avito.ru/web/2/tfa/auth", timeout=0) as response_info:
            await page.goto(url="https://www.avito.ru/#login?authsrc=h", timeout=0)
            # Reloading the page sometimes helps to bypass captcha (!)
            if "Доступ ограничен" in await page.title():
                await page.reload() 

    except:
        logger.error("Браузер неожиданно закрыт. Сессия не будет сохранена")
        return


    try:
        state_file = config.playwright_state_file
        state_filepath = Path(state_file)
        state_filepath.touch(mode=0o600, exist_ok=True) # Set mode to protect sensitive cookies
        storage = await context.storage_state(path=state_filepath)
        await context.close()
        logger.info("Сессия пользователя Авито сохранена в " + state_file)
    except:
        logger.error("Не удалось записать сессию в файл " + state_file)

async def wrapper():
    async with async_playwright() as playwright:
        await prompt_user_login(playwright)

if __name__ == "__main__":
    asyncio.run(wrapper())
