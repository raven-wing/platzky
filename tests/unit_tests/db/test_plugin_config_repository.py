from platzky.db.plugin_config_repository import DocumentPluginConfigRepository


class TestDocumentPluginConfigRepository:
    def test_get_all_returns_validated_configs(self):
        data = {"plugins": {"my_plugin": {"is_active": True, "config": {"key": "value"}}}}
        repository = DocumentPluginConfigRepository(data)

        plugins = repository.get_all()

        assert plugins["my_plugin"].is_active is True
        assert plugins["my_plugin"].config == {"key": "value"}

    def test_get_all_returns_empty_dict_when_missing(self):
        repository = DocumentPluginConfigRepository({})
        assert repository.get_all() == {}

    def test_get_all_returns_empty_dict_when_plugins_is_none(self):
        repository = DocumentPluginConfigRepository({"plugins": None})
        assert repository.get_all() == {}
