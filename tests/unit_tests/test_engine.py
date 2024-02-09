from os.path import dirname

from flask import Flask

from platzky.config import Config
from platzky.platzky import create_engine_from_config, create_app_from_config

from bs4 import BeautifulSoup

def test_engine_creation():
    config = Config.parse_obj(
        {
            "APP_NAME": "testingApp",
            "SECRET_KEY": "secret",
            "DB": {
                "TYPE": "json_file",
                "PATH": f"{dirname(__file__)}/../e2e_tests/e2e_test_data.json",
            },
        }
    )
    engine = create_engine_from_config(config)
    assert isinstance(engine, Flask)


def test_babel_gets_proper_directories():
    translation_directories = ["/some/fake/dir"]
    config = Config.parse_obj(
        {
            "APP_NAME": "testingApp",
            "SECRET_KEY": "secret",
            "TRANSLATION_DIRECTORIES": translation_directories,
            "DB": {
                "TYPE": "json_file",
                "PATH": f"{dirname(__file__)}/../e2e_tests/e2e_test_data.json",
            },
        }
    )
    engine = create_engine_from_config(config)
    with engine.app_context():
        assert (
            list(engine.babel.domain_instance.translation_directories)
            == translation_directories
        )


def test_notifier():
    config = Config.parse_obj(
        {
            "APP_NAME": "testingApp",
            "SECRET_KEY": "secret",
            "DB": {
                "TYPE": "json",
                "DATA": {}
            },
        }
    )
    engine = create_engine_from_config(config)
    notifier_msg = None
    def notifier(message):
        nonlocal notifier_msg
        notifier_msg = message
    engine.add_notifier(notifier)
    engine.notify("test")
    assert notifier_msg == "test"


def test_dynamic_body():
    config = Config.parse_obj(
        {
            "APP_NAME": "testingApp",
            "SECRET_KEY": "secret",
            "USE_WWW": False,
            "BLOG_PREFIX": "/blog",
            "DB": {
                "TYPE": "json",
                "DATA": {
                    "site_content": {
                        "pages": [
                            {
                                "title": "test",
                                "slug": "test",
                                "contentInMarkdown": "test"
                            }
                        ],
                    }
                }
            },
        }
    )
    engine = create_app_from_config(config)
    engine.add_dynamic_body("test")
    engine.add_dynamic_body("test2")
    app = engine.test_client()
    response = app.get("/blog/page/test")

    soup = BeautifulSoup(response.data, "html.parser")
    body_content = soup.body.get_text()

    assert "test" in body_content
    assert "test2" in body_content


def test_dynamic_header():
    config = Config.parse_obj(
        {
            "APP_NAME": "testingApp",
            "SECRET_KEY": "secret",
            "USE_WWW": False,
            "BLOG_PREFIX": "/blog",
            "DB": {
                "TYPE": "json",
                "DATA": {
                    "site_content": {
                        "pages": [
                            {
                                "title": "test",
                                "slug": "test",
                                "contentInMarkdown": "test"
                            }
                        ],
                    }
                }
            },
        }
    )
    engine = create_app_from_config(config)
    engine.add_dynamic_header("test1")
    engine.add_dynamic_header("test2")
    app = engine.test_client()
    response = app.get("/blog/page/test")

    soup = BeautifulSoup(response.data, "html.parser")
    header_content = soup.head.get_text()

    assert "test1" in header_content
    assert "test2" in header_content
