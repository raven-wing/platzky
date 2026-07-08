import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from platzky.db.exceptions import FileRefCycleError, FileRefTraversalError, InvalidFileRefError
from platzky.db.json_file_db import JsonFile, JsonFileDbConfig, db_from_config


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data))


class TestJsonFileDb:
    @pytest.fixture
    def sample_data(self) -> dict[str, Any]:
        return {
            "site_content": {
                "app_description": {"en": "English description", "de": "Deutsche Beschreibung"},
                "posts": [
                    {
                        "title": "Post 1",
                        "slug": "post-1",
                        "content": "Post content",
                        "author": "Author 1",
                        "contentInMarkdown": "# Post 1",
                        "excerpt": "Post 1 excerpt",
                        "comments": [],
                        "tags": ["tag1", "tag2"],
                        "language": "en",
                        "coverImage": {"url": "/images/post1.jpg"},
                        "date": "2023-01-01T00:00:00",
                    }
                ],
                "logo_url": "/logo.png",
            }
        }

    @pytest.fixture
    def db_path(self, tmp_path: Path, sample_data: dict[str, Any]) -> str:
        path = tmp_path / "data.json"
        _write_json(path, sample_data)
        return str(path)

    def test_init_loads_data(self, sample_data: dict[str, Any], db_path: str):
        db = JsonFile(db_path)
        assert db.data == sample_data
        assert db.module_name == "json_file_db"
        assert db.db_name == "JsonFileDb"

    def test_get_app_description(self, db_path: str):
        db = JsonFile(db_path)
        assert db.get_app_description("en") == "English description"
        assert db.get_app_description("de") == "Deutsche Beschreibung"
        assert db.get_app_description("fr") == ""

    def test_add_comment_saves_file(self, db_path: str):
        test_date = datetime(2023, 2, 1, 10, 0)
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = test_date
            db = JsonFile(db_path)
            db.add_comment("Test User", "New comment", "post-1")

        comments = db.data["site_content"]["posts"][0]["comments"]
        assert len(comments) == 1
        assert comments[0]["author"] == "Test User"
        assert comments[0]["comment"] == "New comment"

        on_disk = json.loads(Path(db_path).read_text())
        assert on_disk["site_content"]["posts"][0]["comments"] == comments

    def test_init_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            JsonFile(str(tmp_path / "missing.json"))

    def test_malformed_json_file(self, tmp_path: Path):
        path = tmp_path / "data.json"
        path.write_text("This is not valid JSON")
        with pytest.raises(json.JSONDecodeError):
            JsonFile(str(path))

    def test_json_file_db_config(self):
        config_dict = {"PATH": "/path/to/data.json", "TYPE": "json_file"}
        config = JsonFileDbConfig.model_validate(config_dict)
        assert config.path == "/path/to/data.json"
        assert config.type == "json_file"

    def test_db_from_config(self, db_path: str):
        config = JsonFileDbConfig(TYPE="json_file", PATH=db_path)
        db = db_from_config(config)
        assert isinstance(db, JsonFile)
        assert db.data_file_path == db_path

    def test_get_all_posts(self, db_path: str):
        db = JsonFile(db_path)
        posts = db.get_all_posts("en")
        assert len(posts) == 1
        assert posts[0].title == "Post 1"
        assert posts[0].slug == "post-1"

    def test_get_post(self, db_path: str):
        db = JsonFile(db_path)
        post = db.get_post("post-1")
        assert post.title == "Post 1"
        assert post.slug == "post-1"

    def test_get_post_not_found(self, db_path: str):
        db = JsonFile(db_path)
        with pytest.raises(ValueError):
            db.get_post("non-existent")

    def test_single_file_db_unchanged(self, tmp_path: Path, sample_data: dict[str, Any]):
        path = tmp_path / "data.json"
        _write_json(path, sample_data)
        db = JsonFile(str(path))
        db.add_comment("Author", "Hello", "post-1")

        on_disk = json.loads(path.read_text())
        assert on_disk["site_content"]["logo_url"] == "/logo.png"
        assert len(on_disk["site_content"]["posts"][0]["comments"]) == 1

    def test_nested_file_ref_two_levels(self, tmp_path: Path):
        _write_json(tmp_path / "level2.json", {"value": 42})
        _write_json(tmp_path / "level1.json", {"deeper": {"$file": "level2.json"}})
        _write_json(
            tmp_path / "data.json",
            {"site_content": {"extra": {"$file": "level1.json"}, "logo_url": "/logo.png"}},
        )

        db = JsonFile(str(tmp_path / "data.json"))
        assert db.data["site_content"]["extra"]["deeper"]["value"] == 42

    def test_cycle_detection_raises(self, tmp_path: Path):
        _write_json(tmp_path / "a.json", {"$file": "a.json"})
        _write_json(tmp_path / "data.json", {"site_content": {"loop": {"$file": "a.json"}}})

        with pytest.raises(FileRefCycleError):
            JsonFile(str(tmp_path / "data.json"))

    def test_path_traversal_rejected(self, tmp_path: Path):
        outside_dir = tmp_path.parent / f"{tmp_path.name}-outside"
        outside_dir.mkdir(exist_ok=True)
        _write_json(outside_dir / "secret.json", {"leak": True})

        data_dir = tmp_path / "data_dir"
        data_dir.mkdir()
        _write_json(
            data_dir / "data.json",
            {"site_content": {"secret": {"$file": f"../../{outside_dir.name}/secret.json"}}},
        )

        with pytest.raises(FileRefTraversalError):
            JsonFile(str(data_dir / "data.json"))

    def test_absolute_file_ref_rejected(self, tmp_path: Path):
        _write_json(
            tmp_path / "data.json",
            {"site_content": {"secret": {"$file": "/etc/passwd"}}},
        )

        with pytest.raises(FileRefTraversalError):
            JsonFile(str(tmp_path / "data.json"))

    def test_symlink_escape_rejected(self, tmp_path: Path):
        outside_dir = tmp_path.parent / f"{tmp_path.name}-outside-symlink"
        outside_dir.mkdir(exist_ok=True)
        _write_json(outside_dir / "secret.json", {"leak": True})

        data_dir = tmp_path / "data_dir"
        data_dir.mkdir()
        os.symlink(outside_dir / "secret.json", data_dir / "link.json")
        _write_json(
            data_dir / "data.json",
            {"site_content": {"secret": {"$file": "link.json"}}},
        )

        with pytest.raises(FileRefTraversalError):
            JsonFile(str(data_dir / "data.json"))

    def test_root_level_file_ref_rejected(self, tmp_path: Path):
        _write_json(tmp_path / "other.json", {"site_content": {}})
        _write_json(tmp_path / "data.json", {"$file": "other.json"})

        with pytest.raises(InvalidFileRefError):
            JsonFile(str(tmp_path / "data.json"))

    def test_duplicate_file_target_rejected(self, tmp_path: Path):
        _write_json(tmp_path / "shared.json", {"logo_url": "/logo.png"})
        _write_json(
            tmp_path / "data.json",
            {"site_content": {"a": {"$file": "shared.json"}, "b": {"$file": "shared.json"}}},
        )

        with pytest.raises(InvalidFileRefError):
            JsonFile(str(tmp_path / "data.json"))

    def test_list_element_file_ref_rejected(self, tmp_path: Path):
        _write_json(tmp_path / "post1.json", {"slug": "post-1"})
        _write_json(
            tmp_path / "data.json",
            {"site_content": {"posts": [{"$file": "post1.json"}]}},
        )

        with pytest.raises(InvalidFileRefError):
            JsonFile(str(tmp_path / "data.json"))

    def test_file_ref_nested_inside_list_rejected(self, tmp_path: Path):
        _write_json(tmp_path / "cover.json", {"url": "/img.png"})
        _write_json(
            tmp_path / "data.json",
            {
                "site_content": {
                    "posts": [{"slug": "post-1", "coverImage": {"$file": "cover.json"}}]
                }
            },
        )

        with pytest.raises(InvalidFileRefError):
            JsonFile(str(tmp_path / "data.json"))

    def test_add_comment_multi_file_writes_correct_file(self, tmp_path: Path):
        posts = [
            {
                "title": "Post 1",
                "slug": "post-1",
                "content": "Post content",
                "author": "Author 1",
                "contentInMarkdown": "# Post 1",
                "excerpt": "excerpt",
                "comments": [],
                "tags": [],
                "language": "en",
                "coverImage": {"url": "/img.png"},
                "date": "2023-01-01T00:00:00",
            }
        ]
        pages = [{"title": "About", "slug": "about", "content": "hi"}]
        _write_json(tmp_path / "posts.json", posts)
        _write_json(tmp_path / "pages.json", pages)
        _write_json(
            tmp_path / "data.json",
            {
                "site_content": {
                    "posts": {"$file": "posts.json"},
                    "pages": {"$file": "pages.json"},
                    "logo_url": "/logo.png",
                }
            },
        )

        db = JsonFile(str(tmp_path / "data.json"))
        db.add_comment("Author", "Nice post", "post-1")

        on_disk_main = json.loads((tmp_path / "data.json").read_text())
        assert on_disk_main["site_content"]["posts"] == {"$file": "posts.json"}
        assert on_disk_main["site_content"]["pages"] == {"$file": "pages.json"}
        assert on_disk_main["site_content"]["logo_url"] == "/logo.png"

        on_disk_posts = json.loads((tmp_path / "posts.json").read_text())
        assert len(on_disk_posts[0]["comments"]) == 1
        assert on_disk_posts[0]["comments"][0]["comment"] == "Nice post"

        on_disk_pages = json.loads((tmp_path / "pages.json").read_text())
        assert on_disk_pages == pages

    def test_save_missing_tracked_path_skips_without_deleting_file(self, tmp_path: Path):
        posts = [
            {
                "title": "Post 1",
                "slug": "post-1",
                "content": "Post content",
                "author": "Author 1",
                "contentInMarkdown": "# Post 1",
                "excerpt": "excerpt",
                "comments": [],
                "tags": [],
                "language": "en",
                "coverImage": {"url": "/img.png"},
                "date": "2023-01-01T00:00:00",
            }
        ]
        pages = [{"title": "About", "slug": "about", "content": "hi"}]
        _write_json(tmp_path / "posts.json", posts)
        _write_json(tmp_path / "pages.json", pages)
        _write_json(
            tmp_path / "data.json",
            {
                "site_content": {
                    "posts": {"$file": "posts.json"},
                    "pages": {"$file": "pages.json"},
                }
            },
        )

        db = JsonFile(str(tmp_path / "data.json"))
        del db.data["site_content"]["pages"]
        db.add_comment("Author", "Nice post", "post-1")

        assert (tmp_path / "pages.json").exists()
        assert json.loads((tmp_path / "pages.json").read_text()) == pages

    def test_no_leftover_temp_files_after_save(self, tmp_path: Path):
        posts = [
            {
                "title": "Post 1",
                "slug": "post-1",
                "content": "Post content",
                "author": "Author 1",
                "contentInMarkdown": "# Post 1",
                "excerpt": "excerpt",
                "comments": [],
                "tags": [],
                "language": "en",
                "coverImage": {"url": "/img.png"},
                "date": "2023-01-01T00:00:00",
            }
        ]
        _write_json(tmp_path / "posts.json", posts)
        _write_json(tmp_path / "data.json", {"site_content": {"posts": {"$file": "posts.json"}}})

        db = JsonFile(str(tmp_path / "data.json"))
        db.add_comment("Author", "Nice post", "post-1")

        leftover = [p for p in tmp_path.iterdir() if p.name.startswith(".tmp-")]
        assert leftover == []
