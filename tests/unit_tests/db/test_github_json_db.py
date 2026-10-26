import base64
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from platzky.db.exceptions import ReadOnlyStorageError
from platzky.db.github_json_db import (
    GithubJsonDb,
    GithubJsonDbConfig,
    db_config_type,
    db_from_config,
)


def _api_response(payload: dict[str, Any] | list[dict[str, Any]]) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    return response


def _file_payload(raw: str) -> dict[str, Any]:
    return {"content": base64.b64encode(raw.encode()).decode(), "download_url": None}


@pytest.fixture
def mock_get():
    with patch("platzky.db.github_json_db.requests.Session") as session_cls:
        yield session_cls.return_value.get


def test_returns_correct_db_config_type():
    assert db_config_type() == GithubJsonDbConfig


def test_creates_github_json_db_from_config(mock_get: MagicMock):
    mock_get.return_value = _api_response(_file_payload('{"key": "value"}'))

    config = GithubJsonDbConfig(
        TYPE="github_json_db",
        GITHUB_TOKEN="fake_token",
        REPO_NAME="fake_repo",
        PATH_TO_FILE="path/to/file.json",
        BRANCH_NAME="main",
    )
    db = db_from_config(config)
    assert isinstance(db, GithubJsonDb)
    assert db.branch_name == "main"
    assert db.file_path == "path/to/file.json"
    assert db.data == {"key": "value"}


def test_retrieves_data_from_github_file(mock_get: MagicMock):
    mock_get.return_value = _api_response(_file_payload('{"key": "value"}'))

    db = GithubJsonDb("fake_token", "fake_repo", "main", "path/to/file.json")
    assert db.data == {"key": "value"}


def test_requests_contents_api_with_branch_and_token(mock_get: MagicMock):
    mock_get.return_value = _api_response(_file_payload("{}"))

    GithubJsonDb("fake_token", "owner/repo", "dev", "path/to/file.json")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://api.github.com/repos/owner/repo/contents/path/to/file.json"
    assert kwargs["params"] == {"ref": "dev"}
    assert kwargs["headers"]["Authorization"] == "Bearer fake_token"


def test_raises_error_for_directory_path(mock_get: MagicMock):
    mock_get.return_value = _api_response([{"type": "file"}])

    with pytest.raises(
        ValueError, match=r"Path 'path/to/file\.json' points to a directory, not a file"
    ):
        GithubJsonDb("fake_token", "fake_repo", "main", "path/to/file.json")


def test_retrieves_data_via_download_url_when_content_is_empty(mock_get: MagicMock):
    download_response = MagicMock()
    download_response.text = '{"key": "value"}'
    mock_get.side_effect = [
        _api_response({"content": "", "download_url": "https://example.com/file.json"}),
        download_response,
    ]

    db = GithubJsonDb("fake_token", "fake_repo", "main", "path/to/file.json")
    assert db.data == {"key": "value"}
    assert mock_get.call_args.args[0] == "https://example.com/file.json"


def test_raises_error_for_invalid_json_content(mock_get: MagicMock):
    mock_get.return_value = _api_response(_file_payload("invalid json"))

    with pytest.raises(ValueError, match="Error parsing JSON content: Expecting value"):
        GithubJsonDb("fake_token", "fake_repo", "main", "path/to/file.json")


def test_raises_error_for_http_error(mock_get: MagicMock):
    response = _api_response({})
    response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
    mock_get.return_value = response

    with pytest.raises(ValueError, match="Error retrieving GitHub content: 404 Not Found"):
        GithubJsonDb("fake_token", "fake_repo", "main", "path/to/file.json")


def test_add_comment_raises_read_only_storage_error(mock_get: MagicMock):
    """GithubJsonDb is read-only: writes must fail loudly, not vanish silently."""
    content = json.dumps({"site_content": {"posts": [{"slug": "post-1", "comments": []}]}})
    mock_get.return_value = _api_response(_file_payload(content))

    db = GithubJsonDb("fake_token", "fake_repo", "main", "path/to/file.json")

    with pytest.raises(ReadOnlyStorageError):
        db.add_comment("Test User", "New comment", "post-1")


def test_omits_authorization_header_without_token(mock_get: MagicMock):
    mock_get.return_value = _api_response(_file_payload("{}"))

    GithubJsonDb("", "owner/repo", "main", "file.json")

    assert "Authorization" not in mock_get.call_args.kwargs["headers"]


def test_reports_non_json_api_response_separately_from_data_file_errors(mock_get: MagicMock):
    response = _api_response({})
    response.json.side_effect = requests.exceptions.JSONDecodeError("Expecting value", "<html>", 0)
    mock_get.return_value = response

    with pytest.raises(ValueError, match="not JSON") as exc_info:
        GithubJsonDb("fake_token", "fake_repo", "main", "file.json")

    assert "Error parsing JSON content" not in str(exc_info.value)


def test_session_mounts_retrying_adapter():
    with patch("platzky.db.github_json_db.requests.Session") as session_cls:
        session = session_cls.return_value
        session.get.return_value = _api_response(_file_payload("{}"))

        GithubJsonDb("fake_token", "fake_repo", "main", "file.json")

    prefix, adapter = session.mount.call_args.args
    assert prefix == "https://"
    assert adapter.max_retries.total == 3
    assert 503 in adapter.max_retries.status_forcelist
