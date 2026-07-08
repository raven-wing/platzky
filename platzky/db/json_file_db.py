"""Local file-based JSON database implementation, with multi-file JSON support."""

import json
import logging
import os
import tempfile
from pathlib import Path

from pydantic import Field

from platzky.db.db import DBConfig
from platzky.db.exceptions import FileRefTraversalError
from platzky.db.file_refs import (
    FileRefPath,
    FileRefs,
    JsonValue,
    ResolveLocation,
    resolve_file_refs,
)
from platzky.db.json_db import Json

logger = logging.getLogger(__name__)


class _Missing:
    """Sentinel type for a tracked tree path that no longer exists in the data."""


_MISSING = _Missing()


def db_config_type() -> type["JsonFileDbConfig"]:
    """Return the configuration class for JSON file database.

    Returns:
        JsonFileDbConfig class
    """
    return JsonFileDbConfig


class JsonFileDbConfig(DBConfig):
    """Configuration for JSON file database."""

    path: str = Field(alias="PATH")


def db_from_config(config: JsonFileDbConfig) -> "JsonFile":
    """Create a JSON file database instance from configuration.

    Args:
        config: JSON file database configuration

    Returns:
        Configured JSON file database instance
    """
    return JsonFile(config.path)


class JsonFile(Json):
    """JSON database stored in a local file, with read/write support.

    Supports splitting data across multiple files: any node of the form
    ``{"$file": "relative/path.json"}`` is replaced at load time with the
    parsed content of that file. Included files may themselves include
    further files. References must stay within the main file's directory
    and may only appear as dict values (not list elements, and not at the
    main file's own root), so each reference has a stable tree-path used to
    write its subtree back to the correct file on save.
    """

    def __init__(self, path: str) -> None:
        """Initialize JSON file database, resolving any `$file` references.

        Args:
            path: Absolute or relative path to the main JSON file
        """
        self.data_file_path = path
        main_location = os.path.realpath(path)
        with open(path) as json_file:
            raw_data: JsonValue = json.load(json_file)
        resolved_data, file_refs = resolve_file_refs(
            raw_data,
            main_location=main_location,
            resolve_location=_local_resolve_location(main_location),
            base_of=os.path.dirname,
            load=_local_load,
        )
        assert isinstance(resolved_data, dict), "main JSON file must contain an object"
        super().__init__(resolved_data)
        self._file_refs = file_refs
        self.module_name = "json_file_db"
        self.db_name = "JsonFileDb"

    def __save_file(self) -> None:
        _atomic_write_json(self.data_file_path, _sparse_copy(self.data, (), (), self._file_refs))
        for ref_path, (abs_path, _raw_ref) in self._file_refs.items():
            value = _get_at(self.data, ref_path)
            if isinstance(value, _Missing):
                logger.warning("Tracked path %s missing; leaving %s untouched", ref_path, abs_path)
                continue
            _atomic_write_json(abs_path, _sparse_copy(value, ref_path, ref_path, self._file_refs))

    def add_comment(self, author_name: str, comment: str, post_slug: str) -> None:
        """Add a comment to a blog post and persist to file.

        Args:
            author_name: Name of the comment author
            comment: Comment text content
            post_slug: URL-friendly identifier of the post
        """
        super().add_comment(author_name, comment, post_slug)
        self.__save_file()


def _local_resolve_location(main_location: str) -> ResolveLocation:
    """Build a `resolve_location` callback confined to the main file's directory.

    Args:
        main_location: Realpath of the main JSON file.

    Returns:
        A callable resolving `(base_dir, raw_ref)` to an absolute path.
    """
    main_dir = os.path.dirname(main_location)

    def resolve(base_dir: str, raw_ref: str) -> str:
        """Resolve `raw_ref` against `base_dir`, confined to `main_dir`."""
        if os.path.isabs(raw_ref):
            raise FileRefTraversalError(f"$file value {raw_ref!r} must not be absolute")
        candidate = os.path.realpath(os.path.join(base_dir, raw_ref))
        if not Path(candidate).is_relative_to(Path(main_dir)):
            raise FileRefTraversalError(f"$file value {raw_ref!r} escapes {main_dir!r}")
        return candidate

    return resolve


def _local_load(location: str) -> JsonValue:
    """Read and parse a local JSON file.

    Args:
        location: Absolute path to the file.

    Returns:
        Parsed JSON content.
    """
    with open(location) as included_file:
        return json.load(included_file)


def _get_at(data: dict[str, JsonValue], path: FileRefPath) -> JsonValue | _Missing:
    """Fetch the value at a dict-key path, freshly re-walking from the root.

    Args:
        data: Root mapping to walk.
        path: Sequence of dict keys locating the value.

    Returns:
        The value at `path`, or the module's `_MISSING` sentinel if any key
        along the way is absent or a non-dict is encountered before the end.
    """
    current: JsonValue = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return _MISSING
        current = current[key]
    return current


def _sparse_copy(
    node: JsonValue, path: FileRefPath, root_path: FileRefPath, file_refs: FileRefs
) -> JsonValue:
    """Deep-copy `node`, replacing nested tracked subtrees with `$file` markers.

    Reconstructs what should be written to disk for the file rooted at
    `root_path`: its own content is copied in full, but any deeper subtree
    that came from (and belongs to) a different included file is collapsed
    back into a `{"$file": ...}` reference instead of being inlined.

    Args:
        node: Current subtree being copied.
        path: Tree path of `node` from the database root.
        root_path: Tree path of the file currently being serialized.
        file_refs: Provenance map from `JsonFile._file_refs`.

    Returns:
        A JSON-serializable copy of `node` with nested included subtrees
        collapsed back to their `$file` reference form.
    """
    if path != root_path and path in file_refs:
        _, raw_ref = file_refs[path]
        return {"$file": raw_ref}
    if isinstance(node, dict):
        return {
            key: _sparse_copy(value, (*path, key), root_path, file_refs)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [_sparse_copy(item, path, root_path, file_refs) for item in node]
    return node


def _atomic_write_json(path: str, data: JsonValue) -> None:
    """Write `data` as JSON to `path` atomically via a same-directory temp file.

    Args:
        path: Destination file path.
        data: JSON-serializable data to write.
    """
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as tmp_file:
            json.dump(data, tmp_file)
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
