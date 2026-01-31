import re
from models import Item


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return str(text).replace("\xa0", " ")


def escape_markdown_v2(text: str) -> str:
    text = normalize_text(text)
    return re.sub(r'([_\[\]()~`>#+\-=|{}.!])', r'\\\1', text)


def get_price(ad: Item) -> str:
    price = getattr(ad, "priceDetailed", None)

    if isinstance(price, dict):
        return normalize_text(price.get("value", ""))

    return normalize_text(
        getattr(price, "value", price)
    )


def get_first_image(ad: Item) -> str | None:
    if not getattr(ad, "images", None):
        return None

    def largest(img):
        return max(
            img.root.keys(),
            key=lambda k: int(k.split("x")[0]) * int(k.split("x")[1])
        )

    img = ad.images[0]
    return str(img.root[largest(img)])
