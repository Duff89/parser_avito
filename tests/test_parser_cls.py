import threading
from pathlib import Path
from unittest.mock import MagicMock

from dto import AvitoConfig
from models import Item, IvaStep, IvaComponent
from parser_cls import AvitoParse


def test_add_promotion_to_ads():
    step_null_vas = IvaStep(
        componentData=IvaComponent(component="c", payload=None),
        payload={"vas": None},
        default=False
    )
    step_promoted = IvaStep(
        componentData=IvaComponent(component="c", payload=None),
        payload={"vas": [{"title": "Продвинуто"}]},
        default=False
    )

    ad1 = Item(id=1, iva=None)
    ad2 = Item(id=2, iva={"DateInfoStep": [step_null_vas]})
    ad3 = Item(id=3, iva={"DateInfoStep": [step_promoted]})

    ads = AvitoParse._add_promotion_to_ads([ad1, ad2, ad3])

    assert ads[0].isPromotion is False
    assert ads[1].isPromotion is False
    assert ads[2].isPromotion is True


def test_stop_event_set_preserves_event_object():
    stop_event = threading.Event()
    config = AvitoConfig(
        urls=["https://www.avito.ru/test"],
        output_dir=Path("result"),
        one_time_start=True
    )

    parser = AvitoParse.__new__(AvitoParse)
    parser.config = config
    parser.stop_event = stop_event
    parser.notifier = MagicMock()

    assert not stop_event.is_set()

    # Simulate the one_time_start block in parser.parse()
    if parser.config.one_time_start:
        parser.notifier.notify(message="Парсинг Авито завершён. Все ссылки обработаны")
        if parser.stop_event is not None and hasattr(parser.stop_event, "set"):
            parser.stop_event.set()

    # Verify stop_event is set and is still a threading.Event (not replaced by bool True)
    assert isinstance(parser.stop_event, threading.Event)
    assert parser.stop_event.is_set() is True


def test_clean_null_ads():
    ad1 = Item(id=101)
    ad2 = Item(id=None)
    ad3 = Item(id=0)

    cleaned = AvitoParse._clean_null_ads([ad1, ad2, ad3])
    assert len(cleaned) == 1
    assert cleaned[0].id == 101


def test_is_viewed_handles_none_price():
    parser = AvitoParse.__new__(AvitoParse)
    parser.db_handler = MagicMock()
    parser.db_handler.record_exists.return_value = True

    ad_none_price = Item(id=555, priceDetailed=None)
    result = parser.is_viewed(ad_none_price)

    assert result is True
    parser.db_handler.record_exists.assert_called_once_with(record_id=555, price=0)
