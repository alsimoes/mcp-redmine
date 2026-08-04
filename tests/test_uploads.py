"""Tests for mcp_redmine.uploads."""

from __future__ import annotations

from pathlib import Path

import pytest
import responses as responses_lib

from mcp_redmine.client import RedmineClient
from mcp_redmine.errors import RedmineError
from mcp_redmine.uploads import MAX_UPLOAD_BYTES, upload_file


def test_missing_file_is_rejected_before_touching_the_network(
    client: RedmineClient,
) -> None:
    with pytest.raises(RedmineError, match="not found"):
        upload_file(client, "/no/such/file.txt")


def test_empty_file_is_rejected(client: RedmineClient, tmp_path: Path) -> None:
    empty_file = tmp_path / "empty.txt"
    empty_file.write_bytes(b"")
    with pytest.raises(RedmineError, match="empty"):
        upload_file(client, str(empty_file))


def test_oversized_file_is_rejected(
    client: RedmineClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    big_file = tmp_path / "big.bin"
    big_file.write_bytes(b"x")
    monkeypatch.setattr(
        "mcp_redmine.uploads.os.path.getsize", lambda _path: MAX_UPLOAD_BYTES + 1
    )
    with pytest.raises(RedmineError, match="MB"):
        upload_file(client, str(big_file))


def test_successful_upload_returns_token_name_and_type(
    client: RedmineClient,
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    report = tmp_path / "report.pdf"
    report.write_bytes(b"%PDF-1.4 fake content")

    mocked_responses.add(
        responses_lib.POST,
        "https://redmine.example.com/uploads.json",
        json={"upload": {"token": "abc123.def456"}},
        status=201,
    )

    token, name, content_type = upload_file(client, str(report))

    assert token == "abc123.def456"
    assert name == "report.pdf"
    assert content_type == "application/pdf"


def test_missing_token_in_response_raises(
    client: RedmineClient,
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    report = tmp_path / "report.txt"
    report.write_bytes(b"content")

    mocked_responses.add(
        responses_lib.POST,
        "https://redmine.example.com/uploads.json",
        json={"upload": {}},
        status=201,
    )

    with pytest.raises(RedmineError, match="no token"):
        upload_file(client, str(report))


def test_custom_file_name_overrides_basename(
    client: RedmineClient,
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    local_file = tmp_path / "tmp12345"
    local_file.write_bytes(b"content")

    mocked_responses.add(
        responses_lib.POST,
        "https://redmine.example.com/uploads.json",
        json={"upload": {"token": "tok"}},
        status=201,
    )

    _token, name, content_type = upload_file(client, str(local_file), "notes.txt")

    assert name == "notes.txt"
    assert content_type == "text/plain"
