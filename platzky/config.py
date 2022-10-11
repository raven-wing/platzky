from os import path
import yaml


class Config():
    def __init__(self, absolute_config_path):
        self.config = get_config_mapping(absolute_config_path)

    def add_translations_dir(self, absolute_translation_dir):
        self.config["BABEL_TRANSLATION_DIRECTORIES"] += ";" + absolute_translation_dir

    def asdict(self):
        return self.config


def get_config_mapping(absolute_config_path):
    default_config = {
        "USE_WWW": True,
        "SEO_PREFIX": "/",
        "BLOG_PREFIX": "/"
    }
    with open(absolute_config_path, "r") as stream:
        file_config = yaml.safe_load(stream)

    config = default_config | file_config
    config["CONFIG_PATH"] = absolute_config_path
    babel_format_dir = ";".join(config.get("TRANSLATION_DIRECTORIES", []))
    config["BABEL_TRANSLATION_DIRECTORIES"] = babel_format_dir
    return config


def load_config(absolute_config_path):
    config = Config(absolute_config_path)
    path_to_module_locale = path.join(path.dirname(__file__), "./locale")
    config.add_translations_dir(path_to_module_locale)
    return config
