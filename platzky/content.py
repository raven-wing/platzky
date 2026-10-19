"""How CMS-authored content is handed to the content transformers."""

from typing import Protocol

from markupsafe import Markup

from platzky.content_types import ContentType
from platzky.text_format import TextFormat


class ContentTransformer(Protocol):
    """Renders content of one type through the permitted transformers; see ``Engine``."""

    def __call__(
        self, content: str, content_type: ContentType, *, text_format: TextFormat
    ) -> Markup:
        """Render ``content``, written in ``text_format``, as ``content_type``."""
        ...
