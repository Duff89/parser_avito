import sqlite3

from models import Item


class SQLiteDBHandler:
    """Работа с БД sqlite"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SQLiteDBHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_name="database.db"):
        if not hasattr(self, "_initialized"):
            self.db_name = db_name
            self._create_table()
            self._initialized = True

    def _create_table(self):
        """Создает таблицу viewed, если она не существует."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS viewed (
                    id INTEGER PRIMARY KEY,
                    price INTEGER
                )
                """
            )
            try:
                cursor.execute(
                    """
                    DELETE FROM viewed WHERE rowid NOT IN (
                        SELECT max(rowid) FROM viewed GROUP BY id
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_viewed_id ON viewed (id)
                    """
                )
            except Exception:
                pass
            conn.commit()

    def get_record_price(self, record_id: int) -> int | None:
        """Возвращает сохраненную цену для объявления или None, если запись отсутствует."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT price FROM viewed WHERE id = ?",
                (record_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def add_record(self, ad: Item):
        """Добавляет новую запись в таблицу viewed."""
        price = (
            ad.priceDetailed.value
            if (ad.priceDetailed and getattr(ad.priceDetailed, "value", None) is not None)
            else 0
        )
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO viewed (id, price) VALUES (?, ?)",
                (ad.id, price),
            )
            conn.commit()

    def add_record_from_page(self, ads: list[Item]):
        """Добавляет несколько записей в таблицу viewed."""
        records = [
            (
                ad.id,
                ad.priceDetailed.value
                if (ad.priceDetailed and getattr(ad.priceDetailed, "value", None) is not None)
                else 0,
            )
            for ad in ads
        ]

        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT OR REPLACE INTO viewed (id, price)
                VALUES (?, ?)
                """,
                records,
            )
            conn.commit()

    def record_exists(self, record_id, price):
        """Проверяет, существует ли запись с заданными id и price."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM viewed WHERE id = ? AND price = ?",
                (record_id, price),
            )
            return cursor.fetchone() is not None
