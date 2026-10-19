"""How CMS-authored content is handed to the content transformers."""

from collections.abc import Callable
from typing import Protocol

from markupsafe import Markup

from platzky.content_types import ContentType


class ContentTransformer(Protocol):
    """Renders content of one type through the permitted transformers; see ``Engine``."""

    def __call__(
        self, content: str, content_type: ContentType, *, format_text: Callable[[str, bool], str]
    ) -> Markup:
        """Render ``content`` as ``content_type``, its text formatted by ``format_text``."""
        ...
