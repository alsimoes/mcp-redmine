"""Shared pytest fixtures: an isolated Redmine client with mocked HTTP."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
import responses as responses_lib

from mcp_redmine.app import set_client
from mcp_redmine.client import RedmineClient
from mcp_redmine.config import Settings

BASE_URL = "https://redmine.example.com"
API_KEY = "test-api-key"


@pytest.fixture
def settings() -> Settings:
    """Settings pointing at a fake Redmine instance."""
    return Settings(url=BASE_URL, api_key=API_KEY, timeout=15.0)


@pytest.fixture
def client(settings: Settings) -> Iterator[RedmineClient]:
    """A RedmineClient wired up as the process-wide client used by tools.

    Every test gets a fresh client, and set_client(None) resets the global
    afterwards so tests never leak state into each other.
    """
    redmine_client = RedmineClient(settings)
    set_client(redmine_client)
    yield redmine_client
    set_client(None)


@pytest.fixture
def mocked_responses() -> Iterator[responses_lib.RequestsMock]:
    """An activated `responses` mock registry for stubbing Redmine's API."""
    with responses_lib.RequestsMock(assert_all_requests_are_fired=True) as mock:
        yield mock
