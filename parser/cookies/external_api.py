import json
import time
from pathlib import Path

import requests
from loguru import logger

from parser.cookies.base import CookiesProvider

API_URL = "https://spfa.ru/api"


class ExternalApiCookiesProvider(CookiesProvider):
    MAX_STATUS_HISTORY = 20
    PURCHASE_COOLDOWN = 600  # 10 минут

    def __init__(self, api_key: str, storage_path: str | Path = "storage/cookies_external.json"):
        self.api_key = api_key
        self.storage_path = Path(storage_path)

        self.last_id: str | None = None
        self.last_cookies: dict | None = None

        self.unblock_started_at: float | None = None
        self.UNBLOCK_TIMEOUT = 300  # 5 минут
        self.PAUSE_FOR_ERROR = 120 # 2 минуты
        self.NOT_BALANCE = 300 # 5 минуты
        self.WAIT_FIRST_FOR_UNBLOCK = 5  # 5 сек, пауза для первой разблокировки
        self.WAIT_FOR_NEW = 3  # 3 сек, пауза после покупки для стабильности
        self.WAIT_FOR_UNBLOCK = 10 # пауза при долгой разблокировке

        self.status_history: list[int] = []  # новые: последние коды
        self.last_purchase_at: float | None = None  # новые: время последней покупки

        self._load_from_disk()

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get(self) -> dict:
        if self.last_cookies:
            return self.last_cookies

        return self._get_new_cookies()

    def update(self, response):
        """
        Обновляем историю кодов ответа.
        Сохраняем на диск только при изменении или плохом коде.
        """
        if not response:
            return

        code = getattr(response, "status_code", None)
        if code is None:
            return

        last_code = self.status_history[-1] if self.status_history else None
        self.status_history.append(code)
        if len(self.status_history) > self.MAX_STATUS_HISTORY:
            self.status_history.pop(0)

        # сохраняем только если:
        # 1) код изменился относительно последнего
        # 2) код плохой (403 или 429)
        # 3) первый код (нет истории)
        if code != last_code or code in (403, 429) or last_code is None:
            self._save_to_disk()

    def handle_block(self):
        """
        Пытаемся разблокировать cookies.
        Если не получилось — получаем новые.
        """

        now = time.time()

        # ---- Нет cookies вообще ----
        if not self.last_id:
            logger.warning("⚠️ Нет cookies id — запрашиваем новые cookies")
            self._get_new_cookies()
            return

        # ---- Проверяем историю кодов и время последней покупки ----
        if self.last_purchase_at and (now - self.last_purchase_at) < self.PURCHASE_COOLDOWN:  # 10 минут
            logger.info(
                f"⏱ Последняя покупка была менее 10 минут назад | id={self.last_id} | пытаемся разблокировать"
            )
            # идем к разблокировке
        elif (
                len(self.status_history) >= self.MAX_STATUS_HISTORY
                and all(code in (403, 429) for code in self.status_history[-self.MAX_STATUS_HISTORY:])
        ):
            logger.warning(
                "⚠️ Все последние 20 кодов плохие (403/429) — покупаем новые cookies"
            )
            self._get_new_cookies()
            return

        # ---- Уже ждём разблокировку ----
        if self.unblock_started_at:
            elapsed = now - self.unblock_started_at

            if elapsed < self.UNBLOCK_TIMEOUT:
                logger.info(
                    f"⏳ Ожидаем завершения разблокировки | id={self.last_id} | прошло={int(elapsed)}с"
                )

                return

            logger.warning(
                f"⌛ Превышено время ожидания разблокировки | id={self.last_id}"
            )
            self.unblock_started_at = None  # сбрасываем и пробуем дальше

        logger.info(f"🔓 Пытаемся разблокировать cookies | id={self.last_id}")

        try:
            res = requests.post(
                f"{API_URL}/unblock/",
                json={
                    "id": self.last_id,
                    "api_key": self.api_key,
                },
                headers=self.headers,
                timeout=15,
            )
        except requests.RequestException as e:
            logger.error(
                f"❌ Ошибка при запросе к API разблокировки | id={self.last_id} | {e}"
            )
            self._get_new_cookies()
            return

        # ---- Сервер принял задачу ----
        if res.status_code in (200, 202):
            self.unblock_started_at = now
            logger.info(f"⏳ Разблокировка запущена | id={self.last_id}")
            time.sleep(self.WAIT_FIRST_FOR_UNBLOCK)
            return

        # ---- Уже в процессе ----
        if res.status_code == 409:
            self.unblock_started_at = self.unblock_started_at or now
            logger.info(f"⏳ Разблокировка уже выполняется | id={self.last_id}")
            time.sleep(self.WAIT_FOR_UNBLOCK)
            return

        # ---- Слишком поздно ----
        if res.status_code == 410:
            logger.info(f"⏰ Истёк срок разблокировки cookies | id={self.last_id}")

        # ---- Фатальные ошибки ----
        elif res.status_code == 403:
            time.sleep(self.NOT_BALANCE)
            logger.error("⛔ Доступ запрещён: неверный API key или нет прав")

        elif res.status_code == 404:
            time.sleep(self.PAUSE_FOR_ERROR)
            logger.warning(f"❌ Cookies не найдены на сервере | id={self.last_id}")

        elif res.status_code == 503:
            logger.warning("🚧 Сервис временно недоступен, ждём")
            time.sleep(self.PAUSE_FOR_ERROR)
            return

        else:
            logger.error(f"❌ Неожиданный ответ от сервера | статус={res.status_code} | тело={res.text}")
            return

        # ---- Только здесь можно покупать новые ----
        logger.warning(f"➡️ Покупаем новые cookies вместо id={self.last_id}")
        self.unblock_started_at = None
        self._get_new_cookies()

    def _get_new_cookies(self) -> dict:
        logger.info("🛒 Запрашиваем покупку новых cookies у сервиса")

        try:
            res = requests.post(
                f"{API_URL}/cookies/",
                json={"api_key": self.api_key, "full_format": True},
                headers=self.headers,
                timeout=15,
            )
        except requests.RequestException as e:
            logger.error(f"❌ Не удалось связаться с сервисом cookies | ошибка={e}")
            raise

        # ---- Обработка HTTP ошибок ----
        if res.status_code == 401:
            logger.error("⛔ Не передан API key при запросе cookies")
            time.sleep(self.PAUSE_FOR_ERROR)
            res.raise_for_status()

        if res.status_code == 403:
            logger.error("⛔ Доступ запрещён: неверный API key или недостаточно средств")
            time.sleep(self.NOT_BALANCE)
            res.raise_for_status()

        if res.status_code == 503:
            logger.warning("🚧 Сервис cookies временно недоступен (парсер не готов)")
            time.sleep(self.PAUSE_FOR_ERROR)
            res.raise_for_status()

        if not res.ok:
            logger.error(f"❌ Ошибка при покупке cookies | статус={res.status_code} | тело={res.text}")
            time.sleep(self.PAUSE_FOR_ERROR)
            res.raise_for_status()

        # ---- Успешный ответ ----
        try:
            data = res.json().get("results", {})
        except ValueError:
            logger.error("❌ Сервер вернул некорректный JSON при покупке cookies")
            raise

        self.last_id = data.get("id")
        self.last_cookies = data.get("cookies")

        if not self.last_id or not self.last_cookies:
            logger.error(f"❌ Ответ сервера без cookies | данные={data}")
            raise RuntimeError("Сервер вернул неполные данные cookies")

        self.last_purchase_at = time.time()  # новое: сохраняем дату и время покупки
        self.status_history.clear()  # сбрасываем историю последних кодов после покупки

        logger.info(f"✅ Cookies успешно получены | id={self.last_id}")

        self._save_to_disk()
        logger.debug("💾 Cookies сохранены на диск")
        time.sleep(self.WAIT_FOR_NEW)
        return self.last_cookies

    def _save_to_disk(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "id": self.last_id,
                "cookies": self.last_cookies,
                "saved_at": time.time(),
                "status_history": self.status_history,
                "last_purchase_at": self.last_purchase_at,
            }
            self.storage_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.debug("💾 Cookies сохранены на диск")
        except Exception as err:
            logger.warning(f"Не удалось сохранить cookies локально: {err}")

    def _load_from_disk(self):
        if not self.storage_path.exists():
            logger.info("Нет сохраненных cookies")
            return

        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self.last_id = data.get("id")
            self.last_cookies = data.get("cookies")
            self.status_history = data.get("status_history", [])
            self.last_purchase_at = data.get("last_purchase_at")

            if self.last_id and self.last_cookies:
                logger.info("Загружаем сохраненные cookies с диска")
            else:
                logger.warning("Cookies файл есть, но нет id или cookies в нем")

        except Exception as err:
            logger.warning(f"Не удалось загрузить cookies локально: {err}")
