"""Command line interface for running a Platzky application."""

import json
import textwrap
from datetime import date
from importlib.resources import files
from pathlib import Path
from secrets import token_hex
from string import Template

import click

from platzky.feature_flags import BUILTIN_FLAGS
from platzky.platzky import create_app

_CONFIG_FILENAME = "config.yml"
_DATA_FILENAME = "data.json"
_SCAFFOLD_DIR = "scaffold"
# Named .template so the repository's ignore rules for config.yml/data.json do not apply.
_CONFIG_TEMPLATE = "config.template.yml"
_DATA_TEMPLATE = "data.template.json"


def _commented_feature_flags() -> str:
    """Return every built-in feature flag as commented-out YAML set to its default.

    Returns:
        Commented ``ALIAS: default`` lines, each preceded by the flag's first sentence
    """
    lines: list[str] = []
    for flag in sorted(BUILTIN_FLAGS, key=lambda f: f.alias):
        summary = flag.description.split(". ")[0].rstrip(".")
        if flag.production_warning:
            summary = f"{summary}. Never enable in production"
        lines.extend(
            textwrap.wrap(summary, width=96, initial_indent="#  # ", subsequent_indent="#  # ")
        )
        lines.append(f"#  {flag.alias}: {str(flag.default).lower()}")
    return "\n".join(lines)


def _render_scaffold(filename: str, raw: dict[str, str] | None = None, **values: str) -> str:
    """Fill in the placeholders of a scaffold file shipped with the package.

    Args:
        filename: Name of the file in the scaffold directory
        raw: Replacements inserted as they are, for markers standing for whole YAML blocks
            rather than for a single value
        values: Replacements for the file's ``$placeholder`` markers; each one is escaped so
            that it stays a single valid string in both YAML and JSON

    Returns:
        Contents of the file with every placeholder replaced
    """
    scaffold_file = files("platzky").joinpath(_SCAFFOLD_DIR).joinpath(filename)
    template = Template(scaffold_file.read_text(encoding="utf-8"))
    escaped = {key: json.dumps(value)[1:-1] for key, value in values.items()}
    return template.substitute({**escaped, **(raw or {})})


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
        _render_scaffold(
            _CONFIG_TEMPLATE,
            raw={"feature_flags": _commented_feature_flags()},
            app_name=name,
            secret_key=token_hex(32),
            data_filename=_DATA_FILENAME,
        )
    )
    data_file.write_text(
        _render_scaffold(_DATA_TEMPLATE, app_name=name, today=date.today().isoformat())
    )
    click.echo(f"Created {config_file} and {data_file}")
    click.echo(f"Run it with: platzky run --config {config_file}")
    click.echo("It starts with one sample post and an About page; edit them in the database file.")
