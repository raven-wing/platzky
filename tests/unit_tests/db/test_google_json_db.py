import json
from collections.abc import Mapping
from unittest.mock import MagicMock, patch

import pytest

from platzky.db.exceptions import FileRefCycleError, FileRefTraversalError, InvalidFileRefError
from platzky.db.google_json_db import GoogleJsonDb, get_blob


class TestGoogleJsonDb:
    @pytest.fixture
    def mock_client(self):
        with patch("platzky.db.google_json_db.Client") as mock_client:
            yield mock_client

    def test_get_blob(self, mock_client: MagicMock):
        """Test the get_blob function that retrieves a blob from Google Cloud Storage."""
        # Set up the mock
        mock_bucket = MagicMock()
        mock_client.return_value.bucket.return_value = mock_bucket
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob

        # Call the function
        result = get_blob("test-bucket", "test-blob.json")

        # Assert the mock was called correctly
        mock_client.return_value.bucket.assert_called_once_with("test-bucket")
        mock_bucket.blob.assert_called_once_with("test-blob.json")

        # Assert the result is the mock blob
        assert result == mock_blob


def _make_bucket(blobs: Mapping[str, object]) -> MagicMock:
    bucket = MagicMock()
    blob_mocks: dict[str, MagicMock] = {}
    for name, content in blobs.items():
        blob_mock = MagicMock()
        blob_mock.download_as_text.return_value = json.dumps(content)
        blob_mock.bucket = bucket
        blob_mocks[name] = blob_mock

    def blob_side_effect(name: str) -> MagicMock:
        return blob_mocks[name]

    bucket.blob.side_effect = blob_side_effect
    return bucket


def _build_db(
    blobs: Mapping[str, object], source_blob_name: str, bucket_name: str = "test-bucket"
) -> GoogleJsonDb:
    bucket = _make_bucket(blobs)
    with patch("platzky.db.google_json_db.Client") as mock_client:
        mock_client.return_value.bucket.return_value = bucket
        return GoogleJsonDb(bucket_name, source_blob_name)


class TestGoogleJsonDbMultiFile:
    def test_nested_file_ref_two_levels(self):
        blobs = {
            "data/db.json": {
                "site_content": {"extra": {"$file": "level1.json"}, "logo_url": "/logo.png"}
            },
            "data/level1.json": {"deeper": {"$file": "level2.json"}},
            "data/level2.json": {"value": 42},
        }
        db = _build_db(blobs, "data/db.json")
        assert db.data["site_content"]["extra"]["deeper"]["value"] == 42
        assert db.data["site_content"]["logo_url"] == "/logo.png"

    def test_root_blob_sibling_ref(self):
        blobs = {
            "db.json": {"site_content": {"extra": {"$file": "extra.json"}}},
            "extra.json": {"value": 1},
        }
        db = _build_db(blobs, "db.json")
        assert db.data["site_content"]["extra"]["value"] == 1

    def test_cycle_detection_raises(self):
        blobs = {
            "data/db.json": {"site_content": {"loop": {"$file": "a.json"}}},
            "data/a.json": {"$file": "a.json"},
        }
        with pytest.raises(FileRefCycleError):
            _build_db(blobs, "data/db.json")

    def test_path_traversal_rejected(self):
        blobs = {
            "data/db.json": {"site_content": {"secret": {"$file": "../secret.json"}}},
            "secret.json": {"leak": True},
        }
        with pytest.raises(FileRefTraversalError):
            _build_db(blobs, "data/db.json")

    def test_path_traversal_rejected_at_bucket_root(self):
        blobs = {"db.json": {"site_content": {"secret": {"$file": "../secret.json"}}}}
        with pytest.raises(FileRefTraversalError):
            _build_db(blobs, "db.json")

    def test_absolute_file_ref_rejected(self):
        blobs = {"data/db.json": {"site_content": {"secret": {"$file": "/etc/passwd"}}}}
        with pytest.raises(FileRefTraversalError):
            _build_db(blobs, "data/db.json")

    def test_root_level_file_ref_rejected(self):
        blobs = {"db.json": {"$file": "other.json"}, "other.json": {"site_content": {}}}
        with pytest.raises(InvalidFileRefError):
            _build_db(blobs, "db.json")

    def test_duplicate_file_target_rejected(self):
        blobs = {
            "db.json": {
                "site_content": {"a": {"$file": "shared.json"}, "b": {"$file": "shared.json"}}
            },
            "shared.json": {"logo_url": "/logo.png"},
        }
        with pytest.raises(InvalidFileRefError):
            _build_db(blobs, "db.json")

    def test_list_element_file_ref_rejected(self):
        blobs = {
            "db.json": {"site_content": {"posts": [{"$file": "post1.json"}]}},
            "post1.json": {"slug": "post-1"},
        }
        with pytest.raises(InvalidFileRefError):
            _build_db(blobs, "db.json")
