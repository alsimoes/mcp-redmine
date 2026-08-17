"""Tests for mcp_redmine.tools.time_entries."""

from __future__ import annotations

import json

import responses as responses_lib

from mcp_redmine.client import RedmineClient
from mcp_redmine.tools.time_entries import log_time


class TestLogTimeProjectId:
    """POST /time_entries.json only accepts a numeric project_id, unlike
    /issues.json which also accepts the string identifier — log_time must
    resolve it before sending the request.
    """

    def test_numeric_identifier_is_sent_as_is(
        self, client: RedmineClient, mocked_responses: responses_lib.RequestsMock
    ) -> None:
        mocked_responses.add(
            responses_lib.POST,
            "https://redmine.example.com/time_entries.json",
            json={"time_entry": {"id": 1}},
            status=201,
        )
        log_time(hours=1.0, date="2026-01-01", project_identifier="42")
        body = json.loads(mocked_responses.calls[0].request.body)
        assert body["time_entry"]["project_id"] == 42

    def test_string_identifier_is_resolved_to_a_numeric_id(
        self, client: RedmineClient, mocked_responses: responses_lib.RequestsMock
    ) -> None:
        mocked_responses.add(
            responses_lib.GET,
            "https://redmine.example.com/projects/mcp-test.json",
            json={"project": {"id": 7, "identifier": "mcp-test"}},
            status=200,
        )
        mocked_responses.add(
            responses_lib.POST,
            "https://redmine.example.com/time_entries.json",
            json={"time_entry": {"id": 1}},
            status=201,
        )
        log_time(hours=1.0, date="2026-01-01", project_identifier="mcp-test")
        body = json.loads(mocked_responses.calls[1].request.body)
        assert body["time_entry"]["project_id"] == 7
