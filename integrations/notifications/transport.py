"""
Клиент для уведомлений, для парсера есть свой отдельный
"""
import time
from typing import Callable

import requests
from loguru import logger

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


def send_with_retries(
    send_fn: Callable[[], requests.Response],
    *,
    retries: int = 5,
    delay: float = 2.0,
    backoff: float = 1.5,
):
    """
    Универсальный retry для отправки уведомлений
    """

    for attempt in range(1, retries + 1):
        try:
            response = send_fn()

            if response.status_code in RETRY_STATUS_CODES:
                raise requests.HTTPError(
                    f"Retryable status {response.status_code}",
                    response=response,
                )

            response.raise_for_status()
            return response

        except requests.RequestException as e:
            logger.warning(
                f"[notify retry] attempt {attempt}/{retries}: {e}"
            )

            if attempt >= retries:
                logger.error("[notify retry] retries exhausted")
                raise

            sleep_time = delay * (backoff ** (attempt - 1))
            time.sleep(sleep_time)
