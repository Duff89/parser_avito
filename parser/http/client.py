"""
Клиент для запросов парсера (curl_cffi)
"""
import random
import time
from curl_cffi import requests
from loguru import logger

from parser.cookies.base import CookiesProvider
from parser.proxies.proxy import Proxy


class HttpClient:
    def __init__(
        self,
        proxy: Proxy,
        cookies: CookiesProvider | None = None,
        timeout: int = 20,
        max_retries: int = 5,
        retry_delay: int = 5,
        block_threshold: int = 3,
    ):
        self.proxy = proxy
        self.cookies = cookies
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.block_threshold = block_threshold

        self._block_attempts = 0

    def _build_client(self) -> requests.Session:
        session = requests.Session(
            impersonate="chrome",
        )

        _chrome_version = str(random.randint(140, 147))
        headers = {
            'accept': '*/*',
            'accept-language': 'ru-RU,ru;q=0.9',
            'priority': 'u=1, i',
            'referer': 'https://www.avito.ru',
            'sec-ch-ua': f'"Google Chrome";v="{_chrome_version}", "Not.A/Brand";v="8", "Chromium";v="{_chrome_version}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-requested-with': 'XMLHttpRequest',
            'x-source': 'client-browser',
            "user-agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          f"AppleWebKit/537.36 (KHTML, like Gecko) "
                          f"Chrome/{_chrome_version}.0.0.0 Safari/537.36",
        }

        session.headers.update(headers)

        proxy = self.proxy.get_httpx_proxy()
        if proxy:
            session.proxies = {
                "http": proxy,
                "https": proxy,
            }

        return session

    def request(self, method: str, url: str, **kwargs):
        last_exc = None

        for attempt in range(1, self.max_retries + 1):
            try:
                with self._build_client() as client:

                    if self.cookies:
                        kwargs.setdefault("cookies", self.cookies.get())

                    response = client.request(
                        method,
                        url,
                        timeout=self.timeout,
                        allow_redirects=True,
                        **kwargs,
                    )

                # === обновление cookies ===
                if self.cookies:
                    self.cookies.update(response)

                # === обработка блокировок ===
                if response.status_code in (401, 403, 429):
                    self._block_attempts += 1

                    logger.warning(
                        f"Запрос заблокирован ({response.status_code}), "
                        f"попытка {self._block_attempts}"
                    )

                    if self._block_attempts >= self.block_threshold:
                        logger.warning("Достигнут лимит блокировок, запускается обработка")

                        if self.cookies:
                            self.cookies.handle_block()

                        self.proxy.handle_block()
                        self._block_attempts = 0

                    time.sleep(self.retry_delay)
                    continue

                # === успех ===
                response.raise_for_status()
                self._block_attempts = 0
                return response

            except requests.RequestsError as e:
                last_exc = e
                logger.warning(f"Request error (attempt {attempt}): {e}")
                time.sleep(self.retry_delay)

        raise RuntimeError("HTTP request failed after retries") from last_exc