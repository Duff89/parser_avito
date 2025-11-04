from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Proxy:
    proxy_string: str
    change_ip_link: str


@dataclass
class ProxySplit:
    ip_port: str
    login: str
    password: str
    change_ip_link: str


@dataclass
class AvitoConfig:
    urls: List[str]
    proxy_string: Optional[str] = None
    proxy_change_url: Optional[str] = None
    keys_word_white_list: List[str] = field(default_factory=list)
    keys_word_black_list: List[str] = field(default_factory=list)
    seller_black_list: List[str] = field(default_factory=list)
    count: int = 1
    tg_token: Optional[str] = None
    tg_chat_id: List[str] = None
    max_price: int = 999_999_999
    min_price: int = 0
    geo: Optional[str] = None
    max_age: int = 24 * 60 * 60
    debug_mode: int = 0
    pause_general: int = 60
    pause_between_links: int = 5
    max_count_of_retry: int = 5
    ignore_reserv: bool = True
    ignore_promotion: bool = False
    one_time_start: bool = False
    one_file_for_link: bool = False
    parse_views: bool = False
    save_xlsx: bool = True
    save_json: bool = False

