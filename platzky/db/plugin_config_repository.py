"""Repository for plugin configuration.

Plugin config is app-wide bootstrap wiring, loaded once at startup by
`plugin_loader.plugify()` for every plugin type (notifiers, login, content
transformers, html injectors) -- not blog content, and not per-request site
chrome either, so it's kept separate from both `BlogStorage` and site
settings.
"""

from typing import Any, Protocol

from platzky.plugin.plugin_config import PluginConfigBase


class PluginConfigRepository(Protocol):
    """Repository for plugin configuration."""

    def get_all(self) -> dict[str, PluginConfigBase]:
        """Retrieve configuration data for all plugins, keyed by plugin name.

        Returns:
            Mapping of plugin name to its validated configuration.
        """
        ...


class DocumentPluginConfigRepository:
    """Plugin config repository backed by a shared, in-memory document."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Store a reference to the shared document.

        Args:
            data: The loaded document, shared with whatever else (blog
                storage, site settings) reads from the same backing store.
        """
        self._data = data

    def get_all(self) -> dict[str, PluginConfigBase]:
        """Retrieve configuration data for all plugins, keyed by plugin name.

        Returns:
            Mapping of plugin name to its validated configuration.
        """
        return {
            name: PluginConfigBase.model_validate(cfg)
            for name, cfg in (self._data.get("plugins") or {}).items()
        }
