"""Google Cloud Storage-based JSON database implementation."""

import json
import posixpath
from typing import TYPE_CHECKING, Any

from google.cloud.storage import Client
from pydantic import Field

from platzky.db.db import DBConfig
from platzky.db.exceptions import FileRefTraversalError
from platzky.db.file_refs import JsonValue, Load, ResolveLocation, resolve_file_refs
from platzky.db.json_db import Json

if TYPE_CHECKING:
    from google.cloud.storage import Blob, Bucket


def db_config_type() -> type["GoogleJsonDbConfig"]:
    """Return the configuration class for Google Cloud Storage JSON database.

    Returns:
        GoogleJsonDbConfig class
    """
    return GoogleJsonDbConfig


class GoogleJsonDbConfig(DBConfig):
    """Configuration for Google Cloud Storage JSON database connection."""

    bucket_name: str = Field(alias="BUCKET_NAME")
    source_blob_name: str = Field(alias="SOURCE_BLOB_NAME")


def db_from_config(config: GoogleJsonDbConfig) -> "GoogleJsonDb":
    """Create a Google Cloud Storage JSON database instance from configuration.

    Args:
        config: Google Cloud Storage JSON database configuration

    Returns:
        Configured Google Cloud Storage JSON database instance
    """
    return GoogleJsonDb(config.bucket_name, config.source_blob_name)


def get_blob(bucket_name: str, source_blob_name: str) -> "Blob":
    """Retrieve a blob from Google Cloud Storage.

    Args:
        bucket_name: Name of the GCS bucket
        source_blob_name: Name of the blob/file in the bucket

    Returns:
        GCS Blob object
    """
    storage_client = Client()
    bucket = storage_client.bucket(bucket_name)
    return bucket.blob(source_blob_name)


def get_data(blob: "Blob") -> dict[str, Any]:
    """Download and parse JSON data from a blob.

    Args:
        blob: GCS Blob object to download from

    Returns:
        Parsed JSON data as dictionary
    """
    raw_data = blob.download_as_text()
    return json.loads(raw_data)


class GoogleJsonDb(Json):
    """JSON database stored in Google Cloud Storage.

    Supports splitting data across multiple blobs: any node of the form
    ``{"$file": "relative/blob-name.json"}`` is replaced at load time with
    the parsed content of that blob in the same bucket. References must stay
    within the main blob's key prefix and may only appear as dict values
    (not list elements, and not at the main blob's own root). Read-only:
    mutations are not written back to Cloud Storage (matching the existing
    behavior of this backend).
    """

    def __init__(self, bucket_name: str, source_blob_name: str) -> None:
        """Initialize Google Cloud Storage JSON database connection.

        Args:
            bucket_name: Name of the GCS bucket
            source_blob_name: Name of the blob/file in the bucket
        """
        self.bucket_name = bucket_name
        self.source_blob_name = source_blob_name

        self.blob = get_blob(self.bucket_name, self.source_blob_name)
        raw_data = get_data(self.blob)

        resolved_data, _file_refs = resolve_file_refs(
            raw_data,
            main_location=source_blob_name,
            resolve_location=_gcs_resolve_location(posixpath.dirname(source_blob_name)),
            base_of=posixpath.dirname,
            load=_gcs_load(self.blob.bucket),
        )
        assert isinstance(resolved_data, dict), "main blob must contain a JSON object"
        super().__init__(resolved_data)

        self.module_name = "google_json_db"
        self.db_name = "GoogleJsonDb"


def _contained(candidate: str, root_prefix: str) -> bool:
    """Check whether `candidate` stays within `root_prefix`'s blob-name tree.

    Args:
        candidate: A `posixpath.normpath`-ed candidate blob name.
        root_prefix: The key prefix references must stay within; `""` means
            the main blob lives at the bucket's top level.

    Returns:
        True if `candidate` is `root_prefix` itself or nested under it.
    """
    if root_prefix == "":
        return candidate != ".." and not candidate.startswith("../")
    return candidate == root_prefix or candidate.startswith(root_prefix + "/")


def _gcs_resolve_location(main_prefix: str) -> ResolveLocation:
    """Build a `resolve_location` callback confined to the main blob's key prefix.

    Args:
        main_prefix: Key prefix (directory-like portion) of the main blob name.

    Returns:
        A callable resolving `(base_prefix, raw_ref)` to a canonical blob name.
    """

    def resolve(base_prefix: str, raw_ref: str) -> str:
        """Resolve `raw_ref` against `base_prefix`, confined to `main_prefix`."""
        if posixpath.isabs(raw_ref):
            raise FileRefTraversalError(f"$file value {raw_ref!r} must not be absolute")
        candidate = posixpath.normpath(posixpath.join(base_prefix, raw_ref))
        if not _contained(candidate, main_prefix):
            raise FileRefTraversalError(f"$file value {raw_ref!r} escapes {main_prefix!r}")
        return candidate

    return resolve


def _gcs_load(bucket: "Bucket") -> Load:
    """Build a `load` callback fetching JSON blobs from `bucket`.

    Args:
        bucket: The GCS bucket the main blob (and its references) live in.

    Returns:
        A callable fetching and parsing a blob by name.
    """

    def load(blob_name: str) -> JsonValue:
        """Fetch and parse `blob_name` from `bucket`."""
        return get_data(bucket.blob(blob_name))

    return load
