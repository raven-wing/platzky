import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner, Result

from platzky.cli import cli
from platzky.config import Config
from platzky.feature_flags import BUILTIN_FLAGS, FakeLogin
from platzky.platzky import create_app


def test_run_starts_server_on_given_address():
    app = MagicMock()

    with patch("platzky.cli.create_app", return_value=app) as create:
        result = CliRunner().invoke(
            cli, ["run", "--config", "config.yml", "--host", "0.0.0.0", "--port", "8080"]
        )

    assert result.exit_code == 0
    create.assert_called_once_with("config.yml", development=True)
    app.run.assert_called_once_with(host="0.0.0.0", port=8080, debug=True)


def test_run_defaults_to_localhost():
    app = MagicMock()

    with patch("platzky.cli.create_app", return_value=app):
        result = CliRunner().invoke(cli, ["run", "--config", "config.yml"])

    assert result.exit_code == 0
    app.run.assert_called_once_with(host="127.0.0.1", port=5000, debug=True)


def test_run_requires_config():
    result = CliRunner().invoke(cli, ["run"])

    assert result.exit_code != 0
    assert "--config" in result.output


def test_run_is_development_regardless_of_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FLASK_DEBUG", "0")
    app = MagicMock()

    with patch("platzky.cli.create_app", return_value=app) as create:
        result = CliRunner().invoke(cli, ["run", "--config", "config.yml"])

    assert result.exit_code == 0
    create.assert_called_once_with("config.yml", development=True)
    assert app.run.call_args.kwargs["debug"] is True


class TestInit:
    @staticmethod
    def _init(directory: Path) -> Result:
        return CliRunner().invoke(cli, ["init", "--path", str(directory)])

    def test_writes_config_and_database(self, tmp_path: Path):
        result = self._init(tmp_path)

        assert result.exit_code == 0
        config = yaml.safe_load((tmp_path / "config.yml").read_text())
        assert config["APP_NAME"] == "My Platzky App"
        assert config["DB"] == {"TYPE": "json_file", "PATH": "data.json"}
        assert config["USE_WWW"] is False
        content = json.loads((tmp_path / "data.json").read_text())["site_content"]
        assert [post["slug"] for post in content["posts"]] == ["hello-platzky"]
        assert [page["slug"] for page in content["pages"]] == ["about"]
        assert content["menu_items"]["en"] == [
            {"name": "Blog", "url": "/blog/"},
            {"name": "About", "url": "/blog/page/about"},
        ]

    def test_lists_every_built_in_feature_flag_commented_out(self, tmp_path: Path):
        self._init(tmp_path)

        config_text = (tmp_path / "config.yml").read_text()

        assert "#FEATURE_FLAGS:" in config_text
        for flag in BUILTIN_FLAGS:
            assert f"#  {flag.alias}: {str(flag.default).lower()}" in config_text
        assert yaml.safe_load(config_text).get("FEATURE_FLAGS") is None

    def test_commented_flags_work_once_uncommented(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        self._init(tmp_path)
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            config_file.read_text()
            .replace("#FEATURE_FLAGS:", "FEATURE_FLAGS:")
            .replace("#  FAKE_LOGIN: false", "  FAKE_LOGIN: true")
        )
        monkeypatch.chdir(tmp_path)

        config = Config.parse_yaml("config.yml")

        assert config.feature_flags[FakeLogin.alias] is True

    def test_created_site_serves_its_sample_content(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        self._init(tmp_path)
        # DB PATH is relative, so the application runs from the directory it was created in.
        monkeypatch.chdir(tmp_path)

        app = create_app("config.yml")
        client = app.test_client()

        assert client.get("/blog/").status_code == 200
        assert client.get("/blog/hello-platzky").status_code == 200
        assert client.get("/blog/page/about").status_code == 200

    def test_tells_how_to_run_the_application(self, tmp_path: Path):
        result = self._init(tmp_path)

        # The database path in the config is relative, so the directory matters.
        assert f"Run it from {tmp_path.resolve()}: platzky run --config config.yml" in result.output

    def test_printed_command_actually_starts_the_site(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        self._init(tmp_path)
        monkeypatch.chdir(tmp_path)

        app = create_app("config.yml")

        assert app.test_client().get("/blog/").status_code == 200

    @pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
    def test_config_is_readable_only_by_its_owner(self, tmp_path: Path):
        self._init(tmp_path)

        # It holds the generated SECRET_KEY, which signs session cookies.
        assert (tmp_path / "config.yml").stat().st_mode & 0o777 == 0o600

    def test_created_config_is_valid(self, tmp_path: Path):
        self._init(tmp_path)

        config = Config.parse_yaml(str(tmp_path / "config.yml"))

        assert config.app_name == "My Platzky App"

    def test_secret_key_differs_between_applications(self, tmp_path: Path):
        self._init(tmp_path / "first")
        self._init(tmp_path / "second")

        keys = {
            yaml.safe_load((tmp_path / name / "config.yml").read_text())["SECRET_KEY"]
            for name in ("first", "second")
        }
        assert len(keys) == 2

    def test_refuses_to_overwrite(self, tmp_path: Path):
        self._init(tmp_path)
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_file.read_text().replace("My Platzky App", "Edited By Hand"))

        result = self._init(tmp_path)

        assert result.exit_code != 0
        assert "Refusing to overwrite" in result.output
        assert "Edited By Hand" in config_file.read_text()
