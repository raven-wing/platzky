"""The source of CMS-authored content, and how it is handed to the renderer."""

from dataclasses import dataclass
from typing import Protocol

from markupsafe import Markup

from platzky.content_types import ContentType
from platzky.text_format import TextFormat


@dataclass(frozen=True)
class ContentSource:
    """Content as someone with CMS write access wrote it, before it is rendered.

    Passing one to ``transform_content`` is the caller's declaration of *provenance*, not
    a claim that the text is harmless — the caller is the only party that knows where
    content came from, so only the caller can say. It buys three things: the text is
    formatted and embedded rather than escaped, its author is held to strict shortcode
    syntax so their own mistakes are reported to them, and ``STRIP_CONTENT_HTML`` has
    authored HTML to strip. Anything else — a plain ``str``, or a bare ``Markup`` from
    elsewhere — is treated as written by a stranger: escaped at the boundary, and parsed
    leniently so a typo cannot take a page down.

    Not ``Markup``, so a template cannot render it without going through the renderer.
    Wrapping visitor input in it is how a cross-site scripting hole gets made, which is
    why each use in platzky names the author it is vouching for.

    Attributes:
        text: The text as the author wrote it, shortcodes and all.
        text_format: The format it is written in, e.g. ``MARKDOWN``.
    """

    text: str
    text_format: TextFormat


class ContentTransformer(Protocol):
    """Renders content of one type through the permitted transformers; see ``Engine``."""

    def __call__(self, content: ContentSource | str, content_type: ContentType) -> Markup:
        """Render ``content`` as ``content_type``; a plain ``str`` is escaped first."""
        ...
