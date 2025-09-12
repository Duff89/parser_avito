import asyncio
import random
import httpx
from loguru import logger
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from typing import Optional, Dict, List

from dto import Proxy, ProxySplit

USER_AGENTS = [ua.strip() for ua in open("user_agent_pc.txt").readlines()]
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
    ):
        self.proxy = proxy
        self.proxy_split_obj = self.get_proxy_obj()
        self.headless = headless
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        self.context = self.page = self.browser = None

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
            logger.info(f"Не ошибка, а название страницы: {self.proxy.proxy_string}")
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

        if self.proxy_split_obj:
            context_args["proxy"] = {
                "server": self.proxy_split_obj.ip_port,
                "username": self.proxy_split_obj.login,
                "password": self.proxy_split_obj.password
            }

        self.context = await self.browser.new_context(**context_args)
        self.page = await self.context.new_page()
        # block images, not use now
        #await self.page.route("**/*", lambda route, request: asyncio.create_task(self._block_images(route, request)))
        await self._stealth(self.page)

    async def load_page(self, url: str):
        await self.page.goto(url=url,
                             timeout=60_000,
                             wait_until="domcontentloaded")

        for attempt in range(10):
            await self.check_block(self.page, self.context)
            raw_cookie = await self.page.evaluate("() => document.cookie")
            cookie_dict = self.parse_cookie_string(raw_cookie)
            if cookie_dict.get("ft"):
                logger.info("Cookies получены")
                return cookie_dict
            await asyncio.sleep(5)

        logger.warning("Не удалось получить cookies")
        return {}

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

    async def get_cookies(self, url: str) -> dict:
        return await self.extract_cookies(url)

    async def check_block(self, page, context):
        title = await page.title()
        logger.info(title)
        if BAD_IP_TITLE in str(title).lower():
            logger.info("IP заблокирован")
            await context.clear_cookies()
            await self.change_ip()
            await page.reload(timeout=60*1000)

    async def change_ip(self, retries: int = MAX_RETRIES):
        if not self.proxy_split_obj:
            logger.info("Сейчас бы сменили ip, но прокси нет - поэтому ждем")
            await asyncio.sleep(RETRY_DELAY_WITHOUT_PROXY)
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


async def get_cookies(proxy: Proxy = None, headless: bool = True) -> tuple:
    logger.info("Пытаюсь обновить cookies")
    client = PlaywrightClient(
        proxy=proxy,
        headless=headless
    )
    ads_id = str(random.randint(1111111111, 9999999999))
    cookies = await client.get_cookies(f"https://www.avito.ru/{ads_id}")
    return cookies, client.user_agent
