"""Command line interface for running a Platzky application."""

import json
from datetime import date
from pathlib import Path
from secrets import token_hex
from typing import Any

import click

from platzky.platzky import create_app

_CONFIG_FILENAME = "config.yml"
_DATA_FILENAME = "data.json"

_CONFIG_TEMPLATE = """\
APP_NAME: {name}
SECRET_KEY: {secret_key}

# Set to true once the site is served from a www domain.
USE_WWW: false

LANGUAGES:
  en:
    name: English
    flag: uk
    country: GB

DB:
  TYPE: json_file
  PATH: {data_filename}
"""

_WELCOME_POST_SLUG = "hello-platzky"
_WELCOME_MARKDOWN = """\
Welcome to your new Platzky site.

Edit `data.json` to change this post, add your own, or remove it entirely.
"""


def _sample_site_content(name: str) -> dict[str, Any]:
    """Return the site content a freshly created application starts with.

    Args:
        name: Application name, used in the site description and the sample page

    Returns:
        Site content with one post, one page and a menu linking to both
    """
    return {
        "site_content": {
            "app_description": {"en": f"{name} — a site built with Platzky"},
            "posts": [
                {
                    "title": "Hello, Platzky",
                    "slug": _WELCOME_POST_SLUG,
                    "author": name,
                    "language": "en",
                    "date": date.today().isoformat(),
                    "excerpt": "The first post of your new site.",
                    "contentInMarkdown": _WELCOME_MARKDOWN,
                    "tags": [],
                    "comments": [],
                }
            ],
            "pages": [
                {
                    "title": "About",
                    "slug": "about",
                    "author": name,
                    "language": "en",
                    "excerpt": f"About {name}.",
                    "contentInMarkdown": f"# About\n\nTell your readers about {name}.\n",
                }
            ],
            "menu_items": {
                "en": [
                    {"name": "Blog", "url": "/blog/"},
                    {"name": "About", "url": "/blog/page/about"},
                ]
            },
        }
    }


@click.group()
def cli() -> None:
    """Platzky command line interface."""


@cli.command()
@click.option("--config", "config_path", required=True, help="Path to the YAML config file.")
@click.option("--host", default="127.0.0.1", show_default=True, help="Interface to bind to.")
@click.option("--port", default=5000, show_default=True, type=int, help="Port to bind to.")
def run(config_path: str, host: str, port: int) -> None:
    """Run the development server.

    DEBUG in the configuration file enables the reloader and the interactive debugger.

    Args:
        config_path: Path to the YAML configuration file
        host: Interface the server binds to
        port: Port the server binds to
    """
    app = create_app(config_path)
    # Explicit debug wins over FLASK_DEBUG, which Flask.run would otherwise let override it.
    app.run(host=host, port=port, debug=app.debug)


@cli.command()
@click.option("--name", required=True, help="Application name written to the config file.")
@click.option(
    "--path",
    "directory",
    default=".",
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory the files are created in.",
)
def create(name: str, directory: Path) -> None:
    """Create a new Platzky application: a config file and a JSON database with sample content.

    Args:
        name: Application name written to the config file
        directory: Directory the config and database files are created in
    """
    directory.mkdir(parents=True, exist_ok=True)
    config_file, data_file = directory / _CONFIG_FILENAME, directory / _DATA_FILENAME
    existing = [str(f) for f in (config_file, data_file) if f.exists()]
    if existing:
        raise click.ClickException(f"Refusing to overwrite: {', '.join(existing)}")

    config_file.write_text(
        _CONFIG_TEMPLATE.format(name=name, secret_key=token_hex(32), data_filename=_DATA_FILENAME)
    )
    data_file.write_text(
        json.dumps(_sample_site_content(name), indent=2, ensure_ascii=False) + "\n"
    )
    click.echo(f"Created {config_file} and {data_file}")
    click.echo(f"Run it with: platzky run --config {config_file}")
    click.echo("It starts with one sample post and an About page; edit them in the database file.")
