import threading
from unittest.mock import Mock, patch

import pytest
from gql import Client

from platzky.db.graph_ql_db import (
    GraphQL,
    GraphQlDbConfig,
    db_config_type,
    db_from_config,
)


@pytest.fixture
def mock_client():
    client = Mock()
    return client


@pytest.fixture
def graph_ql_db(mock_client: Mock):
    with patch("platzky.db.graph_ql_db.Client", return_value=mock_client):
        db = GraphQL(
            "https://test.endpoint", "test_token"
        )  # NOSONAR - hardcoded token acceptable in tests
        db.client  # trigger lazy construction now, while Client is patched
    return db


def test_db_config_type():
    assert db_config_type() == GraphQlDbConfig


def test_graph_ql_db_config():
    config = GraphQlDbConfig.model_validate(
        {"TYPE": "graph_ql_db", "CMS_ENDPOINT": "https://test.endpoint", "CMS_TOKEN": "test_token"}
    )
    assert config.endpoint == "https://test.endpoint"
    assert config.token == "test_token"


def test_db_from_config():
    config = GraphQlDbConfig(
        TYPE="graph_ql_db", CMS_ENDPOINT="https://test.endpoint", CMS_TOKEN="test_token"
    )
    with patch("platzky.db.graph_ql_db.GraphQL") as mock_graph_ql:
        db_from_config(config)
        mock_graph_ql.assert_called_once_with("https://test.endpoint", "test_token")


def test_graph_ql_init(mock_client: Mock):
    with (
        patch("platzky.db.graph_ql_db.AIOHTTPTransport") as mock_transport,
        patch("platzky.db.graph_ql_db.Client", return_value=mock_client) as mock_client_class,
    ):
        db = GraphQL(
            "https://test.endpoint", "test_token"
        )  # NOSONAR - hardcoded token acceptable in tests

        assert db.client == mock_client  # client is built lazily, on first access
        mock_transport.assert_called_once_with(
            url="https://test.endpoint", headers={"Authorization": "bearer test_token"}
        )
        mock_client_class.assert_called_once()
        assert db.module_name == "graph_ql_db"
        assert db.db_name == "GraphQLDb"


def test_graph_ql_client_is_per_thread():
    db = GraphQL(
        "https://test.endpoint", "test_token"
    )  # NOSONAR - hardcoded token acceptable in tests

    main_thread_client = db.client
    other_thread_client: list[Client | Exception] = []

    def get_client_in_thread():
        try:
            other_thread_client.append(db.client)
        except Exception as e:
            other_thread_client.append(e)

    thread = threading.Thread(target=get_client_in_thread)
    thread.start()
    thread.join()

    assert len(other_thread_client) == 1, "Thread did not complete"
    if isinstance(other_thread_client[0], Exception):
        raise other_thread_client[0]
    assert db.client is main_thread_client
    assert other_thread_client[0] is not main_thread_client


def test_get_all_posts_delegates_to_blog_storage(graph_ql_db: GraphQL):
    graph_ql_db._blog_storage = Mock()  # type: ignore[reportPrivateUsage]
    graph_ql_db._blog_storage.posts.get_all.return_value = ["sentinel"]  # type: ignore[reportPrivateUsage]

    result = graph_ql_db.get_all_posts("en")

    graph_ql_db._blog_storage.posts.get_all.assert_called_once_with(  # type: ignore[reportPrivateUsage]
        "en"
    )
    assert result == ["sentinel"]


def test_get_post_delegates_to_blog_storage(graph_ql_db: GraphQL):
    graph_ql_db._blog_storage = Mock()  # type: ignore[reportPrivateUsage]
    graph_ql_db._blog_storage.posts.get.return_value = "sentinel"  # type: ignore[reportPrivateUsage]

    result = graph_ql_db.get_post("test-post")

    graph_ql_db._blog_storage.posts.get.assert_called_once_with(  # type: ignore[reportPrivateUsage]
        "test-post"
    )
    assert result == "sentinel"


def test_get_page_delegates_to_blog_storage(graph_ql_db: GraphQL):
    graph_ql_db._blog_storage = Mock()  # type: ignore[reportPrivateUsage]
    graph_ql_db._blog_storage.pages.get.return_value = "sentinel"  # type: ignore[reportPrivateUsage]

    result = graph_ql_db.get_page("about")

    graph_ql_db._blog_storage.pages.get.assert_called_once_with(  # type: ignore[reportPrivateUsage]
        "about"
    )
    assert result == "sentinel"


def test_get_posts_by_tag_delegates_to_blog_storage(graph_ql_db: GraphQL):
    graph_ql_db._blog_storage = Mock()  # type: ignore[reportPrivateUsage]
    graph_ql_db._blog_storage.posts.get_by_tag.return_value = ["sentinel"]  # type: ignore[reportPrivateUsage]

    result = graph_ql_db.get_posts_by_tag("tag", "en")

    graph_ql_db._blog_storage.posts.get_by_tag.assert_called_once_with(  # type: ignore[reportPrivateUsage]
        "tag", "en"
    )
    assert result == ["sentinel"]


def test_add_comment_delegates_to_blog_storage(graph_ql_db: GraphQL):
    graph_ql_db._blog_storage = Mock()  # type: ignore[reportPrivateUsage]

    graph_ql_db.add_comment("John Doe", "Great post!", "test-post")

    graph_ql_db._blog_storage.posts.add_comment.assert_called_once_with(  # type: ignore[reportPrivateUsage]
        "John Doe", "Great post!", "test-post"
    )


def test_get_plugins_data_delegates_to_plugins_repository(graph_ql_db: GraphQL):
    graph_ql_db._plugins_repository = Mock()  # type: ignore[reportPrivateUsage]
    graph_ql_db._plugins_repository.get_all.return_value = {"sentinel": "config"}  # type: ignore[reportPrivateUsage]

    result = graph_ql_db.get_plugins_data()

    graph_ql_db._plugins_repository.get_all.assert_called_once()  # type: ignore[reportPrivateUsage]
    assert result == {"sentinel": "config"}


def test_get_menu_items_in_lang_with_lang(graph_ql_db: GraphQL, mock_client: Mock):
    mock_response = {
        "menuItems": [{"name": "Home", "url": "/"}, {"name": "About", "url": "/about"}]
    }
    mock_client.execute.return_value = mock_response

    menu_items = graph_ql_db.get_menu_items_in_lang("en")

    assert len(menu_items) == 2
    assert menu_items[0].name == "Home"
    assert menu_items[1].url == "/about"
    mock_client.execute.assert_called_once()


def test_get_font(graph_ql_db: GraphQL):
    assert graph_ql_db.get_font() == ""


def test_get_logo_url_with_logos(graph_ql_db: GraphQL, mock_client: Mock):
    mock_response = {
        "logos": [
            {
                "logo": {
                    "alternateText": "Alt text",
                    "image": {"url": "https://example.com/logo.jpg"},
                }
            }
        ]
    }
    mock_client.execute.return_value = mock_response

    logo_url = graph_ql_db.get_logo_url()

    assert logo_url == "https://example.com/logo.jpg"
    mock_client.execute.assert_called_once()


def test_get_logo_url_without_logos(graph_ql_db: GraphQL, mock_client: Mock):
    mock_response = {"logos": []}
    mock_client.execute.return_value = mock_response

    logo_url = graph_ql_db.get_logo_url()

    assert logo_url == ""
    mock_client.execute.assert_called_once()


def test_get_app_description(graph_ql_db: GraphQL, mock_client: Mock):
    mock_response = {"applicationSetups": [{"applicationDescription": "Test description"}]}
    mock_client.execute.return_value = mock_response

    description = graph_ql_db.get_app_description("en")

    assert description == "Test description"
    mock_client.execute.assert_called_once()


def test_get_app_description_missing(graph_ql_db: GraphQL, mock_client: Mock):
    mock_response = {"applicationSetups": [{}]}
    mock_client.execute.return_value = mock_response

    description = graph_ql_db.get_app_description("en")

    assert description == ""
    mock_client.execute.assert_called_once()


def test_get_favicon_url(graph_ql_db: GraphQL, mock_client: Mock):
    mock_response = {"favicons": [{"favicon": {"url": "https://example.com/favicon.ico"}}]}
    mock_client.execute.return_value = mock_response

    favicon_url = graph_ql_db.get_favicon_url()

    assert favicon_url == "https://example.com/favicon.ico"
    mock_client.execute.assert_called_once()


def test_get_home_page_path(graph_ql_db: GraphQL, mock_client: Mock):
    mock_response = {"applicationSetups": [{"homePagePath": "/blog/page/about"}]}
    mock_client.execute.return_value = mock_response

    assert graph_ql_db.get_home_page_path("en") == "/blog/page/about"
    mock_client.execute.assert_called_once()


def test_get_home_page_path_missing(graph_ql_db: GraphQL, mock_client: Mock):
    mock_response = {"applicationSetups": [{}]}
    mock_client.execute.return_value = mock_response

    assert graph_ql_db.get_home_page_path("en") is None


def test_get_home_page_path_no_application_setups(graph_ql_db: GraphQL, mock_client: Mock):
    mock_client.execute.return_value = {"applicationSetups": []}

    assert graph_ql_db.get_home_page_path("en") is None


def test_get_primary_color(graph_ql_db: GraphQL, mock_client: Mock):
    mock_client.execute.return_value = {"themes": [{"primaryColor": "#0085A1"}]}

    color = graph_ql_db.get_primary_color()

    assert color == "#0085A1"
    mock_client.execute.assert_called_once()


def test_get_primary_color_missing(graph_ql_db: GraphQL, mock_client: Mock):
    mock_client.execute.return_value = {"themes": [{}]}

    assert graph_ql_db.get_primary_color() == "white"


def test_get_primary_color_no_themes(graph_ql_db: GraphQL, mock_client: Mock):
    mock_client.execute.return_value = {"themes": []}

    assert graph_ql_db.get_primary_color() == "white"


def test_get_secondary_color(graph_ql_db: GraphQL, mock_client: Mock):
    mock_client.execute.return_value = {"themes": [{"secondaryColor": "#006073"}]}

    color = graph_ql_db.get_secondary_color()

    assert color == "#006073"
    mock_client.execute.assert_called_once()


def test_get_secondary_color_missing(graph_ql_db: GraphQL, mock_client: Mock):
    mock_client.execute.return_value = {"themes": [{}]}

    assert graph_ql_db.get_secondary_color() == "navy"


def test_get_secondary_color_no_themes(graph_ql_db: GraphQL, mock_client: Mock):
    mock_client.execute.return_value = {"themes": []}

    assert graph_ql_db.get_secondary_color() == "navy"


def test_health_check_success(graph_ql_db: GraphQL, mock_client: Mock):
    """Test health check when GraphQL endpoint is accessible"""
    mock_client.execute.return_value = {"__typename": "Query"}

    # Should not raise any exception
    graph_ql_db.health_check()

    mock_client.execute.assert_called_once()


def test_health_check_failure(graph_ql_db: GraphQL, mock_client: Mock):
    """Test health check when GraphQL endpoint is not accessible"""
    mock_client.execute.side_effect = Exception("Connection failed")

    with pytest.raises(Exception, match="Connection failed"):
        graph_ql_db.health_check()
