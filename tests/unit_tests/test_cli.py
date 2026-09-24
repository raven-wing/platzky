from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from platzky.cli import cli


def test_run_starts_server_on_given_address():
    app = MagicMock()

    with patch("platzky.cli.create_app", return_value=app) as create:
        result = CliRunner().invoke(
            cli, ["run", "--config", "config.yml", "--host", "0.0.0.0", "--port", "8080"]
        )

    assert result.exit_code == 0
    create.assert_called_once_with("config.yml")
    app.run.assert_called_once_with(host="0.0.0.0", port=8080)


def test_run_defaults_to_localhost():
    app = MagicMock()

    with patch("platzky.cli.create_app", return_value=app):
        result = CliRunner().invoke(cli, ["run", "--config", "config.yml"])

    assert result.exit_code == 0
    app.run.assert_called_once_with(host="127.0.0.1", port=5000)


def test_run_requires_config():
    result = CliRunner().invoke(cli, ["run"])

    assert result.exit_code != 0
    assert "--config" in result.output
