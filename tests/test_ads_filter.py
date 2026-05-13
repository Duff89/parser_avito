from types import SimpleNamespace

from dto import AvitoConfig
from filters.ads_filter import AdsFilter


def make_ad(address):
    geo = None if address is None else SimpleNamespace(formattedAddress=address)
    return SimpleNamespace(geo=geo)


def test_geo_filter_keeps_matching_address():
    config = AvitoConfig(urls=[], geo="Екатеринбург", max_age=0)
    ads = [make_ad("Россия, Свердловская область, Екатеринбург")]

    result = AdsFilter(config=config)._filter_by_address(ads)

    assert result == ads


def test_geo_filter_ignores_missing_geo():
    config = AvitoConfig(urls=[], geo="Екатеринбург", max_age=0)

    result = AdsFilter(config=config)._filter_by_address([make_ad(None)])

    assert result == []


def test_geo_filter_is_case_insensitive():
    config = AvitoConfig(urls=[], geo="екатеринбург", max_age=0)
    ads = [make_ad("ЕКАТЕРИНБУРГ, Центр")]

    result = AdsFilter(config=config)._filter_by_address(ads)

    assert result == ads
