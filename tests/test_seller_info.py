from bs4 import BeautifulSoup
from models import Item, UserLogo
from parser_cls import AvitoParse


def test_extract_seller_slug_brands():
    ad = Item(id=1, userLogo=UserLogo(link="/brands/techstore"))
    slug = AvitoParse._extract_seller_slug(ad)
    assert slug == "techstore"


def test_extract_seller_slug_user():
    ad = Item(id=2, userLogo=UserLogo(link="/user/a1b2c3d4e5f/profile"))
    slug = AvitoParse._extract_seller_slug(ad)
    assert slug == "a1b2c3d4e5f"


def test_extract_seller_name_from_html_marker():
    html = """
    <html>
        <body>
            <div data-marker="seller-info/name">
                <a href="/user/123/profile">Алексей (частное лицо)</a>
            </div>
        </body>
    </html>
    """
    name = AvitoParse._extract_seller_name(html)
    assert name == "Алексей (частное лицо)"


def test_extract_seller_name_from_json():
    html = """
    <html>
        <head>
            <script type="mime/invalid" data-mfe-state="true">
                {"loaderData": {"data": {"item": {"seller": {"name": "ООО Мебель-Люкс"}}}}}
            </script>
        </head>
        <body></body>
    </html>
    """
    name = AvitoParse._extract_seller_name(html)
    assert name == "ООО Мебель-Люкс"
