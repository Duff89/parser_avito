"""
Клиент для запросов парсера (curl_cffi)
"""
import os
import sys
import time
from curl_cffi import requests
from loguru import logger

from parser.cookies.base import CookiesProvider
from parser.proxies.proxy import Proxy


def get_ca_bundle() -> str | bool:
    """
    Определяет путь к бандлу SSL-сертификатов CA либо False при их отсутствии/недоступности.
    Предотвращает сбой curl: (77) в PyInstaller-сборках (_MEIPASS) и при путях с не-ASCII символами.
    """
    # 1. Проверяем переменные окружения
    for env_var in ("SSL_CERT_FILE", "CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE"):
        path = os.environ.get(env_var)
        if path and os.path.isfile(path):
            return _normalize_ca_path(path)

    # 2. Проверяем certifi
    try:
        import certifi
        cert_path = certifi.where()
        if cert_path and os.path.isfile(cert_path):
            return _normalize_ca_path(cert_path)
    except Exception:
        pass

    # 3. Проверяем распакованный каталог PyInstaller (_MEIPASS)
    if hasattr(sys, "_MEIPASS"):
        mei_path = os.path.join(sys._MEIPASS, "certifi", "cacert.pem")
        if os.path.isfile(mei_path):
            return _normalize_ca_path(mei_path)

    # 4. Если бандл не найден на диске, отключаем проверку во избежание ошибки curl 77
    logger.warning(
        "SSL CA bundle (cacert.pem) не найден на диске. "
        "Проверка SSL будет отключена для предотвращения ошибки curl (77)."
    )
    return False


def _normalize_ca_path(path: str) -> str:
    """Преобразует путь к сертификату в формат, совместимый с Windows libcurl."""
    if sys.platform == "win32":
        # Если путь содержит не-ASCII символы (например, кириллицу в имени пользователя Windows),
        # libcurl может завершиться с ошибкой (77). Получаем короткий 8.3 путь.
        if not all(ord(c) < 128 for c in path):
            try:
                import ctypes
                buf = ctypes.create_unicode_buffer(1024)
                if ctypes.windll.kernel32.GetShortPathNameW(path, buf, 1024) > 0:
                    short_path = buf.value
                    if short_path and os.path.isfile(short_path) and all(ord(c) < 128 for c in short_path):
                        return short_path
            except Exception:
                pass
    return path


class HttpClient:
    ITEM_API_URL = "https://m.avito.ru/api/1/card/items/{item_id}"
    ITEM_API_HEADERS = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ru-RU,ru;q=0.9",
        "referer": "https://m.avito.ru/",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": (
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Mobile Safari/537.36"
        ),
    }

    def __init__(
        self,
        proxy: Proxy,
        cookies: CookiesProvider | None = None,
        timeout: int = 30,
        max_retries: int = 5,
        retry_delay: int = 5,
        block_threshold: int = 3,
        verify: str | bool | None = None,
    ):
        self.proxy = proxy
        self.cookies = cookies
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.block_threshold = block_threshold
        self.verify = get_ca_bundle() if verify is None else verify

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
        session = requests.Session(impersonate=impersonate, verify=self.verify)
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

    def _recover_session(self) -> None:
        """Сменить IP и обновить cookies в правильном порядке."""
        self.proxy.handle_block()
        if self.cookies:
            self.cookies.handle_block()
        self._reset_client()
        self._block_attempts = 0

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

                if response.status_code in (403, 429, 439):
                    self._block_attempts += 1
                    logger.warning(
                        f"Запрос заблокирован ({response.status_code}) к {url}, "
                        f"попытка {self._block_attempts}"
                    )

                    if self._block_attempts >= self.block_threshold:
                        logger.warning("Достигнут лимит блокировок, запускается обработка")
                        self._recover_session()

                    time.sleep(self.retry_delay)
                    continue

                self._block_attempts = 0
                response.raise_for_status()
                return response

            except requests.RequestsError as e:
                last_exc = e
                err_msg = str(e)

                # Перехват ошибки curl: (77) - невозможно загрузить сертификаты CA
                if (
                    "(77)" in err_msg
                    or "certificate verify locations" in err_msg
                    or "trust anchors" in err_msg
                ) and self.verify is not False:
                    logger.warning(
                        f"Ошибка curl (77) установки CA сертификата: {e}. "
                        "Автоматически переключаем HttpClient на verify=False для предотвращения падения парсера."
                    )
                    self.verify = False
                    self._reset_client()
                    continue

                self._block_attempts += 1
                logger.warning(f"Request error (attempt {attempt}): {e}")
                if self._block_attempts >= self.block_threshold:
                    logger.warning(
                        "Достигнут лимит сетевых ошибок, "
                        "обновляем proxy и cookies"
                    )
                    self._recover_session()
                time.sleep(self.retry_delay)

        raise RuntimeError("HTTP запросы были неуспешными") from last_exc

    def fetch_item_data(self, item_id: int) -> dict:
        """Загрузить JSON карточки объявления через mobile API."""
        response = self.request(
            "GET",
            self.ITEM_API_URL.format(item_id=item_id),
            headers=self.ITEM_API_HEADERS.copy(),
        )
        logger.info(f"Карточка {item_id}: HTTP {response.status_code}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Ответ карточки не является JSON-объектом")
        return payload
