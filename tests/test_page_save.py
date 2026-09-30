import threading
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from dto import AvitoConfig
from models import Item
from parser_cls import AvitoParse


def _make_parser(count=2):
    config = AvitoConfig(
        urls=["https://www.avito.ru/all"],
        count=count,
        output_dir=Path("result"),
        save_xlsx=True,
        one_file_for_link=True,
        pause_between_links=0,
    )
    parser = AvitoParse.__new__(AvitoParse)
    parser.config = config
    parser.stop_event = threading.Event()
    parser.good_request_count = 0
    parser.bad_request_count = 0
    parser.url_converter = MagicMock()
    parser.url_converter.convert.return_value = "https://m.avito.ru/api/9/items"
    parser.db_handler = MagicMock()
    parser.notifier = MagicMock()
    parser.ads_filter = MagicMock()
    parser.filter_ads = lambda ads: ads
    parser.parse_views = lambda ads: ads
    parser.parse_phone = lambda ads: ads
    parser._add_seller_to_ads = lambda ads: ads
    parser._add_promotion_to_ads = lambda ads: ads
    parser._clean_null_ads = lambda ads: ads
    parser._extract_api_catalog = lambda data: data
    return parser


def test_parse_saves_per_page_before_subsequent_crash():
    parser = _make_parser(count=2)
    mock_storage = MagicMock()
    item_p1 = Item(id=101, title="Item Page 1")

    def mock_fetch_api_data(api_url, page):
        if page == 1:
            return {"items": [item_p1]}
        raise RuntimeError("Network error or 429 on page 2")

    parser.fetch_api_data = mock_fetch_api_data

    with patch("parser_cls.build_result_storage", return_value=mock_storage):
        with pytest.raises(RuntimeError, match="Network error or 429"):
            parser.parse()

    # Page 1 must have been saved to result_storage and marked in DB
    mock_storage.save.assert_called_once_with([item_p1])
    parser.db_handler.add_record_from_page.assert_called_once_with(ads=[item_p1])


def test_storage_save_called_before_marking_viewed():
    parser = _make_parser(count=1)
    mock_storage = MagicMock()
    item = Item(id=202, title="Item 202")
    parser.fetch_api_data = lambda api_url, page: {"items": [item]}

    call_order = []
    mock_storage.save.side_effect = lambda ads: call_order.append("storage_save")
    parser.db_handler.add_record_from_page.side_effect = lambda ads: call_order.append(
        "db_save"
    )

    with patch("parser_cls.build_result_storage", return_value=mock_storage):
        parser.parse()

    assert call_order == ["storage_save", "db_save"]


def test_storage_save_failure_prevents_marking_viewed():
    parser = _make_parser(count=1)
    mock_storage = MagicMock()
    item = Item(id=303, title="Item 303")
    parser.fetch_api_data = lambda api_url, page: {"items": [item]}
    mock_storage.save.side_effect = PermissionError("Excel file is locked")

    with patch("parser_cls.build_result_storage", return_value=mock_storage):
        with pytest.raises(PermissionError, match="Excel file is locked"):
            parser.parse()

    # DB handler must NOT have marked the item as viewed if storage save failed
    parser.db_handler.add_record_from_page.assert_not_called()


def test_stop_event_during_pagination_preserves_previous_pages():
    parser = _make_parser(count=3)
    mock_storage = MagicMock()
    item_p1 = Item(id=401, title="Item Page 1")
    item_p2 = Item(id=402, title="Item Page 2")

    def mock_fetch_api_data(api_url, page):
        if page == 1:
            return {"items": [item_p1]}
        if page == 2:
            return {"items": [item_p2]}
        # Page 3: stop requested
        parser.stop_event.set()
        return {"items": []}

    parser.fetch_api_data = mock_fetch_api_data

    with patch("parser_cls.build_result_storage", return_value=mock_storage):
        parser.parse()

    assert mock_storage.save.call_count == 2
    assert mock_storage.save.call_args_list == [
        call([item_p1]),
        call([item_p2]),
    ]
    assert parser.db_handler.add_record_from_page.call_count == 2
    assert parser.db_handler.add_record_from_page.call_args_list == [
        call(ads=[item_p1]),
        call(ads=[item_p2]),
    ]
