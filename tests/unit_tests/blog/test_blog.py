# TODO create smaller and more meaningful tests
from platzky.platzky import create_engine
from platzky.blog import blog
from unittest.mock import MagicMock


def test_blog():
    db_mock = MagicMock()
    db_mock.get_post.return_value = {
            "title": "title",
            "language": "en",
            "slug": "slug",
            "tags": [
                "tag/1"
            ],
            "contentInRichText": {
                "markdown": "This is some content"
            },
            "date": "2021-02-19",
            "coverImage": {
                "alternateText": "text which is alternative",
                "image": {
                    "url": "https://media.graphcms.com/XvmCDUjYTIq4c9wOIseo"
                }
            },
            "comments": [
                {
                    "time_delta": "10 months ago",
                    "date": "2021-02-19T00:00:00",
                    "comment": "This is some comment",
                    "author": "author"
                }
            ]
        }

    config_mock = MagicMock()
    config = {"BLOG_PREFIX": '/prefix',  # TODO test without prefix in config (same for seo tests)
              "SECRET_KEY": "secret",
              "PLUGINS": [],
              "USE_WWW": False,
              "SEO_PREFIX": "/",
              "APP_NAME": "test",
              "TESTING": True,
              "DEBUG": True
    }

    config_mock.__getitem__.side_effect = config.__getitem__
    languages = {"en": {"name": "English", "flag": "uk", "domain":"localhost"}}
    domain_langs = {"localhost": "en"}
    app = create_engine(config, db_mock, languages, domain_langs)
    blog_blueprint = blog.create_blog_blueprint(db_mock, config_mock, app.babel)

    app.register_blueprint(blog_blueprint)

    response = app.test_client().get("/prefix/slug")
    assert response.status_code == 200
    assert b"This is some comment" in response.data
    assert b"This is some content" in response.data
