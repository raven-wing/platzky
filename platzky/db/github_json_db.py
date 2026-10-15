"""GitHub-based JSON database implementation."""

import json
import threading
from typing import Any

import requests
from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
from pydantic import Field

from platzky.db.db import DBConfig
from platzky.db.json_db import Json as JsonDB
from platzky.db.json_stores import JsonStore


def db_config_type() -> type["GithubJsonDbConfig"]:
    """Return the configuration class for GitHub JSON database.

    Returns:
        GithubJsonDbConfig class
    """
    return GithubJsonDbConfig


class GithubJsonDbConfig(DBConfig):
    """Configuration for GitHub JSON database connection."""

    github_token: str = Field(alias="GITHUB_TOKEN")
    repo_name: str = Field(alias="REPO_NAME")
    path_to_file: str = Field(alias="PATH_TO_FILE")
    branch_name: str = Field(alias="BRANCH_NAME", default="main")


def db_from_config(config: GithubJsonDbConfig) -> "GithubJsonDb":
    """Create a GitHub JSON database instance from configuration.

    Args:
        config: GitHub JSON database configuration

    Returns:
        Configured GitHub JSON database instance
    """
    return GithubJsonDb(
        config.github_token, config.repo_name, config.branch_name, config.path_to_file
    )


def _download(url: str) -> str:
    response = requests.get(url, timeout=40)
    response.raise_for_status()
    return response.text


def _read_text(file: ContentFile) -> str:
    # The contents API inlines only small files; larger ones need the raw download URL.
    return file.decoded_content.decode("utf-8") if file.content else _download(file.download_url)


class GithubStore(JsonStore):
    """A JSON document stored as a file on a GitHub branch.

    Every `save()` is one commit to the branch. The blob SHA from the last
    load/save is sent with each commit, so a concurrent change to the file on
    GitHub makes the commit fail (409) instead of overwriting it.
    """

    def __init__(self, repo: Repository, branch_name: str, path: str) -> None:
        """Initialize the store.

        Args:
            repo: Repository holding the file
            branch_name: Branch to read from and commit to
            path: Path to the JSON file within the repository
        """
        self._repo = repo
        self._branch_name = branch_name
        self._path = path
        self._sha: str | None = None
        self._lock = threading.Lock()

    def load(self) -> dict[str, Any]:
        """Fetch and parse the file from the branch.

        Returns:
            Parsed JSON document

        Raises:
            ValueError: If the path is a directory or the content can't be fetched or parsed.
        """
        try:
            file = self._repo.get_contents(self._path, ref=self._branch_name)
            if isinstance(file, list):
                raise ValueError(f"Path '{self._path}' points to a directory, not a file")
            data = json.loads(_read_text(file))
            self._sha = file.sha
        except (json.JSONDecodeError, requests.RequestException) as e:
            raise ValueError(f"Error parsing JSON content: {e}")
        except Exception as e:
            raise ValueError(f"Error retrieving GitHub content: {e}")
        return data

    def save(self, data: dict[str, Any]) -> None:
        """Commit the document to the branch as indented, non-ASCII-escaped JSON."""
        content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        with self._lock:
            if self._sha is None:
                raise RuntimeError("Cannot save before the document has been loaded.")
            result = self._repo.update_file(
                self._path,
                f"Update {self._path}",
                content,
                self._sha,
                branch=self._branch_name,
            )
            self._sha = result["content"].sha


class GithubJsonDb(JsonDB):
    """JSON database stored in a GitHub repository.

    Reads from and commits to a single branch, one commit per write. Point it at
    a dedicated data branch and merge that into your main branch through PRs.
    """

    def __init__(
        self, github_token: str, repo_name: str, branch_name: str, path_to_file: str
    ) -> None:
        """Initialize GitHub JSON database connection.

        Args:
            github_token: GitHub personal access token
            repo_name: Full repository name (e.g., 'owner/repo')
            branch_name: Branch to read from and commit to
            path_to_file: Path to the JSON file within the repository
        """
        self.branch_name = branch_name
        self.repo = Github(github_token).get_repo(repo_name)
        self.file_path = path_to_file

        super().__init__(store=GithubStore(self.repo, branch_name, path_to_file))

        self.module_name = "github_json_db"
        self.db_name = "GithubJsonDb"
