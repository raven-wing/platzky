"""Exceptions raised by database implementations."""


class DBError(Exception):
    """Base class for all database errors."""


class NotFoundError(DBError, ValueError):
    """Requested content does not exist in the database.

    Inherits from ValueError for backward compatibility with code that
    catches ValueError; that base will be dropped in the next major release.
    """


class InvalidFileRefError(DBError):
    """A ``{"$file": ...}`` reference in a multi-file JSON database is malformed.

    Covers a non-string or sibling-key ``$file`` value, a ``$file`` node found
    as a list element, a bare ``$file`` at the main file's root, and two tree
    paths resolving to the same physical file.
    """


class FileRefCycleError(InvalidFileRefError):
    """A ``$file`` reference chain includes a file already being resolved."""


class FileRefTraversalError(InvalidFileRefError):
    """A ``$file`` reference resolves to a path outside the main file's directory."""
