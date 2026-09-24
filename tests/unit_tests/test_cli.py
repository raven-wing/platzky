import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner, Result

from platzky.cli import cli
from platzky.config import Config
from platzky.platzky import create_app


def test_run_starts_server_on_given_address():
    app = MagicMock()

    with patch("platzky.cli.create_app", return_value=app) as create:
        result = CliRunner().invoke(
            cli, ["run", "--config", "config.yml", "--host", "0.0.0.0", "--port", "8080"]
        )

    assert result.exit_code == 0
    create.assert_called_once_with("config.yml")
    app.run.assert_called_once_with(host="0.0.0.0", port=8080, debug=app.debug)


def test_run_defaults_to_localhost():
    app = MagicMock()

    with patch("platzky.cli.create_app", return_value=app):
        result = CliRunner().invoke(cli, ["run", "--config", "config.yml"])

    assert result.exit_code == 0
    app.run.assert_called_once_with(host="127.0.0.1", port=5000, debug=app.debug)


def test_run_requires_config():
    result = CliRunner().invoke(cli, ["run"])

    assert result.exit_code != 0
    assert "--config" in result.output


@pytest.mark.parametrize("debug", [True, False], ids=["debug_on", "debug_off"])
def test_run_debug_follows_config_not_environment(monkeypatch: pytest.MonkeyPatch, debug: bool):
    monkeypatch.setenv("FLASK_DEBUG", "0" if debug else "1")
    app = MagicMock()
    app.debug = debug

    with patch("platzky.cli.create_app", return_value=app):
        result = CliRunner().invoke(cli, ["run", "--config", "config.yml"])

    assert result.exit_code == 0
    assert app.run.call_args.kwargs["debug"] is debug


class TestCreate:
    @staticmethod
    def _create(directory: Path, name: str = "My Site") -> Result:
        return CliRunner().invoke(cli, ["create", "--name", name, "--path", str(directory)])

    def test_writes_config_and_database(self, tmp_path: Path):
        result = self._create(tmp_path)

        assert result.exit_code == 0
        config = yaml.safe_load((tmp_path / "config.yml").read_text())
        assert config["APP_NAME"] == "My Site"
        assert config["DB"] == {"TYPE": "json_file", "PATH": "data.json"}
        assert config["USE_WWW"] is False
        content = json.loads((tmp_path / "data.json").read_text())["site_content"]
        assert [post["slug"] for post in content["posts"]] == ["hello-platzky"]
        assert [page["slug"] for page in content["pages"]] == ["about"]
        assert content["menu_items"]["en"] == [
            {"name": "Blog", "url": "/blog/"},
            {"name": "About", "url": "/blog/page/about"},
        ]

    def test_sample_content_is_named_after_the_application(self, tmp_path: Path):
        self._create(tmp_path, name="Bakery")

        content = json.loads((tmp_path / "data.json").read_text())["site_content"]

        assert content["app_description"]["en"] == "Bakery — a site built with Platzky"
        assert content["posts"][0]["author"] == "Bakery"

    def test_created_site_serves_its_sample_content(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        self._create(tmp_path)
        # DB PATH is relative, so the application runs from the directory it was created in.
        monkeypatch.chdir(tmp_path)

        app = create_app("config.yml")
        client = app.test_client()

        assert client.get("/blog/").status_code == 200
        assert client.get("/blog/hello-platzky").status_code == 200
        assert client.get("/blog/page/about").status_code == 200

    def test_tells_how_to_run_the_application(self, tmp_path: Path):
        result = self._create(tmp_path)

        assert f"platzky run --config {tmp_path / 'config.yml'}" in result.output

    def test_created_config_is_valid(self, tmp_path: Path):
        self._create(tmp_path)

        config = Config.parse_yaml(str(tmp_path / "config.yml"))

        assert config.app_name == "My Site"

    def test_secret_key_differs_between_applications(self, tmp_path: Path):
        self._create(tmp_path / "first")
        self._create(tmp_path / "second")

        keys = {
            yaml.safe_load((tmp_path / name / "config.yml").read_text())["SECRET_KEY"]
            for name in ("first", "second")
        }
        assert len(keys) == 2

    def test_refuses_to_overwrite(self, tmp_path: Path):
        self._create(tmp_path)

        result = self._create(tmp_path, name="Other")

        assert result.exit_code != 0
        assert "Refusing to overwrite" in result.output
        assert "My Site" in (tmp_path / "config.yml").read_text()
