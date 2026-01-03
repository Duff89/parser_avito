# 📚 Документация по внутренним функциям Avito Parser

Данный документ описывает внутренние модули и функции проекта для разработчиков, которые хотят расширять функциональность или интегрировать парсер в свои проекты.

---

## 📁 Структура проекта

```
├── AvitoParser.py         # Точка входа GUI-версии
├── parser_cls.py          # Основной класс парсера (CLI)
├── db_service.py          # Работа с SQLite базой данных
├── tg_sender.py           # Отправка уведомлений в Telegram
├── xlsx_service.py        # Экспорт в Excel
├── dto.py                 # Data Transfer Objects (датаклассы)
├── models.py              # Pydantic модели данных
├── load_config.py         # Загрузка/сохранение конфигурации
├── get_cookies.py         # Получение cookies через Playwright
├── common_data.py         # Общие константы (заголовки запросов)
├── hide_private_data.py   # Маскировка приватных данных в логах
├── playwright_setup.py    # Установка/проверка Playwright
├── lang.py                # Строки локализации для GUI
├── version.py             # Версия приложения
└── config.toml            # Файл конфигурации
```

---

## 🎯 Модуль `parser_cls.py` — Основной парсер

### Класс `AvitoParse`

Главный класс парсера, выполняющий сбор данных с Avito.

#### Инициализация

```python
from dto import AvitoConfig
from parser_cls import AvitoParse

config = AvitoConfig(
    urls=["https://www.avito.ru/moskva/telefony?s=104"],
    tg_token="YOUR_BOT_TOKEN",
    tg_chat_id=["123456789"],
    max_price=50000,
    min_price=1000,
)

parser = AvitoParse(config=config)
```

#### Параметры конструктора

| Параметр | Тип | Описание |
|----------|-----|----------|
| `config` | `AvitoConfig` | Объект конфигурации парсера |
| `stop_event` | `threading.Event` | Событие для остановки парсера (опционально) |

---

### Основные методы

#### `parse()`
Запускает основной цикл парсинга.

```python
parser = AvitoParse(config=config)
parser.parse()
```

---

#### `fetch_data(url: str, retries: int = 3, backoff_factor: int = 1) -> str | None`
Выполняет HTTP-запрос к странице с повторными попытками.

```python
html_code = parser.fetch_data(url="https://www.avito.ru/...")
```

| Параметр | Тип | Описание |
|----------|-----|----------|
| `url` | `str` | URL страницы для запроса |
| `retries` | `int` | Количество попыток (по умолчанию 3) |
| `backoff_factor` | `int` | Множитель задержки между попытками |

**Возвращает:** HTML-код страницы или `None` при неудаче.

---

#### `filter_ads(ads: list[Item]) -> list[Item]`
Применяет все фильтры к списку объявлений.

```python
filtered = parser.filter_ads(ads=ads_list)
```

Внутренне вызывает цепочку фильтров:
- `_filter_viewed` — убирает уже просмотренные
- `_filter_by_price_range` — фильтр по цене
- `_filter_by_black_keywords` — исключает стоп-слова
- `_filter_by_white_keyword` — только с нужными словами
- `_filter_by_address` — фильтр по адресу
- `_filter_by_seller` — исключает продавцов из чёрного списка
- `_filter_by_recent_time` — только свежие объявления
- `_filter_by_reserve` — исключает зарезервированные
- `_filter_by_promotion` — исключает продвигаемые

---

#### `find_json_on_page(html_code: str, data_type: str = "mime") -> dict`
Извлекает JSON-данные со страницы Avito.

```python
data = AvitoParse.find_json_on_page(html_code=html)
catalog = data.get("data", {}).get("catalog", {})
```

---

#### `change_ip() -> bool`
Меняет IP-адрес через ссылку смены прокси.

```python
success = parser.change_ip()
```

---

#### `get_cookies(max_retries: int = 1, delay: float = 2.0) -> dict | None`
Получает cookies через headless-браузер.

```python
cookies = parser.get_cookies(max_retries=3)
```

---

#### `save_cookies()` / `load_cookies()`
Сохранение и загрузка cookies в/из `cookies.json`.

```python
parser.save_cookies()  # Сохранить текущие cookies
parser.load_cookies()  # Загрузить cookies из файла
```

---

#### `parse_views(ads: list[Item]) -> list[Item]`
Парсит количество просмотров для каждого объявления (требует дополнительных запросов).

```python
ads_with_views = parser.parse_views(ads=ads_list)
```

---

#### `get_next_page_url(url: str) -> str`
Генерирует URL следующей страницы.

```python
next_url = parser.get_next_page_url(url="https://avito.ru/moskva?p=1")
# Результат: "https://avito.ru/moskva?p=2"
```

---

### Приватные методы фильтрации

| Метод | Описание |
|-------|----------|
| `_filter_by_price_range(ads)` | Фильтрует по диапазону цен |
| `_filter_by_black_keywords(ads)` | Исключает объявления со стоп-словами |
| `_filter_by_white_keyword(ads)` | Оставляет только с ключевыми словами |
| `_filter_by_address(ads)` | Фильтрует по адресу/геолокации |
| `_filter_viewed(ads)` | Убирает уже просмотренные объявления |
| `_filter_by_seller(ads)` | Исключает продавцов из чёрного списка |
| `_filter_by_recent_time(ads)` | Оставляет только свежие объявления |
| `_filter_by_reserve(ads)` | Исключает зарезервированные |
| `_filter_by_promotion(ads)` | Исключает продвигаемые объявления |

---

### Вспомогательные статические методы

#### `_is_phrase_in_ads(ad: Item, phrases: list) -> bool`
Проверяет, содержит ли объявление одну из фраз.

```python
found = AvitoParse._is_phrase_in_ads(
    ad=item,
    phrases=["iphone", "samsung"]
)
```

---

#### `_is_recent(timestamp_ms: int, max_age_seconds: int) -> bool`
Проверяет, является ли объявление достаточно свежим.

```python
is_fresh = AvitoParse._is_recent(
    timestamp_ms=1704067200000,
    max_age_seconds=3600  # 1 час
)
```

---

#### `_extract_views(html: str) -> tuple[int | None, int | None]`
Извлекает количество просмотров (всего, сегодня) со страницы объявления.

```python
total, today = AvitoParse._extract_views(html=html_code)
```

---

## 🗄️ Модуль `db_service.py` — Работа с БД

### Класс `SQLiteDBHandler`

Singleton-класс для работы с SQLite базой данных.

#### Инициализация

```python
from db_service import SQLiteDBHandler

db = SQLiteDBHandler(db_name="my_database.db")
```

---

### Методы

#### `add_record(ad: Item)`
Добавляет одну запись в таблицу `viewed`.

```python
db.add_record(ad=item)
```

---

#### `add_record_from_page(ads: list[Item])`
Добавляет несколько записей за один раз.

```python
db.add_record_from_page(ads=items_list)
```

---

#### `record_exists(record_id: int, price: int) -> bool`
Проверяет, существует ли запись с указанным ID и ценой.

```python
exists = db.record_exists(record_id=12345678, price=15000)
```

---

## 📬 Модуль `tg_sender.py` — Telegram уведомления

### Класс `SendAdToTg`

Отправляет объявления в Telegram.

#### Инициализация

```python
from tg_sender import SendAdToTg

tg = SendAdToTg(
    bot_token="123456:ABC-DEF...",
    chat_id=["123456789", "987654321"],
    max_retries=5,
    retry_delay=5
)
```

| Параметр | Тип | Описание |
|----------|-----|----------|
| `bot_token` | `str` | Токен Telegram бота |
| `chat_id` | `list[str]` | Список chat_id получателей |
| `max_retries` | `int` | Максимум попыток отправки |
| `retry_delay` | `int` | Задержка между попытками (сек) |

---

### Методы

#### `send_to_tg(ad: Item = None, msg: str = None)`
Отправляет объявление или текстовое сообщение всем получателям.

```python
# Отправить объявление
tg.send_to_tg(ad=item)

# Отправить текст
tg.send_to_tg(msg="Парсинг завершён!")
```

---

#### `escape_markdown(text: str) -> str`
Экранирует спецсимволы для MarkdownV2.

```python
safe_text = SendAdToTg.escape_markdown("Цена: 1.500 ₽")
```

---

#### `format_ad(ad: Item) -> str`
Форматирует объявление в Markdown для Telegram.

```python
message = SendAdToTg.format_ad(ad=item)
```

---

#### `get_first_image(ad: Item) -> str | None`
Возвращает URL первого изображения максимального размера.

```python
image_url = SendAdToTg.get_first_image(ad=item)
```

---

## 📊 Модуль `xlsx_service.py` — Экспорт в Excel

### Класс `XLSXHandler`

Сохраняет объявления в Excel-файл.

#### Инициализация

```python
from xlsx_service import XLSXHandler

xlsx = XLSXHandler(file_name="result/output.xlsx")
```

---

### Методы

#### `append_data_from_page(ads: list[Item])`
Добавляет список объявлений в Excel-файл.

```python
xlsx.append_data_from_page(ads=items_list)
```

**Колонки в файле:**
- Название
- Цена
- URL
- Описание
- Дата публикации
- Продавец
- Адрес
- Адрес пользователя
- Координаты
- Изображения
- Поднято
- Просмотры (всего)
- Просмотры (сегодня)

---

#### `get_ad_time(ad: Item) -> datetime`
Преобразует timestamp объявления в datetime.

```python
pub_time = XLSXHandler.get_ad_time(ad=item)
```

---

#### `get_item_coords(ad: Item) -> str`
Возвращает координаты в формате `"lat;lng"`.

```python
coords = XLSXHandler.get_item_coords(ad=item)  # "55.7558;37.6173"
```

---

#### `get_item_address_user(ad: Item) -> str`
Возвращает пользовательский адрес.

```python
address = XLSXHandler.get_item_address_user(ad=item)
```

---

## ⚙️ Модуль `dto.py` — Data Transfer Objects

### Класс `AvitoConfig`

Датакласс с настройками парсера.

```python
from dto import AvitoConfig

config = AvitoConfig(
    urls=["https://www.avito.ru/moskva/telefony"],
    proxy_string="user:pass@proxy.com:8080",
    proxy_change_url="https://proxy.com/change_ip",
    keys_word_white_list=["iphone", "samsung"],
    keys_word_black_list=["разбит", "сломан"],
    seller_black_list=["seller123"],
    count=3,
    tg_token="123456:ABC...",
    tg_chat_id=["123456789"],
    max_price=100000,
    min_price=5000,
    geo="Москва",
    max_age=3600,
    pause_general=60,
    pause_between_links=5,
    max_count_of_retry=5,
    ignore_reserv=True,
    ignore_promotion=False,
    one_time_start=False,
    one_file_for_link=False,
    parse_views=False,
    save_xlsx=True,
    use_webdriver=True,
)
```

| Поле | Тип | По умолчанию | Описание |
|------|-----|--------------|----------|
| `urls` | `list[str]` | — | Список URL для парсинга |
| `proxy_string` | `str \| None` | `None` | Строка прокси |
| `proxy_change_url` | `str \| None` | `None` | URL для смены IP |
| `keys_word_white_list` | `list[str]` | `[]` | Обязательные слова |
| `keys_word_black_list` | `list[str]` | `[]` | Стоп-слова |
| `seller_black_list` | `list[str]` | `[]` | Чёрный список продавцов |
| `count` | `int` | `1` | Количество страниц |
| `tg_token` | `str \| None` | `None` | Токен Telegram бота |
| `tg_chat_id` | `list[str]` | `None` | Список chat_id |
| `max_price` | `int` | `999999999` | Максимальная цена |
| `min_price` | `int` | `0` | Минимальная цена |
| `geo` | `str \| None` | `None` | Фильтр по геолокации |
| `max_age` | `int` | `86400` | Макс. возраст объявления (сек) |
| `pause_general` | `int` | `60` | Пауза между циклами (сек) |
| `pause_between_links` | `int` | `5` | Пауза между ссылками (сек) |
| `max_count_of_retry` | `int` | `5` | Макс. попыток запроса |
| `ignore_reserv` | `bool` | `True` | Игнорировать зарезервированные |
| `ignore_promotion` | `bool` | `False` | Игнорировать продвигаемые |
| `one_time_start` | `bool` | `False` | Однократный запуск |
| `one_file_for_link` | `bool` | `False` | Отдельный файл для каждой ссылки |
| `parse_views` | `bool` | `False` | Парсить просмотры |
| `save_xlsx` | `bool` | `True` | Сохранять в Excel |
| `use_webdriver` | `bool` | `True` | Использовать браузер для cookies |

---

### Класс `Proxy`

```python
from dto import Proxy

proxy = Proxy(
    proxy_string="user:pass@proxy.com:8080",
    change_ip_link="https://proxy.com/change"
)
```

---

## 📄 Модуль `load_config.py` — Конфигурация

### `load_avito_config(path: str = "config.toml") -> AvitoConfig`
Загружает конфигурацию из TOML-файла.

```python
from load_config import load_avito_config

config = load_avito_config("config.toml")
```

---

### `save_avito_config(config: dict)`
Сохраняет конфигурацию в `config.toml`.

```python
from load_config import save_avito_config

save_avito_config({"avito": {"urls": ["..."], "max_price": 50000}})
```

---

## 🔐 Модуль `hide_private_data.py` — Маскировка данных

### `mask_sensitive_data(config_str: str) -> str`
Маскирует приватные данные (токены, пароли, прокси) в строке.

```python
from hide_private_data import mask_sensitive_data

safe = mask_sensitive_data("token='123456:ABC...'")
# Результат: "token='12345***'"
```

---

### `log_config(config: AvitoConfig, version: str)`
Безопасно логирует конфигурацию.

```python
from hide_private_data import log_config

log_config(config=config, version="1.0.0")
```

---

## 🎭 Модуль `get_cookies.py` — Получение cookies

### Класс `PlaywrightClient`

Клиент для получения cookies через headless-браузер.

```python
from get_cookies import get_cookies
from dto import Proxy
import asyncio

proxy = Proxy(
    proxy_string="user:pass@proxy.com:8080",
    change_ip_link="https://..."
)

cookies, user_agent = asyncio.run(
    get_cookies(proxy=proxy, headless=True)
)
```

---

### `get_cookies(proxy: Proxy = None, headless: bool = True, stop_event = None) -> tuple[dict, str]`
Асинхронная функция получения cookies.

**Возвращает:** Кортеж `(cookies_dict, user_agent_string)`

---

## 🎭 Модуль `playwright_setup.py` — Установка Playwright

### `ensure_playwright_installed(browser: str = "chromium")`
Проверяет и устанавливает браузер Playwright при необходимости.

```python
from playwright_setup import ensure_playwright_installed

ensure_playwright_installed("chromium")
```

---

## 📦 Модуль `models.py` — Pydantic модели

### Класс `Item`

Модель объявления Avito.

```python
from models import Item

# Основные поля:
item.id              # ID объявления
item.title           # Заголовок
item.description     # Описание
item.urlPath         # Путь URL
item.priceDetailed   # Детали цены (PriceDetailed)
item.location        # Локация (Location)
item.images          # Список изображений
item.sortTimeStamp   # Timestamp публикации
item.sellerId        # ID продавца
item.isReserved      # Зарезервировано
item.isPromotion     # Продвигается
item.total_views     # Всего просмотров
item.today_views     # Просмотров сегодня
item.coords          # Координаты {"lat": ..., "lng": ...}
item.geo             # Геоданные (Geo)
```

---

### Класс `ItemsResponse`

Ответ API со списком объявлений.

```python
from models import ItemsResponse

response = ItemsResponse(**catalog_data)
items = response.items  # list[Item]
```

---

## 🚀 Примеры использования

### Простой парсинг с сохранением в Excel

```python
from dto import AvitoConfig
from parser_cls import AvitoParse

config = AvitoConfig(
    urls=["https://www.avito.ru/moskva/telefony?s=104"],
    count=2,
    save_xlsx=True,
    one_time_start=True,
)

parser = AvitoParse(config=config)
parser.parse()
```

---

### Парсинг с уведомлениями в Telegram

```python
from dto import AvitoConfig
from parser_cls import AvitoParse

config = AvitoConfig(
    urls=["https://www.avito.ru/moskva/telefony?s=104"],
    tg_token="123456:ABC-DEF...",
    tg_chat_id=["123456789"],
    max_price=30000,
    keys_word_white_list=["iphone 15"],
)

parser = AvitoParse(config=config)
parser.parse()
```

---

### Использование только модуля Telegram

```python
from tg_sender import SendAdToTg
from models import Item

tg = SendAdToTg(
    bot_token="123456:ABC...",
    chat_id=["123456789"]
)

# Отправить текстовое сообщение
tg.send_to_tg(msg="Привет из парсера\\!")
```

---

### Работа с базой данных напрямую

```python
from db_service import SQLiteDBHandler

db = SQLiteDBHandler("my_ads.db")

# Проверить, видели ли объявление
if not db.record_exists(record_id=12345, price=15000):
    print("Новое объявление!")
```

---

### Экспорт в Excel напрямую

```python
from xlsx_service import XLSXHandler
from models import Item

xlsx = XLSXHandler("result/my_export.xlsx")

# После получения списка Item
xlsx.append_data_from_page(ads=items_list)
```

---

## 📝 Логирование

Проект использует `loguru` для логирования. Логи сохраняются в `logs/app.log`.

```python
from loguru import logger

logger.info("Информационное сообщение")
logger.warning("Предупреждение")
logger.error("Ошибка")
logger.debug("Отладочная информация")
```

---

## ⚠️ Обработка ошибок

Все основные функции обрабатывают исключения и логируют их. При критических ошибках парсер автоматически перезапускается через 30 секунд.

```python
try:
    parser.parse()
except Exception as err:
    logger.error(f"Ошибка: {err}")
```

---

## 🔧 Расширение функциональности

### Добавление нового фильтра

1. Создайте метод в классе `AvitoParse`:

```python
def _filter_by_custom(self, ads: list[Item]) -> list[Item]:
    return [ad for ad in ads if your_condition(ad)]
```

2. Добавьте его в список фильтров в методе `filter_ads()`:

```python
filters = [
    # ...existing filters...
    self._filter_by_custom,
]
```

---

### Добавление нового способа уведомлений

Создайте класс по аналогии с `SendAdToTg` и используйте его в `AvitoParse`:

```python
class SendAdToEmail:
    def __init__(self, email: str):
        self.email = email
    
    def send(self, ad: Item):
        # Логика отправки
        pass
```

