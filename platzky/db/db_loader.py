"""Dynamic database module loader based on configuration type."""

import importlib
import pkgutil
import types

from platzky.db.db import DB, DBConfig
from platzky.db.exceptions import UnknownDBTypeError

_BACKEND_SUFFIX = "_db"


def get_db(db_config: DBConfig) -> DB:
    """Load and initialise the database backend specified in *db_config*."""
    db_name = db_config.type
    db = get_db_module(db_name)
    return db.db_from_config(db_config)


def available_db_types() -> list[str]:
    """List the database backends shipped in the platzky.db package.

    Returns:
        Sorted values accepted as ``DB.TYPE``, derived from the ``*_db`` modules of the package.
    """
    parent_module_name = ".".join(__name__.split(".")[:-1])
    parent = importlib.import_module(parent_module_name)
    return sorted(
        module.name.removesuffix(_BACKEND_SUFFIX)
        for module in pkgutil.iter_modules(parent.__path__)
        if module.name.endswith(_BACKEND_SUFFIX)
    )


def get_db_module(db_type: str) -> types.ModuleType:
    """Import the db module for db_type from the platzky.db package.

    The type is checked against the available backends before importing, so a
    ModuleNotFoundError raised for a missing third-party dependency inside a valid
    backend is never mistaken for an unknown type.

    Args:
        db_type: Name of the db module, without the ``_db`` suffix.

    Returns:
        The imported db module.

    Raises:
        UnknownDBTypeError: If db_type is not an available backend.
    """
    available = available_db_types()
    if db_type not in available:
        raise UnknownDBTypeError(
            f"Unknown DB type {db_type!r}; available types: {', '.join(available)}"
        )
    parent_module_name = ".".join(__name__.split(".")[:-1])
    return importlib.import_module(f"{parent_module_name}.{db_type}{_BACKEND_SUFFIX}")
