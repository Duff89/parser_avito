from loguru import logger

from models import Item
from .base import Notifier


class CompositeNotifier(Notifier):
    def __init__(self, notifiers: list[Notifier]):
        self.notifiers = notifiers

    def notify(self, ad: Item = None, message: str = None):
        for notifier in self.notifiers:
            try:
                notifier.notify(ad=ad, message=message)
            except Exception as e:
                logger.exception(
                    f"Ошибка {e} отправки уведомления через {notifier.__class__.__name__}"
                )


class NullNotifier(Notifier):
    def notify(self, ad: Item = None, message: str = None):
        pass
