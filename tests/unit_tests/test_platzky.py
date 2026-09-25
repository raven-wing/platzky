import logging
import re
from collections.abc import Callable, Iterator
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from platzky import create_app_from_config
from platzky.config import Config, LanguageConfig
from platzky.platzky import (
    create_app,
    create_engine,
)


class TestPlatzky:
    @pytest.fixture
    def mock_db(self) -> MagicMock:
        return MagicMock()

    def test_change_language_with_domain(self, mock_db: MagicMock):
        """Test the change_language function when a domain is specified."""
        mock_config = MagicMock()
        mock_config.languages = {
            "en": LanguageConfig(name="English", flag="gb", country="GB", domain="example.com"),
            "de": LanguageConfig(name="German", flag="de", country="DE", domain="example.de"),
        }

        app = create_engine(mock_config, mock_db)
        app.config["WTF_CSRF_ENABLED"] = (
            False  # NOSONAR - CSRF intentionally disabled in test context
        )

        with app.test_request_context():
            mock_config.use_www = False
            app.secret_key = "test_secret_key"  # NOSONAR - hardcoded secret acceptable in tests
            response = app.test_client().get("/lang/de", follow_redirects=False)
            assert response.status_code == 302
            assert response.headers.get("Location") == "http://example.de"

    def test_change_language_without_domain(self, mock_db: MagicMock):
        """Test the change_language function when no domain is specified."""
        mock_config = MagicMock()
        mock_config.languages = {
            "en": LanguageConfig(name="English", flag="gb", country="GB", domain=None),
            "de": LanguageConfig(name="German", flag="de", country="DE", domain=None),
        }

        app = create_engine(mock_config, mock_db)
        app.config["WTF_CSRF_ENABLED"] = (
            False  # NOSONAR - CSRF intentionally disabled in test context
        )

        with app.test_request_context():
            mock_config.use_www = False
            app.secret_key = "test_secret_key"  # NOSONAR - hardcoded secret acceptable in tests
            response = app.test_client().get("/lang/de", follow_redirects=False)
            assert response.status_code == 302
            # When request.referrer is None, it should redirect to "/" instead
            assert response.headers.get("Location") == "/"

    def test_change_language_invalid_locale(self, mock_db: MagicMock):
        """Test that invalid language codes return 404."""
        mock_config = MagicMock()
        mock_config.languages = {
            "en": LanguageConfig(name="English", flag="gb", country="GB", domain=None),
            "de": LanguageConfig(name="German", flag="de", country="DE", domain=None),
        }

        app = create_engine(mock_config, mock_db)
        app.config["WTF_CSRF_ENABLED"] = (
            False  # NOSONAR - CSRF intentionally disabled in test context
        )

        with app.test_request_context():
            mock_config.use_www = False
            app.secret_key = "test_secret_key"  # NOSONAR - hardcoded secret acceptable in tests

            # Verify that session language does not get set to invalid language
            with app.test_client() as client:
                response = client.get("/lang/invalid_lang", follow_redirects=False)
                assert response.status_code == 404

                # Check that the invalid language was NOT set in session
                with client.session_transaction() as sess:
                    # Session might have a default language, but shouldn't be 'invalid_lang'
                    assert sess.get("language") != "invalid_lang"

    def test_url_link(self, mock_db: MagicMock):
        """Test the url_link function."""

        def url_link_func(x: object) -> str:
            return str(x)

        def context_proc() -> dict[str, Callable[[object], str]]:
            return {"url_link": url_link_func}

        mock_config = MagicMock()
        mock_config.context_processor_functions = [context_proc]

        app = create_engine(mock_config, mock_db)
        mock_processor = MagicMock()

        def url_link_func2(x: object) -> str:
            return str(x)

        mock_processor.return_value = {"url_link": url_link_func2}

        with app.test_request_context():
            url_link = mock_processor.return_value["url_link"]
            assert url_link("test") == "test"

    def test_create_app(self):
        """Test the create_app function."""
        with patch("platzky.platzky.Config.parse_yaml") as mock_parse_yaml:
            with patch("platzky.platzky.create_app_from_config") as mock_create_app_from_config:
                mock_config = MagicMock()
                mock_parse_yaml.return_value = mock_config
                mock_engine = MagicMock()
                mock_create_app_from_config.return_value = mock_engine

                result = create_app("test_config.yml")

                mock_parse_yaml.assert_called_once_with("test_config.yml")
                mock_create_app_from_config.assert_called_once_with(mock_config, development=False)
                assert result == mock_engine

    def test_fake_login_routes(self, mock_db: MagicMock):
        """Test the fake login routes."""
        with patch("platzky.platzky.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db

            config_raw = {
                "USE_WWW": False,
                "APP_NAME": "testing App Name",
                "SECRET_KEY": "secret",
                "SEO_PREFIX": "/seo",
                "TESTING": True,
                "DB": {"TYPE": "json", "DATA": {}},
                "FEATURE_FLAGS": {"FAKE_LOGIN": True},
            }
            config = Config.model_validate(config_raw)

            app = create_app_from_config(config, development=True)
            app.secret_key = "test_secret_key"  # NOSONAR - hardcoded secret acceptable in tests
            client = app.test_client()

            response = client.get("/login")
            html = response.data.decode("utf-8")

            match = re.search(r'name="csrf_token" value="(.+?)"', html)
            csrf_token = match.group(1) if match else None
            assert csrf_token is not None

            # Invalid role returns 401, no session user set
            response = client.post(
                "/login/verify/fake",
                data={"csrf_token": csrf_token, "role": "invalidrole"},
            )
            assert response.status_code == 401
            with client.session_transaction() as sess:
                assert "user" not in sess

            # GET is not allowed
            response = client.get("/login/verify/fake")
            assert response.status_code == 405
            with client.session_transaction() as sess:
                assert "user" not in sess

            response = client.post(
                "/login/verify/fake",
                follow_redirects=True,
                data={"csrf_token": csrf_token, "role": "admin"},
            )
            assert response.status_code == 200
            with client.session_transaction() as sess:
                assert "user" in sess
                assert sess["user"]["username"] == "admin"
                assert sess["user"]["role"] == "admin"

            response = client.post(
                "/login/verify/fake",
                follow_redirects=True,
                data={"csrf_token": csrf_token, "role": "nonadmin"},
            )
            assert response.status_code == 200
            with client.session_transaction() as sess:
                assert "user" in sess
                assert sess["user"]["username"] == "user"
                assert sess["user"]["role"] == "nonadmin"

    def test_fake_login_is_blocked_outside_development(self):
        """Test that fake login is blocked unless the app runs in development mode."""
        config_raw = {
            "USE_WWW": False,
            "APP_NAME": "testing App Name",
            "SECRET_KEY": "secret",
            "SEO_PREFIX": "/seo",
            "DB": {"TYPE": "json", "DATA": {}},
            "FEATURE_FLAGS": {"FAKE_LOGIN": True},
        }

        config = Config.model_validate(config_raw)

        with pytest.raises(
            RuntimeError,
            match="Cannot register FakeLoginPlugin in production",
        ):
            create_app_from_config(config)


class TestLogging:
    @pytest.fixture(autouse=True)
    def root_logger(self) -> Iterator[logging.Logger]:
        """Restore the root logger, which creating an application configures."""
        root_logger = logging.getLogger()
        level, handlers = root_logger.level, root_logger.handlers[:]
        yield root_logger
        root_logger.setLevel(level)
        root_logger.handlers = handlers

    @staticmethod
    def _create_app(development: bool = False, log_level: str | None = None) -> None:
        raw_config = {
            "APP_NAME": "testing App Name",
            "SECRET_KEY": "secret",
            "DB": {"TYPE": "json", "DATA": {}},
        }
        if log_level is not None:
            raw_config["LOG_LEVEL"] = log_level
        config = Config.model_validate(raw_config)
        with patch("platzky.platzky.get_db", return_value=MagicMock()):
            create_app_from_config(config, development=development)

    def test_defaults_to_info(self, root_logger: logging.Logger):
        self._create_app()

        assert root_logger.level == logging.INFO

    def test_development_enables_debug_level(self, root_logger: logging.Logger):
        self._create_app(development=True)

        assert root_logger.level == logging.DEBUG

    def test_log_level_applies_outside_development(self, root_logger: logging.Logger):
        self._create_app(log_level="WARNING")

        assert root_logger.level == logging.WARNING

    def test_log_level_wins_over_development(self, root_logger: logging.Logger):
        self._create_app(development=True, log_level="WARNING")

        assert root_logger.level == logging.WARNING

    def test_log_level_covers_other_libraries(self):
        self._create_app(log_level="DEBUG")

        assert logging.getLogger("some_other_library").getEffectiveLevel() == logging.DEBUG

    @pytest.mark.parametrize("level", ["debug", "Debug"], ids=["lower", "mixed"])
    def test_log_level_is_case_insensitive(self, root_logger: logging.Logger, level: str):
        self._create_app(log_level=level)

        assert root_logger.level == logging.DEBUG

    def test_invalid_log_level_is_rejected(self):
        with pytest.raises(ValidationError, match="Invalid LOG_LEVEL"):
            self._create_app(log_level="VERBOSE")

    def test_adds_one_handler_when_none_configured(self, root_logger: logging.Logger):
        root_logger.handlers = []

        self._create_app()
        self._create_app()

        assert len(root_logger.handlers) == 1

    def test_keeps_application_handlers(self, root_logger: logging.Logger):
        app_handler = logging.NullHandler()
        root_logger.handlers = [app_handler]

        self._create_app()

        assert root_logger.handlers == [app_handler]
