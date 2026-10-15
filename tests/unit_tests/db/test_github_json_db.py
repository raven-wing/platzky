import base64
import json
from unittest.mock import MagicMock, patch

import pytest
from github import GithubException

from platzky.db.github_json_db import (
    GithubJsonDb,
    GithubJsonDbConfig,
    db_config_type,
    db_from_config,
)


def test_returns_correct_db_config_type():
    assert db_config_type() == GithubJsonDbConfig


def test_creates_github_json_db_from_config():
    with patch("platzky.db.github_json_db.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_file = MagicMock()
        mock_file.content = "eyJrZXkiOiAidmFsdWUifQ=="
        mock_file.decoded_content = b'{"key": "value"}'
        MockGithub.return_value.get_repo.return_value = mock_repo
        mock_repo.get_contents.return_value = mock_file

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


def test_retrieves_data_from_github_file():
    with patch("platzky.db.github_json_db.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_file = MagicMock()
        mock_file.content = "eyJrZXkiOiAidmFsdWUifQ=="  # Base64 for '{"key": "value"}'
        mock_file.decoded_content = b'{"key": "value"}'
        MockGithub.return_value.get_repo.return_value = mock_repo
        mock_repo.get_contents.return_value = mock_file

        db = GithubJsonDb("fake_token", "fake_repo", "main", "path/to/file.json")
        assert db.data == {"key": "value"}


def test_raises_error_for_directory_path():
    with patch("platzky.db.github_json_db.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_contents.return_value = [MagicMock()]  # Simulate directory
        MockGithub.return_value.get_repo.return_value = mock_repo

        with pytest.raises(
            ValueError, match=r"Path 'path/to/file\.json' points to a directory, not a file"
        ):
            GithubJsonDb("fake_token", "fake_repo", "main", "path/to/file.json")


def test_retrieves_data_via_download_url_when_content_is_empty():
    with (
        patch("platzky.db.github_json_db.Github") as MockGithub,
        patch("platzky.db.github_json_db.requests.get") as mock_requests,
    ):
        mock_repo = MagicMock()
        mock_file = MagicMock()
        mock_file.content = None
        mock_file.download_url = "https://example.com/file.json"
        mock_repo.get_contents.return_value = mock_file
        MockGithub.return_value.get_repo.return_value = mock_repo

        mock_response = MagicMock()
        mock_response.text = '{"key": "value"}'
        mock_requests.return_value = mock_response

        db = GithubJsonDb("fake_token", "fake_repo", "main", "path/to/file.json")
        assert db.data == {"key": "value"}


def test_raises_error_for_invalid_json_content():
    with patch("platzky.db.github_json_db.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_file = MagicMock()
        mock_file.content = "eyJrZXkiOiAidmFsdWUifQ=="  # Base64 for '{"key": "value"}'
        mock_file.decoded_content = b"invalid json"
        mock_repo.get_contents.return_value = mock_file
        MockGithub.return_value.get_repo.return_value = mock_repo

        with pytest.raises(ValueError, match="Error parsing JSON content: Expecting value"):
            GithubJsonDb("fake_token", "fake_repo", "main", "path/to/file.json")


def _repo_with_post(sha: str = "sha-1") -> MagicMock:
    mock_repo = MagicMock()
    mock_file = MagicMock()
    content = json.dumps({"site_content": {"posts": [{"slug": "post-1", "comments": []}]}})
    mock_file.content = base64.b64encode(content.encode()).decode()
    mock_file.decoded_content = content.encode()
    mock_file.sha = sha
    mock_repo.get_contents.return_value = mock_file
    return mock_repo


def test_add_comment_commits_to_configured_branch():
    with patch("platzky.db.github_json_db.Github") as MockGithub:
        mock_repo = _repo_with_post()
        mock_repo.update_file.return_value = {"content": MagicMock(sha="sha-2")}
        MockGithub.return_value.get_repo.return_value = mock_repo

        db = GithubJsonDb("fake_token", "fake_repo", "onlydata", "path/to/file.json")
        db.add_comment("Zażółć Gęślą", "Jaźń", "post-1")

        mock_repo.get_contents.assert_called_once_with("path/to/file.json", ref="onlydata")
        path, _message, content, sha = mock_repo.update_file.call_args.args
        assert path == "path/to/file.json"
        assert sha == "sha-1"
        assert mock_repo.update_file.call_args.kwargs == {"branch": "onlydata"}
        assert "Zażółć Gęślą" in content
        assert content.startswith('{\n  "site_content"')
        comments = json.loads(content)["site_content"]["posts"][0]["comments"]
        assert [(c["author"], c["comment"]) for c in comments] == [("Zażółć Gęślą", "Jaźń")]


def test_consecutive_writes_use_sha_of_previous_commit():
    with patch("platzky.db.github_json_db.Github") as MockGithub:
        mock_repo = _repo_with_post()
        mock_repo.update_file.side_effect = [
            {"content": MagicMock(sha="sha-2")},
            {"content": MagicMock(sha="sha-3")},
        ]
        MockGithub.return_value.get_repo.return_value = mock_repo

        db = GithubJsonDb("fake_token", "fake_repo", "onlydata", "path/to/file.json")
        db.add_comment("A", "first", "post-1")
        db.add_comment("B", "second", "post-1")

        shas = [call.args[3] for call in mock_repo.update_file.call_args_list]
        assert shas == ["sha-1", "sha-2"]


def test_failed_commit_leaves_data_unchanged():
    with patch("platzky.db.github_json_db.Github") as MockGithub:
        mock_repo = _repo_with_post()
        mock_repo.update_file.side_effect = GithubException(409, "conflict", None)
        MockGithub.return_value.get_repo.return_value = mock_repo

        db = GithubJsonDb("fake_token", "fake_repo", "onlydata", "path/to/file.json")

        with pytest.raises(GithubException):
            db.add_comment("Test User", "New comment", "post-1")
        assert db.data["site_content"]["posts"][0]["comments"] == []
