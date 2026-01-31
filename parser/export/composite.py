from loguru import logger

from parser.export.base import ResultStorage
from models import Item

class CompositeResultStorage(ResultStorage):
    """
    Прокси-хранилище.
    Делегирует сохранение сразу в несколько ResultStorage.
    """

    def __init__(self, storages: list[ResultStorage]):
        if not storages:
            raise ValueError("CompositeResultStorage requires at least one storage")

        self.storages = storages

    def save(self, ads: list[Item]) -> None:
        if not ads:
            return

        for storage in self.storages:
            try:
                storage.save(ads)
            except Exception as e:
                logger.exception(
                    f"Failed to save results using {storage.__class__.__name__}: {e}"
                )
