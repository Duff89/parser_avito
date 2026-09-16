from unittest.mock import MagicMock

from dto import AvitoConfig
from models import Item
from parser_cls import AvitoParse


def test_extract_description_from_data_marker():
    html = """
    <html>
        <body>
            <div data-marker="item-description/text">
                <p>Игровой компьютер в идеальном состоянии.</p>
                <p>Характеристики: Ryzen 5 5600, RTX 4060, 32GB RAM.</p>
                <p>Любые проверки на месте.</p>
            </div>
        </body>
    </html>
    """
    desc = AvitoParse._extract_description(html)
    assert desc is not None
    assert "Игровой компьютер в идеальном состоянии." in desc
    assert "Ryzen 5 5600" in desc


def test_extract_description_from_schema_org():
    html = """
    <html>
        <body>
            <div itemprop="description">
                Продаю ноутбук в хорошем состоянии. Батарею держит 5 часов.
            </div>
        </body>
    </html>
    """
    desc = AvitoParse._extract_description(html)
    assert desc == "Продаю ноутбук в хорошем состоянии. Батарею держит 5 часов."


def test_extract_description_from_embedded_json():
    html = """
    <html>
        <head>
            <script type="mime/invalid" data-mfe-state="true">
                {"loaderData": {"data": {"item": {"description": "Полное описание товара из JSON loaderData"}}}}
            </script>
        </head>
        <body></body>
    </html>
    """
    desc = AvitoParse._extract_description(html)
    assert desc == "Полное описание товара из JSON loaderData"


def test_extract_description_returns_none_when_empty():
    html = "<html><body><div>Просто текст без маркеров</div></body></html>"
    desc = AvitoParse._extract_description(html)
    assert desc is None


def test_parse_description_method_updates_ad():
    config = AvitoConfig(urls=["https://www.avito.ru/test"], parse_description=True)
    parser = AvitoParse.__new__(AvitoParse)
    parser.config = config

    html = """
    <html><body>
        <div data-marker="item-description/text">
            Полный текст описания, который ранее обрезался кнопкой Читать полностью.
        </div>
    </body></html>
    """
    parser.fetch_data = MagicMock(return_value=html)

    ad = Item(id=1, urlPath="/item_123", description="Короткое описание...")
    result = parser.parse_description([ad])

    assert len(result) == 1
    assert result[0].description == "Полный текст описания, который ранее обрезался кнопкой Читать полностью."
