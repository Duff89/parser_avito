import os
from datetime import datetime
from openpyxl import Workbook, load_workbook
from threading import Lock
from datetime import datetime
from tzlocal import get_localzone
from models import Item


class XLSXHandler:
    """Сохраняет информацию в xlsx"""
    _instance = None
    _lock = Lock()

    def __new__(cls, file_name):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(XLSXHandler, cls).__new__(cls)
                cls._instance._initialize(file_name)
        return cls._instance

    def _initialize(self, file_name):
        self.file_name = file_name
        os.makedirs("result", exist_ok=True)
        if not os.path.exists(self.file_name):
            self._create_file()

    def _create_file(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Data"
        sheet.append([
            "Название",
            "Цена",
            "URL",
            "Описание",
            "Дата публикации",
            "Продавец",
            "Адрес",
        ])
        workbook.save(self.file_name)

    def append_data(self, ad: Item):
        workbook = load_workbook(self.file_name)
        sheet = workbook.active

        timestamp_sec = ad.sortTimeStamp / 1000

        utc_time = datetime.utcfromtimestamp(timestamp_sec)

        local_time = utc_time.astimezone(get_localzone())

        row = [
            ad.title,
            ad.priceDetailed.value,
            f"https://www.avito.ru/{ad.urlPath}",
            ad.description,
            local_time.strftime('%Y-%m-%d %H:%M:%S'),
            ad.sellerId if ad.sellerId else "",
            ad.location.name if ad.location else "",
        ]
        sheet.append(row)
        workbook.save(self.file_name)

