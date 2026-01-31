from parser.cookies.base import CookiesProvider
from parser.cookies.external_api import ExternalApiCookiesProvider


def build_cookies_provider(config) -> CookiesProvider | None:
    if not config.cookies_api_key:
        return None

    return ExternalApiCookiesProvider(config.cookies_api_key)
