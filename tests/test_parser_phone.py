from types import SimpleNamespace

import parser_cls
from dto import AvitoConfig
from parser_cls import AvitoParse


def make_parser(parse_phone):
    parser = object.__new__(AvitoParse)
    parser.config = AvitoConfig(urls=[], parse_phone=parse_phone)
    return parser


def test_parse_phone_disabled_does_not_call_service(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("ParsePhone must not be called")

    monkeypatch.setattr(parser_cls, "ParsePhone", fail_if_called)
    ads = [SimpleNamespace(id=1)]

    result = make_parser(parse_phone=False).parse_phone(ads)

    assert result == ads


def test_parse_phone_enabled_calls_service(monkeypatch):
    ads = [SimpleNamespace(id=1)]
    updated_ads = [SimpleNamespace(id=1, phone="79990000000")]
    calls = []

    class FakeParsePhone:
        def __init__(self, ads, config):
            calls.append((ads, config))

        def parse_phones(self):
            return updated_ads

    monkeypatch.setattr(parser_cls, "ParsePhone", FakeParsePhone)

    result = make_parser(parse_phone=True).parse_phone(ads)

    assert result == updated_ads
    assert calls
    assert calls[0][0] == ads
