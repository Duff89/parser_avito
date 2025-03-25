import os
from openpyxl import Workbook, load_workbook
from threading import Lock


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
            "Название", "Цена", "URL", "Описание", "Просмотров", "Дата публикации", "Продавец", "Адрес", "Ссылка на продавца"
        ])
        workbook.save(self.file_name)

    def append_data(self, data):
        workbook = load_workbook(self.file_name)
        sheet = workbook.active
        row = [
            data.get("name", '-'),
            data.get("price", '-'),
            data.get("url", '-'),
            data.get("description", '-'),
            data.get("views", '-'),
            data.get("date_public", '-'),
            data.get("seller_name", 'no'),
            data.get("geo", '-'),
            data.get("seller_link", '-')
        ]
        sheet.append(row)
        workbook.save(self.file_name)

