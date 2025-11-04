import json
import os
from datetime import datetime
from threading import Lock

from models import Item


class JSONHandler:
    """Сохраняет информацию в json"""

    def __init__(self, file_name):
        self._initialize(file_name=file_name)
        self.lock = Lock()

    def _initialize(self, file_name):
        self.file_name = file_name
        os.makedirs("result", exist_ok=True)
        if not os.path.exists(self.file_name):
            with open(self.file_name, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def append_data_from_page(self, ads: list[Item]):
        with self.lock:
            try:
                with open(self.file_name, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = []

            for ad in ads:
                data.append(ad.model_dump(mode='json'))

            with open(self.file_name, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)