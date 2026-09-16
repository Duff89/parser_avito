from datetime import datetime, timezone, timedelta
from pathlib import Path

from dto import AvitoConfig
from filters.ads_filter import AdsFilter
from models import Item, Geo, PriceDetailed, IvaStep, IvaComponent


def _make_config(**kwargs) -> AvitoConfig:
    defaults = {
        "urls": ["https://www.avito.ru/test"],
        "output_dir": Path("result"),
    }
    defaults.update(kwargs)
    return AvitoConfig(**defaults)


def test_filter_by_address_matches():
    config = _make_config(geo="Москва")
    filter_service = AdsFilter(config)

    ad_moscow = Item(
        id=1,
        geo=Geo(geoReferences=[], formattedAddress="г. Москва, ул. Тверская, д. 1")
    )
    ad_spb = Item(
        id=2,
        geo=Geo(geoReferences=[], formattedAddress="г. Санкт-Петербург, Невский пр-т")
    )

    result = filter_service._filter_by_address([ad_moscow, ad_spb])
    assert len(result) == 1
    assert result[0].id == 1


def test_filter_by_address_case_insensitive_and_whitespace():
    config = _make_config(geo="  мОсКвА  ")
    filter_service = AdsFilter(config)

    ad = Item(
        id=1,
        geo=Geo(geoReferences=[], formattedAddress="Россия, Москва, Варшавское шоссе")
    )
    result = filter_service._filter_by_address([ad])
    assert len(result) == 1


def test_filter_by_address_handles_none_geo():
    config = _make_config(geo="Москва")
    filter_service = AdsFilter(config)

    ad_none_geo = Item(id=1, geo=None)
    ad_with_geo = Item(
        id=2,
        geo=Geo(geoReferences=[], formattedAddress="Москва, Арбат")
    )

    result = filter_service._filter_by_address([ad_none_geo, ad_with_geo])
    assert len(result) == 1
    assert result[0].id == 2


def test_filter_by_address_empty_config_passes_all():
    config = _make_config(geo="")
    filter_service = AdsFilter(config)

    ad1 = Item(id=1, geo=None)
    ad2 = Item(id=2, geo=Geo(geoReferences=[], formattedAddress="Казань"))

    result = filter_service._filter_by_address([ad1, ad2])
    assert len(result) == 2


def test_filter_by_price_range_handles_none_price():
    config = _make_config(min_price=1000, max_price=5000)
    filter_service = AdsFilter(config)

    ad_none_price = Item(id=1, priceDetailed=None)
    ad_in_range = Item(
        id=2,
        priceDetailed=PriceDetailed(
            enabled=True,
            fullString="3 000 ₽",
            hasValue=True,
            postfix="",
            string="3 000",
            stringWithoutDiscount=None,
            title={},
            titleDative="",
            value=3000,
            wasLowered=False,
            exponent=""
        )
    )
    ad_too_high = Item(
        id=3,
        priceDetailed=PriceDetailed(
            enabled=True,
            fullString="10 000 ₽",
            hasValue=True,
            postfix="",
            string="10 000",
            stringWithoutDiscount=None,
            title={},
            titleDative="",
            value=10000,
            wasLowered=False,
            exponent=""
        )
    )

    result = filter_service._filter_by_price_range([ad_none_price, ad_in_range, ad_too_high])
    assert len(result) == 1
    assert result[0].id == 2


def test_filter_by_promotion_handles_null_vas():
    config = _make_config(ignore_promotion=True)
    filter_service = AdsFilter(config)

    # Step with payload having vas = None
    step_null_vas = IvaStep(
        componentData=IvaComponent(component="test", payload=None),
        payload={"vas": None},
        default=False
    )
    ad_with_null_vas = Item(
        id=1,
        iva={"DateInfoStep": [step_null_vas]}
    )

    # Step with payload having vas with "Продвинуто"
    step_promoted = IvaStep(
        componentData=IvaComponent(component="test", payload=None),
        payload={"vas": [{"title": "Продвинуто"}]},
        default=False
    )
    ad_promoted = Item(
        id=2,
        iva={"DateInfoStep": [step_promoted]}
    )

    result = filter_service._filter_by_promotion([ad_with_null_vas, ad_promoted])
    assert len(result) == 1
    assert result[0].id == 1


def test_filter_by_recent_time_handles_none_timestamp():
    config = _make_config(max_age=3600)
    filter_service = AdsFilter(config)

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    ad_none_ts = Item(id=1, sortTimeStamp=None)
    ad_recent = Item(id=2, sortTimeStamp=now_ms - 60000)  # 1 min ago
    ad_old = Item(id=3, sortTimeStamp=now_ms - 7200000)   # 2 hours ago

    result = filter_service._filter_by_recent_time([ad_none_ts, ad_recent, ad_old])
    assert len(result) == 1
    assert result[0].id == 2
