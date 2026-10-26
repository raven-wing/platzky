import importlib
from types import ModuleType
from typing import cast
from unittest.mock import MagicMock, mock_open, patch

import pytest

from platzky.config import Config
from platzky.db import db_loader
from platzky.db.exceptions import UnknownDBTypeError
from platzky.db.json_db import Json


def test_loading_json_db_dynamically():
    config_data = {
        "APP_NAME": "testingApp",
        "SECRET_KEY": "secret",
        "DB": {"TYPE": "json", "DATA": {}},
    }

    config = Config.model_validate(config_data)

    db = db_loader.get_db(config.db)
    assert db.__class__.__name__ == "Json"


def test_loading_json_file_db_dynamically():
    config_data = {
        "APP_NAME": "testingApp",
        "SECRET_KEY": "secret",
        "DB": {
            "TYPE": "json_file",
            "PATH": "some/path",
        },
    }

    config = Config.model_validate(config_data)

    with patch("builtins.open", mock_open(read_data="data")):
        with patch("json.load", return_value={"site_content": {}}):
            db = db_loader.get_db(config.db)
            assert db.__class__.__name__ == "JsonFile"
            assert hasattr(db, "data")
            assert cast(Json, db).data == {"site_content": {}}


def test_loading_google_json_db_dynamically():
    config_data = {
        "APP_NAME": "testingApp",
        "SECRET_KEY": "secret",
        "DB": {
            "TYPE": "google_json",
            "BUCKET_NAME": "bucket-name",
            "SOURCE_BLOB_NAME": "data.json",
        },
    }

    expected_data = {"site_content": {}}

    with patch("platzky.db.google_json_db.Client") as mock_client:
        client_mock = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        client_mock.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.download_as_text.return_value = '{"site_content": {}}'

        mock_client.return_value = client_mock

        config = Config.model_validate(config_data)
        db = db_loader.get_db(config.db)

        assert db.__class__.__name__ == "GoogleJsonDb"
        assert hasattr(db, "data")
        assert cast(Json, db).data == expected_data

        mock_client.assert_called_once()
        mock_bucket.blob.assert_called_once_with("data.json")
        mock_blob.download_as_text.assert_called_once()


def test_loading_graph_db_dynamically():
    config_data = {
        "APP_NAME": "testingApp",
        "SECRET_KEY": "secret",
        "DB": {
            "TYPE": "graph_ql",
            "CMS_ENDPOINT": "http://localhost:1337/graphql",
            "CMS_TOKEN": "token",
        },
    }

    config = Config.model_validate(config_data)
    db = db_loader.get_db(config.db)
    assert db.__class__.__name__ == "GraphQL"


def test_unknown_db_type_names_type_and_lists_backends():
    with pytest.raises(UnknownDBTypeError) as exc_info:
        db_loader.get_db_module("nosuch")

    message = str(exc_info.value)
    assert "'nosuch'" in message
    for backend in ("json", "json_file", "google_json", "github_json", "graph_ql", "mongodb"):
        assert backend in message
    assert isinstance(exc_info.value, ValueError)


def test_known_db_type_still_loads_module():
    module = db_loader.get_db_module("json_file")
    assert module.__name__ == "platzky.db.json_file_db"


def test_missing_dependency_inside_backend_is_not_reported_as_unknown_type():
    real_import_module = importlib.import_module

    def import_module(name: str) -> ModuleType:
        if name == "platzky.db.mongodb_db":
            raise ModuleNotFoundError("No module named 'pymongo'", name="pymongo")
        return real_import_module(name)

    with patch("platzky.db.db_loader.importlib.import_module", side_effect=import_module):
        with pytest.raises(ModuleNotFoundError) as exc_info:
            db_loader.get_db_module("mongodb")

    assert not isinstance(exc_info.value, UnknownDBTypeError)
    assert exc_info.value.name == "pymongo"


@pytest.mark.parametrize("db_type", ["../x", "json_file.x", ""])
def test_odd_db_type_is_reported_as_unknown(db_type: str):
    with pytest.raises(UnknownDBTypeError, match="available types"):
        db_loader.get_db_module(db_type)
