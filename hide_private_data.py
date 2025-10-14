import re
from loguru import logger


def mask_sensitive_data(config_str: str) -> str:
    """
    Маскирует приватные данные (прокси, токены, пароли и т.п.) в строке конфига.
    """
    masked = config_str

    # Прокси: user:pass@host:port → user:***@host:port
    masked = re.sub(
        r"([\w\-]+):([\w\-]+)@([\w\.\-]+):(\d+)",
        lambda m: f"{m.group(1)}:***@{m.group(3)}:{m.group(4)}",
        masked,
    )

    # Telegram токен
    masked = re.sub(
        r"(tg_token[\"']?\s*[:=]\s*[\"'])([^\"']+)([\"'])",
        lambda m: f"{m.group(1)}{m.group(2)[:5]}***{m.group(3)}",
        masked,
    )

    # Telegram chat_id
    masked = re.sub(
        r"(tg_chat_id[\"']?\s*[:=]\s*)(\[?[^\]]*\]?)",
        lambda m: f"{m.group(1)}['***']",
        masked,
    )

    # proxy_change_url → скрываем почти полностью, оставляем домен
    masked = re.sub(
        r"(proxy_change_url[\"']?\s*[:=]\s*[\"'])([^\"']+)([\"'])",
        lambda m: f"{m.group(1)}{_mask_url(m.group(2))}{m.group(3)}",
        masked,
    )

    # Общая маскировка чувствительных ключей (password, token, api_key, secret)
    masked = re.sub(
        r"((?:password|token|api_key|secret)[\"']?\s*[:=]\s*[\"'])([^\"']+)([\"'])",
        lambda m: f"{m.group(1)}***{m.group(3)}",
        masked,
        flags=re.IGNORECASE,
    )

    return masked


def _mask_url(url: str) -> str:
    """Маскирует URL, оставляя только домен для наглядности."""
    match = re.search(r"https?://([^/]+)/?", url)
    if match:
        domain = match.group(1)
        return f"https://{domain}/***"
    return "***"


def log_config(config, version: str):
    """
    Безопасно логирует конфигурацию, скрывая чувствительные данные.
    """
    safe_config_str = mask_sensitive_data(str(config))
    logger.info(f"Запуск AvitoParse v{version} с настройками:\n{safe_config_str}")
