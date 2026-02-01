from abc import ABC, abstractmethod
import requests


class Proxy(ABC):
    @abstractmethod
    def get_httpx_proxy(self) -> dict | None:
        pass

    @abstractmethod
    def handle_block(self):
        pass


class NoProxy(Proxy):
    def get_httpx_proxy(self):
        return None

    def handle_block(self):
        pass


class ServerProxy(Proxy):
    def __init__(self, proxy):
        self.proxy = proxy

    def get_httpx_proxy(self):
        return f"http://{self.proxy}"

    def handle_block(self):
        pass


class MobileProxy(Proxy):
    def __init__(self, url, change_ip_url):
        self.url = url
        self.change_ip_url = change_ip_url

    def get_httpx_proxy(self):
        return f"http://{self.url}"

    def handle_block(self):
        # делаем запрос на смену IP
        requests.get(self.change_ip_url, timeout=10)
