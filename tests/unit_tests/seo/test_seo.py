from unittest.mock import MagicMock
from flask import Flask
from platzky.seo import seo


def test_config_creation_with_incorrect_mappings():
    db_mock = MagicMock()
    config_mock = MagicMock()
    config_mock.__getitem__.return_value = '/prefix'

    seo_blueprint = seo.create_seo_blueprint(db_mock, config_mock)
    app = Flask(__name__)
    app.config.update({
        "TESTING": True,
        "DEBUG": True
    })
    app.register_blueprint(seo_blueprint)

    response = app.test_client().get("/prefix/robots.txt")
    assert b"Sitemap: https://localhost/sitemap.xml" in response.data
    assert response.status_code == 200
