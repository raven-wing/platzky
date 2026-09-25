"""Command line interface for running a Platzky application."""

from datetime import date
from importlib.resources import files
from pathlib import Path
from secrets import token_hex
from string import Template

import click

from platzky.platzky import create_app

_CONFIG_FILENAME = "config.yml"
_DATA_FILENAME = "data.json"
_SCAFFOLD_DIR = "scaffold"
# Named .template so the repository's ignore rules for config.yml/data.json do not apply.
_CONFIG_TEMPLATE = "config.template.yml"
_DATA_TEMPLATE = "data.template.json"


def _render_scaffold(filename: str, **values: str) -> str:
    """Fill in the placeholders of a scaffold file shipped with the package.

    Args:
        filename: Name of the file in the scaffold directory
        values: Replacements for the file's ``$placeholder`` markers

    Returns:
        Contents of the file with every placeholder replaced
    """
    scaffold_file = files("platzky").joinpath(_SCAFFOLD_DIR).joinpath(filename)
    return Template(scaffold_file.read_text(encoding="utf-8")).substitute(values)


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
    """
    app = create_app(config_path)
    # Explicit debug wins over FLASK_DEBUG, which Flask.run would otherwise let override it.
    app.run(host=host, port=port, debug=app.debug)


@cli.command()
@click.option(
    "--path",
    "directory",
    default=".",
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory the files are created in.",
)
def create(directory: Path) -> None:
    """Create a new Platzky application: a config file and a JSON database with sample content."""
    directory.mkdir(parents=True, exist_ok=True)
    config_file, data_file = directory / _CONFIG_FILENAME, directory / _DATA_FILENAME
    existing = [str(f) for f in (config_file, data_file) if f.exists()]
    if existing:
        raise click.ClickException(f"Refusing to overwrite: {', '.join(existing)}")

    config_file.write_text(
        _render_scaffold(
            _CONFIG_TEMPLATE,
            secret_key=token_hex(32),
            data_filename=_DATA_FILENAME,
        )
    )
    data_file.write_text(_render_scaffold(_DATA_TEMPLATE, today=date.today().isoformat()))
    click.echo(f"Created {config_file} and {data_file}")
    click.echo(f"Run it with: platzky run --config {config_file}")
    click.echo("It starts with one sample post and an About page; edit them in the database file.")
