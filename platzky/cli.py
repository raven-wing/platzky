"""Command line interface for running a Platzky application."""

import click

from platzky.platzky import create_app


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
    create_app(config_path).run(host=host, port=port)
