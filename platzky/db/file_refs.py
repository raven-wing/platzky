"""Storage-agnostic resolution of `{"$file": ...}` reference nodes.

Shared by any JSON-backed `DB` that wants to split its data across multiple
files: `JsonFile` (local filesystem) and `GoogleJsonDb` (Google Cloud Storage)
each supply their own notion of "location" (a local path vs. a GCS blob
name), how to resolve+validate a reference against it, and how to load the
referenced content; the tree walk, cycle guard, and reference-shape rules are
identical for both and live here once.
"""

from collections.abc import Callable

from platzky.db.exceptions import FileRefCycleError, InvalidFileRefError

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
FileRefPath = tuple[str, ...]
FileRefs = dict[FileRefPath, tuple[str, str]]

ResolveLocation = Callable[[str, str], str]
BaseOf = Callable[[str], str]
Load = Callable[[str], JsonValue]


def resolve_file_refs(
    root: JsonValue,
    *,
    main_location: str,
    resolve_location: ResolveLocation,
    base_of: BaseOf,
    load: Load,
) -> tuple[JsonValue, FileRefs]:
    """Recursively resolve `$file` reference nodes in a parsed JSON tree.

    Args:
        root: The parsed content of the main document.
        main_location: Canonical location of the main document (e.g. a
            realpath or a blob name), used to seed the cycle guard.
        resolve_location: Given `(base_location, raw_ref)`, returns the
            canonical location the reference points to, or raises a
            `FileRefTraversalError` if it is invalid (absolute, escapes the
            allowed area, etc).
        base_of: Given a canonical location, returns the location further
            `$file` values nested inside it should resolve against (e.g. a
            directory or key prefix).
        load: Given a canonical location, returns its parsed JSON content.

    Returns:
        A tuple of the tree with all `$file` nodes replaced by their
        resolved content, and a provenance map from tree-path to
        `(canonical_location, original_raw_ref)` for every reference found.
    """
    file_refs: FileRefs = {}
    resolved = _resolve_node(
        root,
        base_location=base_of(main_location),
        seen=frozenset({main_location}),
        path=(),
        file_refs=file_refs,
        resolve_location=resolve_location,
        base_of=base_of,
        load=load,
    )
    return resolved, file_refs


def _resolve_node(
    node: JsonValue,
    *,
    base_location: str,
    seen: frozenset[str],
    path: FileRefPath,
    file_refs: FileRefs,
    resolve_location: ResolveLocation,
    base_of: BaseOf,
    load: Load,
    within_list: bool = False,
) -> JsonValue:
    """Recursively resolve `$file` nodes, delegating storage specifics to callbacks.

    Args:
        node: Current subtree being walked.
        base_location: Location relative `$file` values in this subtree resolve against.
        seen: Canonical locations currently open in the include chain (cycle guard).
        path: Tree path (dict keys) from the document root to this node.
        file_refs: Provenance map being populated as references are resolved.
        resolve_location: See `resolve_file_refs`.
        base_of: See `resolve_file_refs`.
        load: See `resolve_file_refs`.
        within_list: Whether this node is nested (at any depth) inside a list, in
            which case `$file` is rejected since list-index provenance is unstable.

    Returns:
        The subtree with any `$file` nodes replaced by their resolved content.

    Raises:
        InvalidFileRefError: A `$file` node is malformed, nested under a list, at
            the document's root, or duplicates another reference's target.
        FileRefCycleError: The include chain revisits a location already open.
        FileRefTraversalError: A `$file` value is rejected by `resolve_location`.
    """
    if isinstance(node, dict):
        if "$file" in node:
            if within_list:
                raise InvalidFileRefError(f"$file is not allowed inside a list (at {path!r})")
            if len(node) != 1:
                raise InvalidFileRefError(f"$file must be the only key in its object (at {path!r})")
            if path == ():
                raise InvalidFileRefError("$file is not allowed at the document's root")
            raw_ref = node["$file"]
            if not isinstance(raw_ref, str):
                raise InvalidFileRefError(f"$file value must be a string (at {path!r})")
            candidate = resolve_location(base_location, raw_ref)
            if candidate in seen:
                raise FileRefCycleError(
                    f"$file cycle at {path!r}: {candidate!r} is already being resolved"
                )
            for existing_path, (existing_loc, _existing_raw) in file_refs.items():
                if existing_loc == candidate:
                    raise InvalidFileRefError(
                        f"$file target {candidate!r} at {path!r} "
                        f"duplicates ref at {existing_path!r}"
                    )
            content = load(candidate)
            resolved = _resolve_node(
                content,
                base_location=base_of(candidate),
                seen=seen | {candidate},
                path=path,
                file_refs=file_refs,
                resolve_location=resolve_location,
                base_of=base_of,
                load=load,
            )
            file_refs[path] = (candidate, raw_ref)
            return resolved
        return {
            key: _resolve_node(
                value,
                base_location=base_location,
                seen=seen,
                path=(*path, key),
                file_refs=file_refs,
                resolve_location=resolve_location,
                base_of=base_of,
                load=load,
                within_list=within_list,
            )
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [
            _resolve_node(
                item,
                base_location=base_location,
                seen=seen,
                path=path,
                file_refs=file_refs,
                resolve_location=resolve_location,
                base_of=base_of,
                load=load,
                within_list=True,
            )
            for item in node
        ]
    return node
