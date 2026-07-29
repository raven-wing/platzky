"""Plugin config repository implementation backed by a GraphQL (Hygraph) CMS."""

import threading

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

from platzky.plugin.plugin_config import PluginConfigBase


class GraphQLPluginConfigRepository:
    """Plugin config repository backed by a GraphQL CMS.

    Hygraph's ``PluginConfig`` schema only exposes ``name``, ``isActive``, and
    ``config`` (a JSON scalar) -- there's no room for a sibling field like
    ``allowed_content_types``. Authors put permission fields directly inside
    the ``config`` JSON instead; this spreads ``config``'s keys to the top
    level so the engine's capability-specific config classes
    (``ContentTransformerPluginConfig``, etc.) can find them by name.
    """

    def __init__(self, endpoint: str, token: str) -> None:
        """Store connection details for a lazily-built, per-thread client.

        Args:
            endpoint: GraphQL API endpoint URL.
            token: Authentication token for the API.
        """
        self._endpoint = endpoint
        self._headers = {"Authorization": "bearer " + token}
        self._local = threading.local()

    @property
    def _client(self) -> Client:
        """This thread's GraphQL client, built lazily on first access.

        AIOHTTPTransport's connect/close cycle tracks a single session flag per
        transport instance; sharing one Client across threads lets a second
        thread's connect() race a first thread's still-open session, raising
        TransportAlreadyConnected. A client per thread avoids that.
        """
        client = getattr(self._local, "client", None)
        if client is None:
            transport = AIOHTTPTransport(url=self._endpoint, headers=self._headers)
            client = Client(transport=transport)
            self._local.client = client
        return client

    def get_all(self) -> dict[str, PluginConfigBase]:
        """Retrieve configuration data for all plugins, keyed by plugin name.

        Returns:
            Mapping of plugin name to its validated configuration.
        """
        plugins_query = gql("""
            query MyQuery {
              pluginConfigs(stage: PUBLISHED) {
                name
                is_active: isActive
                config
              }
            }
            """)
        raw = self._client.execute(plugins_query)["pluginConfigs"]
        return {
            d["name"]: PluginConfigBase.model_validate({**(d.get("config") or {}), **d})
            for d in raw
        }
