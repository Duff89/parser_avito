import asyncio
import random
import httpx
from loguru import logger
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from typing import Optional, Dict, List
from pathlib import Path

from dto import Proxy, ProxySplit
from playwright_setup import ensure_playwright_installed
from load_config import load_avito_config

MAX_RETRIES = 3
RETRY_DELAY = 10
RETRY_DELAY_WITHOUT_PROXY = 300
BAD_IP_TITLE = "проблема с ip"


class PlaywrightClient:
    def __init__(
            self,
            proxy: Proxy = None,
            headless: bool = True,
            user_agent: Optional[str] = None,
            stop_event=None
    ):
        self.proxy = proxy
        self.proxy_split_obj = self.get_proxy_obj()
        self.headless = headless
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        self.context = self.page = self.browser = None
        self.stop_event = stop_event

    @staticmethod
    def check_protocol(ip_port: str) -> str:
        if "http://" not in ip_port:
            return f"http://{ip_port}"
        return ip_port

    @staticmethod
    def del_protocol(proxy_string: str):
        if "//" in proxy_string:
            return proxy_string.split("//")[1]
        return proxy_string

    def get_proxy_obj(self) -> ProxySplit | None:
        if not self.proxy:
            return None
        try:
            self.proxy.proxy_string = self.del_protocol(proxy_string=self.proxy.proxy_string)
            if "@" in self.proxy.proxy_string:
                ip_port, user_pass = self.proxy.proxy_string.split("@")
                if "." in user_pass:
                    ip_port, user_pass = user_pass, ip_port
                login, password = str(user_pass).split(":")
            else:
                login, password, ip, port = self.proxy.proxy_string.split(":")
                if "." in login:
                    login, password, ip, port = ip, port, login, password
                ip_port = f"{ip}:{port}"

            ip_port = self.check_protocol(ip_port=ip_port)

            return ProxySplit(
                ip_port=ip_port,
                login=login,
                password=password,
                change_ip_link=self.proxy.change_ip_link
            )
        except Exception as err:
            logger.error(err)
            logger.critical("Прокси в таком формате не поддерживаются. "
                            "Используй: ip:port@user:pass или ip:port:user:pass")

    @staticmethod
    def parse_cookie_string(cookie_str: str) -> dict:
        return dict(pair.split("=", 1) for pair in cookie_str.split("; ") if "=" in pair)

    async def launch_browser(self):
        ensure_playwright_installed("chromium")

        try:
            config = load_avito_config("config.toml")
        except Exception as err:
            logger.error(f"Ошибка загрузки конфига: {err}")

        stealth = Stealth()
        self.playwright_context = stealth.use_async(async_playwright())
        playwright = await self.playwright_context.__aenter__()
        self.playwright = playwright

        launch_args = {
            "headless": self.headless,
            "chromium_sandbox": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--start-maximized",
                "--window-size=1920,1080",
            ]
        }

        self.browser = await playwright.chromium.launch(**launch_args)

        context_args = {
            "user_agent": self.user_agent,
            "viewport": {"width": 1920, "height": 1080},
            "screen": {"width": 1920, "height": 1080},
            "device_scale_factor": 1,
            "is_mobile": False,
            "has_touch": False,
        }

        if isinstance(config.playwright_state_file,str) and config.playwright_state_file != "":
            context_args["storage_state"] = config.playwright_state_file
            logger.debug(f"Используем Playwright state file {config.playwright_state_file}")
        else:
            logger.debug("Playwright state file не задан. Используем пустой контекст Playwright.")

        if self.proxy_split_obj:
            context_args["proxy"] = {
                "server": self.proxy_split_obj.ip_port,
                "username": self.proxy_split_obj.login,
                "password": self.proxy_split_obj.password
            }

        self.context = await self.browser.new_context(**context_args)
        self.page = await self.context.new_page()
        # block images, not use now
        # await self.page.route("**/*", lambda route, request: asyncio.create_task(self._block_images(route, request)))
        await self._stealth(self.page)

    async def load_page(self, url: str):
        try:
            config = load_avito_config("config.toml")
        except Exception as err:
            logger.error(f"Ошибка загрузки конфига: {err}")
        await self.page.goto(url=url,
                             timeout=60_000,
                             wait_until="domcontentloaded")

        for attempt in range(10):
            if self.stop_event and self.stop_event.is_set():
                return {}
            await self.check_block(self.page, self.context)
            if isinstance(config.playwright_state_file,str) and config.playwright_state_file != "":
                try:
                    state_file = config.playwright_state_file
                    state_filepath = Path(state_file)
                    state_filepath.touch(mode=0o600, exist_ok=True) # Set mode to protect sensitive cookies
                    storage = await self.context.storage_state(path=state_filepath)
                    logger.info("Сессия пользователя Авито сохранена в " + state_file)
                except:
                    logger.error("Не удалось записать сессию в файл " + state_file)
            raw_cookie = await self.context.cookies(["https://avito.ru","https://www.avito.ru"])
            cookie_dict = self.convert_cookies_from_playwright_to_requests(raw_cookie)
            if cookie_dict.get("ft"):
                logger.info("Cookies получены")
                return cookie_dict
            await asyncio.sleep(5)

        logger.warning("Не удалось получить cookies")
        return {}

    @staticmethod
    def convert_cookies_from_playwright_to_requests(context_cookies: List) -> dict:
        cookie_dict = dict()
        for cookie in context_cookies:
            cookie_dict[cookie["name"]] = cookie["value"]
        return cookie_dict

    async def extract_cookies(self, url: str) -> dict:
        try:
            await self.launch_browser()
            return await self.load_page(url)
        finally:
            if hasattr(self, "browser"):
                if self.browser:
                    await self.browser.close()
            if hasattr(self, "playwright"):
                await self.playwright.stop()
            if hasattr(self, "playwright_context") and self.playwright_context:
                await self.playwright_context.__aexit__(None, None, None)

    async def get_cookies(self, url: str) -> dict:
        return await self.extract_cookies(url)

    async def check_block(self, page, context):
        title = await page.title()
        logger.info(f"Не ошибка, а название страницы: {title}")
        if BAD_IP_TITLE in str(title).lower():
            logger.info("IP заблокирован")
            await context.clear_cookies()
            await self.change_ip()
            await page.reload(timeout=60 * 1000)

    async def change_ip(self, retries: int = MAX_RETRIES):
        if not self.proxy_split_obj:
            logger.info("Сейчас бы сменили ip, но прокси нет - поэтому ждем")
            for i in range(RETRY_DELAY_WITHOUT_PROXY):
                if self.stop_event and self.stop_event.is_set():
                    return False
                await asyncio.sleep(1)
            return False
        for attempt in range(1, retries + 1):
            try:
                response = httpx.get(self.proxy_split_obj.change_ip_link + "&format=json", timeout=20)
                if response.status_code == 200:
                    logger.info(f"IP изменён на {response.json().get('new_ip')}")
                    return True
                else:
                    logger.warning(f"[{attempt}/{retries}] Ошибка смены IP: {response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"[{attempt}/{retries}] Ошибка смены IP: {e}")

            if attempt < retries:
                logger.info(f"Повторная попытка сменить IP через {RETRY_DELAY} секунд...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                logger.error("Превышено количество попыток смены IP")
                return False

    @staticmethod
    async def _stealth(page):
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)

    @staticmethod
    async def _block_images(route, request):
        if request.resource_type == "image":
            await route.abort()
        else:
            await route.continue_()


async def get_cookies(proxy: Proxy = None, headless: bool = True, stop_event=None) -> tuple:
    logger.info("Пытаюсь обновить cookies")
    client = PlaywrightClient(
        proxy=proxy,
        headless=headless,
        stop_event=stop_event
    )
    ads_id = str(random.randint(1111111111, 9999999999))
    cookies = await client.get_cookies(f"https://www.avito.ru/{ads_id}")
    return cookies, client.user_agent
