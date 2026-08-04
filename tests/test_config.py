"""Tests for mcp_redmine.config."""

from __future__ import annotations

import pytest

from mcp_redmine.config import ConfigurationError, load_settings


def test_missing_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDMINE_URL", raising=False)
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.delenv("REDMINE_API_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        load_settings()


def test_trailing_slash_is_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com/")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.delenv("REDMINE_TIMEOUT", raising=False)
    settings = load_settings()
    assert settings.url == "https://redmine.example.com"


def test_default_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.delenv("REDMINE_TIMEOUT", raising=False)
    settings = load_settings()
    assert settings.timeout == 15.0


def test_custom_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.setenv("REDMINE_TIMEOUT", "30")
    settings = load_settings()
    assert settings.timeout == 30.0


def test_invalid_timeout_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.setenv("REDMINE_TIMEOUT", "not-a-number")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_zero_timeout_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.setenv("REDMINE_TIMEOUT", "0")
    with pytest.raises(ConfigurationError):
        load_settings()
