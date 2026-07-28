import json
from pathlib import Path
from typing import Any

import pytest

from platzky.db.blog_storage import BlogStorage
from platzky.db.document_blog_storage import DocumentBlogStorage
from platzky.db.exceptions import DBError, NotFoundError, ReadOnlyStorageError
from platzky.db.json_stores import FileStore, JsonStore, MemoryStore, ReadOnlyStore


def sample_data() -> dict[str, Any]:
    return {
        "site_content": {
            "posts": [
                {
                    "slug": "post-1",
                    "author": "Author",
                    "title": "Title",
                    "contentInMarkdown": "content",
                    "excerpt": "excerpt",
                    "language": "en",
                    "tags": ["python"],
                    "comments": [],
                },
                {
                    "slug": "post-2",
                    "author": "Author",
                    "title": "Title 2",
                    "contentInMarkdown": "content 2",
                    "excerpt": "excerpt 2",
                    "language": "pl",
                    "tags": [],
                    "comments": [],
                },
            ],
            "pages": [
                {
                    "slug": "page-1",
                    "author": "Author",
                    "title": "Page title",
                    "contentInMarkdown": "page content",
                    "excerpt": "page excerpt",
                    "language": "en",
                }
            ],
        },
        "plugins": {
            "my_plugin": {"is_active": True, "config": {"key": "value"}},
        },
    }


def _memory_store(data: dict[str, Any], _tmp_path: Path) -> JsonStore:
    return MemoryStore(data)


def _file_store(data: dict[str, Any], tmp_path: Path) -> JsonStore:
    path = tmp_path / "data.json"
    path.write_text(json.dumps(data))
    return FileStore(str(path))


@pytest.fixture(params=[_memory_store, _file_store], ids=["MemoryStore", "FileStore"])
def store(request: pytest.FixtureRequest, tmp_path: Path) -> JsonStore:
    return request.param(sample_data(), tmp_path)


@pytest.fixture
def storage(store: JsonStore) -> DocumentBlogStorage:
    return DocumentBlogStorage(store)


class TestPosts:
    def test_get_returns_matching_post(self, storage: DocumentBlogStorage):
        post = storage.posts.get("post-1")
        assert post.slug == "post-1"
        assert post.title == "Title"

    def test_get_raises_not_found_for_unknown_slug(self, storage: DocumentBlogStorage):
        with pytest.raises(NotFoundError):
            storage.posts.get("missing")

    def test_get_raises_not_found_when_posts_key_missing(self):
        storage = DocumentBlogStorage(MemoryStore({"site_content": {}}))
        with pytest.raises(NotFoundError):
            storage.posts.get("post-1")

    def test_get_all_filters_by_language(self, storage: DocumentBlogStorage):
        posts = storage.posts.get_all("en")
        assert [p.slug for p in posts] == ["post-1"]

    def test_get_by_tag_filters_by_tag_and_language(self, storage: DocumentBlogStorage):
        posts = storage.posts.get_by_tag("python", "en")
        assert [p.slug for p in posts] == ["post-1"]

    def test_get_by_tag_excludes_other_language(self, storage: DocumentBlogStorage):
        assert storage.posts.get_by_tag("python", "pl") == []

    def test_add_comment_persists_and_is_visible_via_get(self, storage: DocumentBlogStorage):
        storage.posts.add_comment("Alice", "Nice post!", "post-1")
        post = storage.posts.get("post-1")
        assert len(post.comments) == 1
        assert post.comments[0].author == "Alice"
        assert post.comments[0].comment == "Nice post!"

    def test_add_comment_raises_not_found_for_unknown_slug(self, storage: DocumentBlogStorage):
        with pytest.raises(NotFoundError):
            storage.posts.add_comment("Alice", "Nice post!", "missing")

    def test_add_comment_rolls_back_on_save_failure(self):
        data = sample_data()
        storage = DocumentBlogStorage(ReadOnlyStore(data))

        with pytest.raises(ReadOnlyStorageError):
            storage.posts.add_comment("Alice", "Nice post!", "post-1")

        assert storage.data["site_content"]["posts"][0]["comments"] == []

    def test_add_comment_rollback_removes_comments_key_if_it_was_absent(self):
        data = sample_data()
        del data["site_content"]["posts"][0]["comments"]
        storage = DocumentBlogStorage(ReadOnlyStore(data))

        with pytest.raises(ReadOnlyStorageError):
            storage.posts.add_comment("Alice", "Nice post!", "post-1")

        assert "comments" not in storage.data["site_content"]["posts"][0]


class TestPages:
    def test_get_returns_matching_page(self, storage: DocumentBlogStorage):
        page = storage.pages.get("page-1")
        assert page.slug == "page-1"

    def test_get_raises_not_found_for_unknown_slug(self, storage: DocumentBlogStorage):
        with pytest.raises(NotFoundError):
            storage.pages.get("missing")

    def test_get_raises_not_found_when_pages_key_missing(self):
        storage = DocumentBlogStorage(MemoryStore({"site_content": {}}))
        with pytest.raises(NotFoundError):
            storage.pages.get("page-1")


class TestPlugins:
    def test_get_all_returns_validated_configs(self, storage: DocumentBlogStorage):
        plugins = storage.plugins.get_all()
        assert plugins["my_plugin"].is_active is True
        assert plugins["my_plugin"].config == {"key": "value"}

    def test_get_all_returns_empty_dict_when_missing(self):
        storage = DocumentBlogStorage(MemoryStore({"site_content": {}}))
        assert storage.plugins.get_all() == {}


class TestSharedDocument:
    def test_site_content_missing_raises_db_error(self):
        storage = DocumentBlogStorage(MemoryStore({}))
        with pytest.raises(DBError):
            storage.posts.get_all("en")


def test_document_blog_storage_satisfies_blog_storage_protocol(
    storage: DocumentBlogStorage,
) -> None:
    """Structural check: pyright rejects this assignment if the shape drifts."""
    conforms: BlogStorage = storage
    assert conforms is storage
