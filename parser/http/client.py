"""
Клиент для запросов парсера (curl_cffi)
"""
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
        timeout: int = 30,
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
        self._client = self._build_client()

    def _build_client(self) -> requests.Session:
        fingerprint = self.cookies.get_fingerprint() if self.cookies else None
        fingerprint = fingerprint if isinstance(fingerprint, dict) else {}
        fingerprint_headers = fingerprint.get("headers", {})
        fingerprint_headers = (
            fingerprint_headers if isinstance(fingerprint_headers, dict) else {}
        )
        user_agent = fingerprint_headers.get("user-agent")
        if not user_agent and self.cookies:
            user_agent = self.cookies.get_user_agent()
        user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/150.0.0.0 Safari/537.36"
        )
        is_mobile = " Mobile " in user_agent
        impersonate = fingerprint.get("impersonate") or "chrome"
        session = requests.Session(impersonate=impersonate)
        default_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            "referer": "https://www.avito.ru/",
            'sec-ch-ua': '"Not=A?Brand";v="99", "Google Chrome";v="149", "Chromium";v="149"',
            'sec-ch-ua-mobile': '?1' if is_mobile else '?0',
            'sec-ch-ua-platform': '"Android"' if is_mobile else '"Windows"',
            'user-agent': user_agent,
        }
        headers = {**default_headers, **fingerprint_headers}
        headers["user-agent"] = user_agent
        session.headers.update(headers)
        if self.cookies:
            session.cookies.update(self.cookies.get())

        proxy = self.proxy.get_httpx_proxy()
        if proxy:
            session.proxies = {
                "http": proxy,
                "https": proxy,
            }

        return session

    def _reset_client(self) -> None:
        self._client.close()
        self._client = self._build_client()

    def request(self, method: str, url: str, **kwargs):
        last_exc = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs,
                )

                if self.cookies:
                    self.cookies.update(response)

                print(response.url)
                if response.status_code in (403, 429, 439):
                    self._block_attempts += 1
                    logger.warning(
                        f"Запрос заблокирован ({response.status_code}) к {url}, "
                        f"попытка {self._block_attempts}"
                    )

                    if self._block_attempts >= self.block_threshold:
                        logger.warning("Достигнут лимит блокировок, запускается обработка")
                        if self.cookies:
                            self.cookies.handle_block()
                        self.proxy.handle_block()
                        self._reset_client()
                        self._block_attempts = 0

                    time.sleep(self.retry_delay)
                    continue

                self._block_attempts = 0
                response.raise_for_status()
                return response

            except requests.RequestsError as e:
                last_exc = e
                self._block_attempts = 0
                logger.warning(f"Request error (attempt {attempt}): {e}")
                time.sleep(self.retry_delay)

        raise RuntimeError("HTTP запросы были неуспешными") from last_exc