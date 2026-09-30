import sqlite3
from unittest.mock import MagicMock
from models import Item, PriceDetailed
from db_service import SQLiteDBHandler
from integrations.notifications.base import Notifier


class DummyNotifier(Notifier):
    def notify(self, ad: Item = None, message: str = None):
        return self.format(ad) if ad else message


def test_db_get_record_price(tmp_path):
    db_file = str(tmp_path / "test.db")
    db = SQLiteDBHandler.__new__(SQLiteDBHandler)
    db.db_name = db_file
    db._create_table()

    # Initially None
    assert db.get_record_price(100) is None

    # Insert record with price 1000
    item = Item(id=100, priceDetailed=PriceDetailed(
        enabled=True, fullString="1 000 ₽", hasValue=True, postfix="₽",
        string="1 000 ₽", title={}, titleDative="", value=1000,
        wasLowered=False, exponent=""
    ))
    db.add_record_from_page([item])

    assert db.get_record_price(100) == 1000

    # Update with new price 800
    item_updated = Item(id=100, priceDetailed=PriceDetailed(
        enabled=True, fullString="800 ₽", hasValue=True, postfix="₽",
        string="800 ₽", title={}, titleDative="", value=800,
        wasLowered=True, exponent=""
    ))
    db.add_record_from_page([item_updated])

    assert db.get_record_price(100) == 800


def test_price_change_notification_format():
    notifier = DummyNotifier()

    # Ad with price dropped
    ad_lowered = Item(
        id=123,
        title="Тестовый товар",
        priceDetailed=PriceDetailed(
            enabled=True, fullString="8 500 ₽", hasValue=True, postfix="₽",
            string="8 500 ₽", title={}, titleDative="", value=8500,
            wasLowered=True, exponent=""
        ),
        old_price=10000
    )

    formatted = notifier.format(ad_lowered)
    assert "8 500" in formatted
    assert "10 000" in formatted
    assert "📉" in formatted or "Цена" in formatted

    # Ad with price raised
    ad_raised = Item(
        id=124,
        title="Тестовый товар 2",
        priceDetailed=PriceDetailed(
            enabled=True, fullString="12 000 ₽", hasValue=True, postfix="₽",
            string="12 000 ₽", title={}, titleDative="", value=12000,
            wasLowered=False, exponent=""
        ),
        old_price=10000
    )

    formatted_raised = notifier.format(ad_raised)
    assert "12 000" in formatted_raised
    assert "10 000" in formatted_raised
    assert "📈" in formatted_raised or "Цена" in formatted_raised


def test_new_ad_notification_format_without_old_price():
    notifier = DummyNotifier()

    ad_new = Item(
        id=125,
        title="Новый товар",
        priceDetailed=PriceDetailed(
            enabled=True, fullString="5 000 ₽", hasValue=True, postfix="₽",
            string="5 000 ₽", title={}, titleDative="", value=5000,
            wasLowered=False, exponent=""
        ),
        old_price=None
    )

    formatted_new = notifier.format(ad_new)
    assert "5000" in formatted_new
    assert "➔" not in formatted_new


def test_vk_notification_price_change():
    from integrations.notifications.vk import VKNotifier
    ad_lowered = Item(
        id=126,
        title="Ноутбук",
        priceDetailed=PriceDetailed(
            enabled=True, fullString="45 000 ₽", hasValue=True, postfix="₽",
            string="45 000 ₽", title={}, titleDative="", value=45000,
            wasLowered=True, exponent=""
        ),
        old_price=50000,
        sellerName="Иван Продавец"
    )

    formatted = VKNotifier.format_ad(ad_lowered)
    assert "45 000" in formatted
    assert "50 000" in formatted
    assert "📉" in formatted
    assert "Иван Продавец" in formatted
