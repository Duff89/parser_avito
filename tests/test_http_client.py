import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from curl_cffi import requests

from parser.http.client import HttpClient, get_ca_bundle, _normalize_ca_path
from parser.proxies.proxy import NoProxy


def test_get_ca_bundle_from_env(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
        fake_cert = f.name
    try:
        monkeypatch.setenv("CURL_CA_BUNDLE", fake_cert)
        assert get_ca_bundle() == fake_cert
    finally:
        if os.path.exists(fake_cert):
            os.remove(fake_cert)


def test_get_ca_bundle_from_certifi(monkeypatch):
    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)

    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
        fake_cert = f.name
    try:
        with patch("certifi.where", return_value=fake_cert):
            bundle = get_ca_bundle()
            assert bundle == fake_cert
    finally:
        if os.path.exists(fake_cert):
            os.remove(fake_cert)


def test_get_ca_bundle_from_meipass(monkeypatch):
    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)

    with tempfile.TemporaryDirectory() as tmp_dir:
        cert_dir = Path(tmp_dir) / "certifi"
        cert_dir.mkdir(parents=True, exist_ok=True)
        cert_file = cert_dir / "cacert.pem"
        cert_file.write_text("dummy-cert-data", encoding="utf-8")

        monkeypatch.setattr(sys, "_MEIPASS", tmp_dir, raising=False)
        with patch("certifi.where", return_value=str(Path(tmp_dir) / "nonexistent" / "cacert.pem")):
            bundle = get_ca_bundle()
            assert bundle == str(cert_file)


def test_get_ca_bundle_missing_returns_false(monkeypatch):
    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)

    if hasattr(sys, "_MEIPASS"):
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    with patch("certifi.where", return_value=r"C:\nonexistent\cacert.pem"):
        bundle = get_ca_bundle()
        assert bundle is False


def test_normalize_ca_path_ascii():
    ascii_path = r"C:\Users\test\cacert.pem"
    assert _normalize_ca_path(ascii_path) == ascii_path


def test_http_client_init_with_custom_verify():
    proxy = NoProxy()
    client = HttpClient(proxy=proxy, verify=False)
    assert client.verify is False


def test_http_client_recovers_from_curl_77():
    proxy = NoProxy()
    client = HttpClient(proxy=proxy, verify=r"C:\fake\broken\cacert.pem")
    assert client.verify == r"C:\fake\broken\cacert.pem"

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.raise_for_status = MagicMock()

    calls = 0

    mock_session = MagicMock()

    def mock_request(method, url, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise requests.RequestsError(
                "Failed to perform, curl: (77) error setting certificate verify locations: "
                r"CAfile: C:\fake\broken\cacert.pem CApath: none."
            )
        return fake_response

    mock_session.request = mock_request
    mock_session.close = MagicMock()

    with patch.object(client, "_build_client", return_value=mock_session):
        client._client = mock_session
        response = client.request("GET", "https://m.avito.ru/api/1/card/items/123")
        assert response == fake_response
        assert client.verify is False
        assert calls == 2


def test_http_client_fetch_item_data():
    proxy = NoProxy()
    client = HttpClient(proxy=proxy, verify=False)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": 12345, "title": "Test Item"}

    with patch.object(client, "request", return_value=mock_resp) as mock_req:
        data = client.fetch_item_data(12345)
        assert data == {"id": 12345, "title": "Test Item"}
        mock_req.assert_called_once()
        assert "12345" in mock_req.call_args[0][1]
