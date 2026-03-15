"""
Клиент для запросов парсера (curl_cffi)
"""

import time
from curl_cffi import requests
from loguru import logger

from parser.cookies.base import CookiesProvider
from parser.proxies.proxy import Proxy


HEADERS = {
    "sec-ch-ua-platform": '"Windows"',
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    "sec-ch-ua-mobile": "?0",
}


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

        session.headers.update(HEADERS)

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
                        f"Blocked request ({response.status_code}), "
                        f"attempt {self._block_attempts}"
                    )

                    if self._block_attempts >= self.block_threshold:
                        logger.warning("Block threshold reached, handling block")

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