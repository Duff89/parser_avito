from parser.cookies.base import CookiesProvider
from parser.cookies.external_api import ExternalApiCookiesProvider
from parser.cookies.own_cookies import OwnCookiesProvider

def build_cookies_provider(config) -> CookiesProvider | None:
    if config.use_bypass_api:
        return ExternalApiCookiesProvider(config.cookies_api_key)
    elif config.use_own_cookies:
        return OwnCookiesProvider()

    return None


