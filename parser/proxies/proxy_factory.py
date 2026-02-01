from loguru import logger

from dto import AvitoConfig
from .proxy import NoProxy, ServerProxy, MobileProxy, Proxy


def build_proxy(config: AvitoConfig) -> Proxy:
    """
    Определяет тип прокси
    """
    if config.proxy_change_url and not config.proxy_string:
        raise ValueError("proxy_change_url указан без proxy_string")

    if config.proxy_string and config.proxy_change_url:
        logger.info("Прокси определен как мобильный")
        return MobileProxy(config.proxy_string, config.proxy_change_url)

    if config.proxy_string:
        logger.info("Прокси определен как серверный")
        return ServerProxy(config.proxy_string)

    return NoProxy()

