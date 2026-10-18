"""Markdown rendering for CMS-authored content."""

import logging

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin

# HTML passes through: an author may mix it in, shortcode output reaches the renderer as
# placeholder tags, and the result is sanitized afterwards.
_markdown = (
    MarkdownIt("commonmark", {"html": True})
    .enable(["table", "strikethrough"])
    .use(tasklists_plugin)
)

# markdown-it traces every parsing rule at DEBUG, which buries a site's own debug log.
logging.getLogger("markdown_it").setLevel(logging.INFO)


def render_markdown(text: str, inline: bool) -> str:
    """Convert Markdown to HTML, unsanitized.

    Args:
        text: The Markdown source.
        inline: Render without block structure, for text inside an element such as a
            link, where a wrapping ``<p>`` would be invalid.

    Returns:
        The rendered HTML.
    """
    return _markdown.renderInline(text) if inline else _markdown.render(text)
