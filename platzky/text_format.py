"""The formats an author can write content in, and how each becomes HTML."""

import logging
from typing import Protocol

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin

# markdown-it traces every parsing rule at DEBUG, which buries a site's own debug log.
logging.getLogger("markdown_it").setLevel(logging.INFO)


class TextFormat(Protocol):
    """How text an author wrote becomes HTML."""

    def to_html(self, text: str, *, inline: bool) -> str:
        """Turn the author's text into HTML.

        Args:
            text: The author's text, with a placeholder tag where each shortcode goes.
            inline: Whether the text sits inside a shortcode element such as a link, where
                block structure like a wrapping ``<p>`` would be invalid.

        Returns:
            The text as HTML.
        """
        ...


class _Html:
    """Text written in HTML already."""

    def to_html(self, text: str, *, inline: bool) -> str:  # noqa: ARG002
        """Return the text as it is."""
        return text


class _Markdown:
    """Text written in Markdown, which may mix in HTML."""

    def __init__(self) -> None:
        """Set up CommonMark with tables, strikethrough and task lists."""
        # HTML passes through: an author may mix it in, and shortcode output reaches the
        # renderer as placeholder tags.
        self._parser = (
            MarkdownIt("commonmark", {"html": True})
            .enable(["table", "strikethrough"])
            .use(tasklists_plugin)
        )

    def to_html(self, text: str, *, inline: bool) -> str:
        """Render the text from Markdown."""
        return self._parser.renderInline(text) if inline else self._parser.render(text)


HTML: TextFormat = _Html()
MARKDOWN: TextFormat = _Markdown()
