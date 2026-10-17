import pytest

from platzky.config import Config
from platzky.platzky import create_app_from_config

CONTENT_URLS = ["/blog/slug", "/blog/page/slug"]


def _html(url: str, markdown: str, flags: dict[str, bool] | None = None) -> str:
    content = {
        "author": "author",
        "slug": "slug",
        "title": "title",
        "language": "en",
        "contentInMarkdown": markdown,
        "excerpt": "excerpt",
    }
    config = Config.model_validate(
        {
            "APP_NAME": "testApp",
            "SECRET_KEY": "secret",
            "USE_WWW": False,
            "BLOG_PREFIX": "/blog",
            "TRANSLATION_DIRECTORIES": [],
            "FEATURE_FLAGS": flags or {},
            "DB": {
                "TYPE": "json",
                "DATA": {
                    "site_content": {"posts": [content], "pages": [content]},
                    "plugins": {},
                },
            },
        }
    )
    app = create_app_from_config(config)
    return app.test_client().get(url).get_data(as_text=True)


@pytest.mark.parametrize("url", CONTENT_URLS)
def test_markdown_is_rendered_as_html(url: str):
    html = _html(url, "First line.\n\n## Heading\n\nSome **bold** text.\n\n> A quote")
    assert "<p>First line.</p>" in html
    assert "<h2>Heading</h2>" in html
    assert "<strong>bold</strong>" in html
    assert "<blockquote><p>A quote</p></blockquote>" in html
    assert "## Heading" not in html


@pytest.mark.parametrize("url", CONTENT_URLS)
def test_markdown_links_lists_and_task_lists_are_rendered(url: str):
    html = _html(url, "[Passkey](https://example.com/a_b_c)\n\n- one\n- [ ] todo\n- [x] done")
    assert '<a href="https://example.com/a_b_c">Passkey</a>' in html
    assert "<li>one</li>" in html
    assert 'type="checkbox"> todo</li>' in html
    assert 'checked="checked" disabled="disabled" type="checkbox"> done</li>' in html


@pytest.mark.parametrize("url", CONTENT_URLS)
def test_shortcodes_inside_markdown_still_render(url: str):
    html = _html(url, 'Some *emphasis* and [link url="/x_y"]a **link**[/link].')
    assert '<a href="/x_y"' in html
    assert "<strong>link</strong>" in html
    assert "<em>emphasis</em>" in html


@pytest.mark.parametrize("url", CONTENT_URLS)
def test_authored_html_passes_through_markdown(url: str):
    html = _html(url, "Before <b>bold</b> after.")
    assert "<p>Before <b>bold</b> after.</p>" in html


@pytest.mark.parametrize("url", CONTENT_URLS)
def test_strip_content_html_keeps_markdown_formatting(url: str):
    html = _html(url, "**kept** and <b>stripped</b>", flags={"STRIP_CONTENT_HTML": True})
    assert "<strong>kept</strong>" in html
    assert "<b>stripped</b>" not in html
