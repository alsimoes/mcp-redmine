"""Tests for mcp_redmine.tools.issues."""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import responses as responses_lib

from mcp_redmine.client import RedmineClient
from mcp_redmine.tools.issues import (
    _optional_issue_fields,
    bulk_update_issues,
    list_issues,
)


def _query(url: str | None) -> dict[str, list[str]]:
    assert url is not None
    return parse_qs(urlparse(url).query)


class TestOptionalIssueFields:
    """The (0, "", -1) sentinels mean 'leave this field alone'."""

    def test_defaults_produce_an_empty_payload(self) -> None:
        assert _optional_issue_fields() == {}

    def test_zero_id_is_omitted(self) -> None:
        assert "category_id" not in _optional_issue_fields(category_id=0)

    def test_nonzero_id_is_included(self) -> None:
        assert _optional_issue_fields(category_id=5) == {"category_id": 5}

    def test_negative_done_ratio_is_omitted(self) -> None:
        assert _optional_issue_fields(done_ratio=-1) == {}

    def test_zero_done_ratio_is_included(self) -> None:
        # 0% complete is a legitimate value, distinct from "not provided".
        assert _optional_issue_fields(done_ratio=0) == {"done_ratio": 0}

    def test_custom_fields_are_converted_to_redmine_shape(self) -> None:
        result = _optional_issue_fields(custom_fields={"1": "8"})
        assert result == {"custom_fields": [{"id": 1, "value": "8"}]}


class TestListIssuesFilters:
    def test_date_range_uses_between_operator(
        self, client: RedmineClient, mocked_responses: responses_lib.RequestsMock
    ) -> None:
        mocked_responses.add(
            responses_lib.GET,
            "https://redmine.example.com/issues.json",
            json={"issues": [], "total_count": 0},
            status=200,
        )
        list_issues(created_after="2026-01-01", created_before="2026-01-31")
        query = _query(mocked_responses.calls[0].request.url)
        assert query["created_on"] == ["><2026-01-01|2026-01-31"]

    def test_created_after_only_uses_gte(
        self, client: RedmineClient, mocked_responses: responses_lib.RequestsMock
    ) -> None:
        mocked_responses.add(
            responses_lib.GET,
            "https://redmine.example.com/issues.json",
            json={"issues": [], "total_count": 0},
            status=200,
        )
        list_issues(created_after="2026-01-01")
        query = _query(mocked_responses.calls[0].request.url)
        assert query["created_on"] == [">=2026-01-01"]

    def test_subject_contains_uses_tilde_prefix(
        self, client: RedmineClient, mocked_responses: responses_lib.RequestsMock
    ) -> None:
        mocked_responses.add(
            responses_lib.GET,
            "https://redmine.example.com/issues.json",
            json={"issues": [], "total_count": 0},
            status=200,
        )
        list_issues(subject_contains="crash")
        query = _query(mocked_responses.calls[0].request.url)
        assert query["subject"] == ["~crash"]

    def test_custom_fields_become_cf_params(
        self, client: RedmineClient, mocked_responses: responses_lib.RequestsMock
    ) -> None:
        mocked_responses.add(
            responses_lib.GET,
            "https://redmine.example.com/issues.json",
            json={"issues": [], "total_count": 0},
            status=200,
        )
        list_issues(custom_fields={"1": "8"})
        query = _query(mocked_responses.calls[0].request.url)
        assert query["cf_1"] == ["8"]

    def test_query_id_ignores_other_filters(
        self, client: RedmineClient, mocked_responses: responses_lib.RequestsMock
    ) -> None:
        mocked_responses.add(
            responses_lib.GET,
            "https://redmine.example.com/issues.json",
            json={"issues": [], "total_count": 0},
            status=200,
        )
        list_issues(query_id=42, status="closed", tracker_id=3)
        query = _query(mocked_responses.calls[0].request.url)
        assert query["query_id"] == ["42"]
        assert "status_id" not in query
        assert "tracker_id" not in query

    def test_remaining_accounts_for_offset(
        self, client: RedmineClient, mocked_responses: responses_lib.RequestsMock
    ) -> None:
        mocked_responses.add(
            responses_lib.GET,
            "https://redmine.example.com/issues.json",
            json={
                "issues": [
                    {
                        "id": i,
                        "subject": "x",
                        "status": {"name": "Open"},
                        "priority": {"name": "Normal"},
                        "project": {"name": "Demo"},
                    }
                    for i in range(10)
                ],
                "total_count": 30,
            },
            status=200,
        )
        result = json.loads(list_issues(offset=10, limit=10))
        assert result["total"] == 30
        assert result["returned"] == 10
        assert result["offset"] == 10
        assert result["remaining"] == 10


class TestBulkUpdateIssues:
    def test_requires_at_least_one_issue(self, client: RedmineClient) -> None:
        assert "at least one issue" in bulk_update_issues(issue_ids=[])

    def test_requires_at_least_one_field(self, client: RedmineClient) -> None:
        assert "Nothing to update" in bulk_update_issues(issue_ids=[1])

    def test_partial_failure_does_not_abort_the_batch(
        self, client: RedmineClient, mocked_responses: responses_lib.RequestsMock
    ) -> None:
        mocked_responses.add(
            responses_lib.PUT,
            "https://redmine.example.com/issues/1.json",
            json={},
            status=200,
        )
        mocked_responses.add(
            responses_lib.PUT,
            "https://redmine.example.com/issues/2.json",
            json={"errors": ["Status cannot be changed"]},
            status=422,
        )

        result = json.loads(bulk_update_issues(issue_ids=[1, 2], status_id=5))

        assert result["attempted"] == 2
        assert result["updated"] == 1
        assert result["failed"] == 1
        assert result["details"][0] == {"issue": 1, "result": "ok"}
        assert result["details"][1]["issue"] == 2
        assert result["details"][1]["result"] == "error"
        assert "Status cannot be changed" in result["details"][1]["detail"]
