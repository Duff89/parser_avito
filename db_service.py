import sqlite3


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
                    id INTEGER,
                    price INTEGER
                )
                """
            )
            conn.commit()

    def add_record(self, record_id, price):
        """Добавляет новую запись в таблицу viewed."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO viewed (id, price) VALUES (?, ?)",
                (record_id, price),
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
