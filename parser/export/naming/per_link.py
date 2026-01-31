import hashlib
from urllib.parse import urlparse

from parser.export.naming.base import ResultNamingStrategy

class PerLinkNamingStrategy(ResultNamingStrategy):
    def __init__(self, base_dir: str = "result"):
        self.base_dir = base_dir

    def get_storage_key(self, *, url: str | None = None) -> str:
        if not url:
            raise ValueError("URL required for per-link naming")

        parsed = urlparse(url)
        safe = hashlib.md5(url.encode()).hexdigest()[:10]

        return f"{self.base_dir}/{parsed.netloc}_{safe}.xlsx"

