import os
import sys
from os.path import dirname, abspath
import importlib.util


def find_plugins():
    plugin_dir = os.path.join(dirname(abspath(__file__)), 'plugins')
    plugins = []
    for name in os.listdir(plugin_dir):
        if "plugin" in name:
            module_name = name.removesuffix('.py')
            spec = importlib.util.spec_from_file_location(module_name,
                                                          os.path.join(plugin_dir, name))
            plugin = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = plugin
            spec.loader.exec_module(plugin)
            plugins.append(plugin)
    return plugins


def plugify(app):
    for plugin in find_plugins():
        plugin.process(app)
    return app
