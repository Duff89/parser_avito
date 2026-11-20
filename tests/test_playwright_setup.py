import asyncio
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest
from playwright_setup import (
    get_browsers_dir,
    _check_browser_sync,
    _browser_installed,
    ensure_playwright_installed,
)


def test_get_browsers_dir_custom_env(monkeypatch):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "custom/browser/path")
    assert get_browsers_dir() == "custom/browser/path"


def test_get_browsers_dir_default(monkeypatch):
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    path = get_browsers_dir()
    assert "ms-playwright" in path


def test_browser_installed_sync():
    with patch("playwright_setup._check_browser_sync", return_value=True) as mock_check:
        assert _browser_installed("chromium") is True
        mock_check.assert_called_once_with("chromium")


def test_browser_installed_inside_asyncio_loop():
    async def async_caller():
        with patch("playwright_setup._check_browser_sync", return_value=True) as mock_check:
            return _browser_installed("chromium")

    result = asyncio.run(async_caller())
    assert result is True


def test_ensure_playwright_installed_when_already_installed():
    with patch("playwright_setup._browser_installed", return_value=True), \
         patch("subprocess.run") as mock_run:
        ensure_playwright_installed("chromium")
        mock_run.assert_not_called()


def _expected_frozen_run_kwargs():
    kwargs = {"env": {}, "check": True}
    if sys.platform == "win32":
        no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if no_window:
            kwargs["creationflags"] = no_window
    return kwargs


def test_ensure_playwright_installed_frozen_uses_driver(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "AvitoParser.exe")

    mock_driver = MagicMock()
    mock_driver.compute_driver_executable.return_value = ("node.exe", "cli.js")
    mock_driver.get_driver_env.return_value = {}

    with patch.dict(sys.modules, {
        "playwright": MagicMock(),
        "playwright._impl": MagicMock(),
        "playwright._impl._driver": mock_driver,
    }), \
         patch("playwright_setup._browser_installed", return_value=False), \
         patch("subprocess.run") as mock_run:

        ensure_playwright_installed("chromium")

        mock_run.assert_called_once_with(
            ["node.exe", "cli.js", "install", "chromium"],
            **_expected_frozen_run_kwargs(),
        )


def test_ensure_playwright_installed_frozen_single_str_driver(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "AvitoParser.exe")

    mock_driver = MagicMock()
    mock_driver.compute_driver_executable.return_value = "playwright.cmd"
    mock_driver.get_driver_env.return_value = {}

    with patch.dict(sys.modules, {
        "playwright": MagicMock(),
        "playwright._impl": MagicMock(),
        "playwright._impl._driver": mock_driver,
    }), \
         patch("playwright_setup._browser_installed", return_value=False), \
         patch("subprocess.run") as mock_run:

        ensure_playwright_installed("chromium")

        mock_run.assert_called_once_with(
            ["playwright.cmd", "install", "chromium"],
            **_expected_frozen_run_kwargs(),
        )


def test_ensure_playwright_installed_non_frozen_uses_sys_executable(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", "C:\\python\\python.exe")

    with patch("playwright_setup._browser_installed", return_value=False), \
         patch("subprocess.run") as mock_run:

        ensure_playwright_installed("chromium")

        mock_run.assert_called_once_with(
            ["C:\\python\\python.exe", "-m", "playwright", "install", "chromium"],
            check=True,
        )
