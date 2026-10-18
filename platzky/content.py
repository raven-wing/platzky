"""Bodies of CMS-authored content, and the format each is written in."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from markupsafe import Markup

from platzky.content_types import CmsAuthored, ContentType
from platzky.markdown import render_markdown


class ContentTransformer(Protocol):
    """Renders content of one type through the permitted transformers; see ``Engine``."""

    def __call__(
        self, content: str, content_type: ContentType, *, format_text: Callable[[str, bool], str]
    ) -> Markup:
        """Render ``content`` as ``content_type``, its text formatted by ``format_text``."""
        ...


@dataclass(frozen=True)
class Content(ABC):
    """A body of content written by someone with CMS write access, in some format."""

    text: str

    @abstractmethod
    def format_text(self, text: str, inline: bool) -> str:
        """Turn the author's text into HTML, before it is sanitized.

        Args:
            text: The author's text, with a placeholder tag where each shortcode goes.
            inline: Whether the text sits inside a shortcode element.

        Returns:
            HTML, still to be sanitized.
        """

    def to_html(self, transform: ContentTransformer, content_type: ContentType) -> Markup:
        """Render the content as safe HTML.

        Args:
            transform: Runs the shortcodes and filters permitted for ``content_type``.
            content_type: The kind of content, e.g. ``POST``.

        Returns:
            The rendered content, safe to embed.
        """
        # CmsAuthored vouches: a Content is only made from what a CMS author wrote.
        return transform(CmsAuthored(self.text), content_type, format_text=self.format_text)


class HtmlContent(Content):
    """Content written in HTML."""

    def format_text(self, text: str, inline: bool) -> str:  # noqa: ARG002
        """Return the text as it is; it is HTML already."""
        return text


class MarkdownContent(Content):
    """Content written in Markdown, which may mix in HTML."""

    def format_text(self, text: str, inline: bool) -> str:
        """Render the text from Markdown."""
        return render_markdown(text, inline)
