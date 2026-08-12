from parser.cookies.base import CookiesProvider
from parser.cookies.external_api import ExternalApiCookiesProvider
from parser.cookies.own_cookies import OwnCookiesProvider

def build_cookies_provider(config, proxy=None) -> CookiesProvider | None:
    if config.use_bypass_api:
        return ExternalApiCookiesProvider(config, proxy=proxy)
    elif config.use_own_cookies:
        return OwnCookiesProvider()

    return None


